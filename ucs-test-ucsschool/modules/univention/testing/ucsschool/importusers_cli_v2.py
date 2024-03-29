# -*- coding: utf-8 -*-

import copy
import csv
import datetime
import json
import os
import pprint
import random
import shutil
import subprocess
import sys
import tempfile
import traceback
from collections import Mapping

from ldap.dn import escape_dn_chars
from ldap.filter import escape_filter_chars, filter_format
from six import iteritems, string_types

import univention.testing.strings as uts
import univention.testing.ucr
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm
from univention.admin.uexceptions import ldapError, noObject
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import get_mail_domain
from univention.testing.ucsschool.ucs_test_school import get_ucsschool_logger

try:
    from univention.testing.ucs_samba import DRSReplicationFailed
except ImportError:
    DRSReplicationFailed = Exception

from typing import Set  # noqa: F401


class ImportException(Exception):
    pass


class TestFailed(Exception):
    def __init__(self, msg, stack):
        self.msg = msg
        self.stack = stack


def reset_notifier_restart_burst_limit():
    """
    Avoid "univention-directory-notifier.service: Failed with result 'start-limit-hit'." errors due to
    too many notifier restarts.
    This resets the burst limit counter, which includes successful service starts
    (even though the option is called "reset-failed").
    """
    subprocess.call(("systemctl", "reset-failed", "univention-directory-notifier.service"))


class ConfigDict(dict):
    def update_entry(self, key, value):
        """
        update_entry('foo:bar:baz', 'my value')
        update_entry('foo:bar:ding', False)
        """
        if isinstance(value, string_types):
            if value.lower() == "false":
                value = False
            elif value.lower() == "true":
                value = True
        mydict = self
        items = key.split(":")
        while items:
            if len(items) == 1:
                if items[0] in mydict and isinstance(mydict[items[0]], Mapping):
                    mydict[items[0]].update(value)
                else:
                    mydict[items[0]] = value
            else:
                mydict = mydict.setdefault(items[0], {})
            del items[0]


class PyHooks(object):
    def __init__(self, hook_basedir=None):
        self.hook_basedir = hook_basedir or "/usr/share/ucs-school-import/pyhooks"
        self.tmpdir = tempfile.mkdtemp(prefix="pyhook.", dir="/tmp")
        self.cleanup_files = set()
        self.log = get_ucsschool_logger()

    def create_hooks(self):
        fn = "%s.py" % (uts.random_name(),)
        data = """from ucsschool.importer.utils.user_pyhook import UserPyHook
import os

class MyHook(UserPyHook):
    priority = {
            "pre_create": 1,
            "post_create": 1,
            "pre_modify": 1,
            "post_modify": 1,
            "pre_move": 1,
            "post_move": 1,
            "pre_remove": 1,
            "post_remove": 1
    }

    def pre_create(self, user):
            self.logger.info("Running a pre_create hook for %%s.", user)
            self.run(user, 'create', 'pre')

    def post_create(self, user):
            self.logger.info("Running a post_create hook for %%s.", user)
            self.run(user, 'create', 'post')

    def pre_modify(self, user):
            self.logger.info("Running a pre_modify hook for %%s.", user)
            self.run(user, 'modify', 'pre')

    def post_modify(self, user):
            self.logger.info("Running a post_modify hook for %%s.", user)
            self.run(user, 'modify', 'post')

    def pre_move(self, user):
            self.logger.info("Running a pre_move hook for %%s.", user)
            self.run(user, 'move', 'pre')

    def post_move(self, user):
            self.logger.info("Running a post_move hook for %%s.", user)
            self.run(user, 'move', 'post')

    def pre_remove(self, user):
            self.logger.info("Running a pre_remove hook for %%s.", user)
            self.run(user, 'remove', 'pre')

    def post_remove(self, user):
            self.logger.info("Running a post_remove hook for %%s.", user)
            self.run(user, 'remove', 'post')

    def run(self, user, action, when):
        self.logger.info("***** Running {} {} hook for user {}.".format(when, action, user))
        # udm_properties[k] is only filled from LDAP, if k was in the input
        # don't try to get_udm_object() on a user not {anymore, yet} in ldap
        if not user.udm_properties.get('street') and not ((action == 'create' and when == 'pre') \
        or (action == 'remove' and when == 'post')):
            obj = user.get_udm_object(self.lo)
            user.udm_properties['street'] = obj.info.get('street', '')
        user.udm_properties['street'] = user.udm_properties.get('street', '') + ',{}-{}'.format(
            when, action)
        if when == 'post' and action != 'remove':
            user.modify(self.lo)
        fn_touchfile = os.path.join(%(tmpdir)r, '%%s-%%s' %% (when, action))
        open(fn_touchfile, 'w').write('EXECUTED\\n')
""" % {
            "tmpdir": self.tmpdir
        }

        fn = os.path.join(self.hook_basedir, fn)
        self.cleanup_files.add(fn)
        with open(fn, "w") as fd:
            fd.write(data)
        self.log.info("Created hook %r", fn)

    def cleanup(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for fn in list(self.cleanup_files):
            try:
                os.remove(fn)
                self.log.debug("Removed %r.", fn)
            except (IOError, OSError):
                self.log.warning("Failed to remove %r" % (fn,))
            if fn.endswith(".py"):
                try:
                    os.remove("%sc" % (fn,))  # also remove .pyc files
                    self.log.debug("Removed %sc.", fn)
                except (IOError, OSError):
                    pass
            self.cleanup_files.remove(fn)


class ImportTestbase(object):
    ou_A = utu.Bunch(name=None, dn=None)  # will be initializes in create_ous()
    ou_B = utu.Bunch(name=None, dn=None)  # set ou_B to None if a second OU is not needed
    ou_C = utu.Bunch(name=None, dn=None)  # set ou_C to None if a third OU is not needed
    use_ou_cache = True  # if True: use cached OUs, if false create fresh OUs
    all_roles = ("staff", "student", "teacher", "teacher_and_staff")

    def __init__(self):
        self.ucr = univention.testing.ucr.UCSTestConfigRegistry()
        self.ucr.load()
        self.log = get_ucsschool_logger()
        self.lo = None  # will be initialized in run()
        self.ldap_status = None  # type: Set[str]
        # will be initialized in run():
        self.schoolenv = None  # type: univention.testing.ucsschool.UCSTestSchool
        self.udm = None  # type: univention.testing.udm.UCSTestUDM  # will be initialized in run()
        self.maildomain = get_mail_domain()

    def cleanup(self):
        self.log.info("Performing ImportTestbase cleanup...")
        self.udm.cleanup()
        self.log.info("Reverting UCR...")
        self.ucr.revert_to_original_registry()
        self.log.info("ImportTestbase cleanup done")

    def save_ldap_status(self):
        self.log.debug("Saving LDAP status...")
        self.ldap_status = utu.UCSTestSchool.get_ldap_status(self.lo)
        self.log.debug("LDAP status saved.")

    def diff_ldap_status(self):
        self.log.debug("Reading LDAP status to check differences...")
        res = utu.UCSTestSchool.diff_ldap_status(self.lo, self.ldap_status)
        self.log.debug("New objects: {!r}".format(res.new))
        self.log.debug("Removed objects: {!r}".format(res.removed))
        return res

    @classmethod
    def pugre_timestamp_ldap2udm(cls, ldap_val):
        """Convert '20090101000000Z' to '2009-01-01'. Ignores timezones."""
        if not ldap_val:
            return ""
        ldap_date = datetime.datetime.strptime(ldap_val, cls.ldap_date_format)
        return ldap_date.strftime(cls.udm_date_format)

    @classmethod
    def pugre_timestamp_udm2ldap(cls, udm_val):
        """Convert '2009-01-01' to '20090101000000Z'. Ignores timezones."""
        if not udm_val:
            return ""
        udm_date = datetime.datetime.strptime(udm_val, cls.udm_date_format)
        return udm_date.strftime(cls.ldap_date_format)

    def check_new_and_removed_users(self, exp_new, exp_removed):
        ldap_diff = self.diff_ldap_status()
        new_users = [x for x in ldap_diff.new if x.startswith("uid=")]
        if len(new_users) != exp_new:
            self.log.error(
                "Invalid number of new users (expected %d, found %d)! Found new objects: %r",
                exp_new,
                len(new_users),
                new_users,
            )
            self.fail("Stopping because of invalid number of new users.")
        removed_users = [x for x in ldap_diff.removed if x.startswith("uid=")]
        if len(removed_users) != exp_removed:
            self.log.error(
                "Invalid number of removed users (expected %d, found %d)! Removed objects: %r",
                exp_removed,
                len(removed_users),
                removed_users,
            )
            self.fail("Stopping because of invalid number of removed users.")

    def fail(self, msg, returncode=1):
        """Print package versions, traceback and error message."""
        self.log.error("\n%s\n%s%s", "=" * 79, "".join(traceback.format_stack()), "=" * 79)
        utils.fail(msg, returncode)

    def create_ous(self, schoolenv):
        self.log.info("Creating OUs...")
        ous = [ou for ou in [self.ou_A, self.ou_B, self.ou_C] if ou is not None]
        res = schoolenv.create_multiple_ous(
            len(ous), name_edudc=self.ucr.get("hostname"), use_cache=self.use_ou_cache
        )
        for num, (name, dn) in enumerate(res):
            ou = ous[num]
            ou.name, ou.dn = name, dn
        self.log.info(
            "Created OUs: %r.",
            [_ou.name for _ou in [self.ou_A, self.ou_B, self.ou_C] if _ou is not None],
        )

    def setup_testenv(self, schoolenv):
        self.schoolenv = schoolenv
        self.udm = schoolenv.udm
        if self.maildomain not in self.ucr.get("mail/hosteddomains", ""):
            self.log.info("\n\n*** Creating mail domain %r...\n", self.maildomain)
            self.udm.create_object(
                "mail/domain",
                position="cn=domain,cn=mail,{}".format(self.ucr["ldap/base"]),
                name=self.maildomain,
                ignore_exists=True,
            )
        has_admin_credentials = self.ucr["server/role"] in (
            "domaincontroller_master",
            "domaincontroller_backup",
        )
        self.lo = schoolenv.open_ldap_connection(admin=has_admin_credentials)

    def run(self):
        try:
            with utu.UCSTestSchool() as schoolenv:
                self.setup_testenv(schoolenv)
                self.create_ous(schoolenv)
                self.test()
                self.log.info("Test was successful.\n\n")
        finally:
            self.cleanup()

    def test(self):
        raise NotImplementedError()

    def wait_for_drs_replication_of_membership(
        self, group_dn, member_uid, is_member=True, try_resync=True, **kwargs
    ):
        """
        wait_for_drs_replication() of a user to become a member of a group.
        :param group: str: DN of a group
        :param member_uid: str: username
        :param is_member: bool: whether the user should be a member or not
        :param try_resync: bool: if waiting for drs replication didn't succeed, run
        "/usr/share/univention-s4-connector/resync_object_from_ucs.py <group_dn>" and wait again
        :param kwargs: dict: will be passed to wait_for_drs_replication() with a modified 'ldap_filter'
        :return: None | <ldb result>
        """
        if not utils.package_installed("univention-samba4"):
            self.log.info(
                "wait_for_drs_replication_of_membership(): skip, univention-samba4 not installed."
            )
            return
        try:
            user_filter = kwargs["ldap_filter"]
            if user_filter and not user_filter.startswith("("):
                user_filter = "({})".format(user_filter)
        except KeyError:
            user_filter = ""
        if is_member:
            member_filter = filter_format("(memberOf=%s)", (group_dn,))
        else:
            member_filter = filter_format("(!(memberOf=%s))", (group_dn,))
        kwargs["ldap_filter"] = "(&(cn={}){}{})".format(
            escape_filter_chars(member_uid), member_filter, user_filter
        )
        try:
            res = wait_for_drs_replication(**kwargs)
        except DRSReplicationFailed as exc:
            self.log.error("DRSReplicationFailed: %s", exc)
            res = None
        if not res:
            self.log.warning("No result from wait_for_drs_replication().")
            if try_resync:
                cmd = ["/usr/share/univention-s4-connector/resync_object_from_ucs.py", group_dn]
                self.log.info("Running subprocess.call(%r)...", cmd)
                subprocess.call(cmd)
                self.log.info(
                    "Waiting again. Executing: wait_for_drs_replication_of_membership(group_dn=%r, "
                    "member_uid=%r, is_member=%r, try_resync=False, **kwargs=%r)...",
                    group_dn,
                    member_uid,
                    is_member,
                    kwargs,
                )
                # recursion once with try_resync=False
                res = self.wait_for_drs_replication_of_membership(
                    group_dn=group_dn,
                    member_uid=member_uid,
                    is_member=is_member,
                    try_resync=False,
                    **kwargs
                )
        return res


class CLI_Import_v2_Tester(ImportTestbase):
    ldap_date_format = "%Y%m%d%H%M%SZ"
    udm_date_format = "%Y-%m-%d"

    def __init__(self):
        super(CLI_Import_v2_Tester, self).__init__()
        self.tmpdir = tempfile.mkdtemp(prefix="34_import-users_via_cli_v2.", dir="/tmp/")
        self.hook_fn_set = set()
        self.default_config = ConfigDict(
            {
                "factory": "ucsschool.importer.default_user_import_factory.DefaultUserImportFactory",
                "classes": {},
                "input": {"type": "csv", "filename": "import.csv"},
                "csv": {
                    "mapping": {
                        "OUs": "schools",
                        "Vor": "firstname",
                        "Nach": "lastname",
                        "Gruppen": "school_classes",
                        "E-Mail": "email",
                        "Beschreibung": "description",
                    }
                },
                "maildomain": self.maildomain,
                "scheme": {
                    "email": "<:umlauts><firstname>[0].<lastname>@<maildomain>",
                    "record_uid": "<firstname>;<lastname>;<email>",
                    "username": {"default": "<:umlauts><firstname>[0].<lastname>[COUNTER2]"},
                },
                "source_uid": "sourceDB",
                "user_role": "student",
                "tolerate_errors": 0,
                "verbose": True,
            }
        )

    def cleanup(self):
        self.log.info("Performing CLI_Import_v2_Tester cleanup...")
        self.log.info("Purging %r", self.tmpdir)
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for hook_fn in self.hook_fn_set:
            try:
                os.remove(hook_fn)
            except (IOError, OSError):
                self.log.warning("Failed to remove %r" % (hook_fn,))
        reset_notifier_restart_burst_limit()
        super(CLI_Import_v2_Tester, self).cleanup()
        self.log.info("CLI_Import_v2_Tester cleanup done")

    def create_config_json(self, values=None, config=None):
        """
        Creates a config file for "ucs-school-user-import".
        Default values may be overridden via a dict called values.
        >>> values = {'user_role': 'teacher', 'input:type': 'csv' }
        >>> create_config_json(values=values)
        '/tmp/config.dkgfcsdz'
        >>> create_config_json(values=values, config=DEFAULT_CONFIG)
        '/tmp/config.dkgfcsdz'
        """
        fn = tempfile.mkstemp(prefix="config.", dir=self.tmpdir)[1]
        if not config:
            config = copy.deepcopy(self.default_config)
        if values:
            for config_option, value in iteritems(values):
                config.update_entry(config_option, value)
        with open(fn, "w") as fd:
            json.dump(config, fd)
            self.log.info("Config: %r" % config)

        return fn

    def create_csv_file(
        self, person_list, sisopi_school=None, mapping=None, fn_csv=None, prefix_schools=True
    ):
        """
        Create CSV file for given persons
        >>> from univention.testing.ucsschool.importusers import Person
        >>> create_csv_file([Person('schoolA', 'student'), Person('schoolB', 'teacher')])
        '/tmp/import.sldfhgsg.csv'
        >>> create_csv_file([Person('schoolA', 'student'), Person('schoolB', 'teacher')],
            fn_csv='/tmp/import.foo.csv')
        '/tmp/import.foo.csv'
        >>> create_csv_file([Person('schoolA', 'student'), Person('schoolB', 'teacher')],
            headers={'firstname': 'Vorname', ...})
        '/tmp/import.cetjdfgj.csv'
        """
        if mapping:
            header2properties = mapping
        else:
            header2properties = self.default_config["csv"]["mapping"]

        properties2headers = {v: k for k, v in iteritems(header2properties)}

        header_row = list(header2properties)
        random.shuffle(header_row)
        self.log.info("Header row = %r", header_row)

        fn = fn_csv or tempfile.mkstemp(prefix="users.", dir=self.tmpdir)[1]
        writer = csv.DictWriter(
            open(fn, "w"), header_row, restval="", delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL
        )
        writer.writeheader()
        for person in person_list:
            if sisopi_school:
                tmp = copy.deepcopy(person)
                tmp.school = sisopi_school
                tmp.schools = [sisopi_school]
                if tmp.role != "staff":
                    tmp.school_classes = {}
                    tmp.school_classes[sisopi_school] = person.school_classes[sisopi_school]
                person_dict = tmp.map_to_dict(properties2headers, prefix_schools=prefix_schools)
            else:
                person_dict = person.map_to_dict(properties2headers, prefix_schools=prefix_schools)
            self.log.info("Person data = %r", person_dict)
            writer.writerow(person_dict)
        return fn

    def check_for_non_empty_config(self, raise_exc=True):
        base_dir = "/var/lib/ucs-school-import/configs/"
        user_config = ["user_import.json"]
        school_configs = [
            "{}.json".format(ou.name) for ou in [self.ou_A, self.ou_B, self.ou_C] if ou is not None
        ]
        configs = school_configs + user_config
        for config in configs:
            config_path = os.path.join(base_dir, config)
            if not os.path.isfile(config_path):
                continue
            with open(config_path) as config_file:
                if len(json.load(config_file)) != 0:
                    msg = (
                        'The config under "%s" seems to be non-empty. That often causes problems for '
                        'tests. Please replace it with an empty config: "{}".' % (config_path,)
                    )
                    if raise_exc:
                        raise ImportException(msg)
                    else:
                        self.log.warning("*" * 40)
                        self.log.warning(msg)
                        self.log.warning("*" * 40)

    def check_for_non_empty_pyhooks(self, raise_exc=True):
        path = "/usr/share/ucs-school-import/pyhooks"
        dir_content = [x for x in os.listdir(path) if x != "__pycache__"]
        if dir_content:
            msg = (
                "The directory {!r} seems to be non-empty: {!r} That often causes problems for tests. "
                "Please remove all files in it.".format(path, dir_content)
            )
            if raise_exc:
                raise ImportException(msg)
            else:
                self.log.warning("*" * 40)
                self.log.warning(msg)
                self.log.warning("*" * 40)

    def run_import(
        self, args, fail_on_error=True, fail_on_preexisting_config=True, fail_on_preexisting_pyhook=True
    ):
        self.check_for_non_empty_config(fail_on_preexisting_config)
        self.check_for_non_empty_pyhooks(fail_on_preexisting_pyhook)
        cmd = ["/usr/share/ucs-school-import/scripts/ucs-school-user-import", "-v"] + args
        self.log.info("Starting import: %r", cmd)
        sys.stdout.flush()
        sys.stderr.flush()
        if fail_on_error:
            try:
                exitcode = subprocess.check_call(cmd)
            except subprocess.CalledProcessError as exc:
                self.log.error("As requested raising an exception due to non-zero exit code")
                raise ImportException(
                    "Command '%r' returned non-zero exit status %r (output=%r)"
                    % (exc.cmd, exc.returncode, exc.output)
                )
        else:
            exitcode = subprocess.call(cmd)
        self.log.info("Import process exited with exit code %r", exitcode)
        return exitcode


class UniqueObjectTester(CLI_Import_v2_Tester):
    def __init__(self):
        super(UniqueObjectTester, self).__init__()
        self.unique_basenames_to_remove = []

    def cleanup(self):
        self.log.info("Removing new unique-usernames,cn=ucsschool entries...")
        if not self.lo:
            self.lo = utu.UCSTestSchool.open_ldap_connection(admin=True)
        for username in self.unique_basenames_to_remove:
            dn = "cn={},cn=unique-usernames,cn=ucsschool,cn=univention,{}".format(
                escape_dn_chars(username), self.lo.base
            )
            self.log.debug("Removing %r", dn)
            try:
                self.lo.delete(dn)
            except noObject:
                pass
            except ldapError as exc:
                self.log.error("DN %r -> %s", dn, exc)
        super(UniqueObjectTester, self).cleanup()

    def check_unique_obj(self, obj_name, prefix, next_num):
        """check if history object exists"""
        self.log.info("Checking for %s object...", obj_name)
        dn = "cn={},cn={},cn=ucsschool,cn=univention,{}".format(prefix, obj_name, self.lo.base)
        attrs = {
            "objectClass": ["ucsschoolUsername"],
            "ucsschoolUsernameNextNumber": [next_num],
            "cn": [prefix],
        }
        utils.verify_ldap_object(dn, expected_attr=attrs, strict=True, should_exist=True)
        self.log.debug(
            "%s object %r:\n%s", obj_name, dn, pprint.PrettyPrinter(indent=2).pformat(self.lo.get(dn))
        )
        self.log.info("%s object has been found and is correct.", obj_name)
