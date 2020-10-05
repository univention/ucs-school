#!/usr/share/ucs-test/runner python
## desc: Rename Class Function
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-import, ucs-school-singlemaster]

import glob
import grp
import os
import pwd
import tempfile
from pprint import pprint

from ldap.filter import filter_format

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.share import ClassShare
from ucsschool.lib.models.utils import exec_cmd
from ucsschool.lib.roles import create_ucsschool_role_string, role_school_class, role_school_class_share
from univention.uldap import getMachineConnection

try:
    from typing import Dict, Optional, Tuple

    from univention.admin.uldap import access as LoType

    MegaSuperDuperPermissionTuple = Tuple[Tuple[Tuple[str, str], str], Dict[str, Tuple[str, str, str]]]
except ImportError:
    pass


BACKUP_PATH = "/home/backup/groups"


def ldap_info(cn):  # type: (str) -> Dict[str, str]
    with ucr_test.UCSTestConfigRegistry() as ucr:
        basedn = ucr.get("ldap/base")
        lo = getMachineConnection()
        gidNumber = lo.search(filter="cn=%s" % cn, base=basedn)[0][1].get("gidNumber")
        memberUid = lo.search(filter="cn=%s" % cn, base=basedn)[0][1].get("memberUid")
        univentionShareGid = lo.search(filter="cn=%s" % cn, base=basedn)[1][1].get("univentionShareGid")
        univentionShareUid = lo.search(filter="cn=%s" % cn, base=basedn)[1][1].get("univentionShareUid")
    return {
        "gidNumber": gidNumber,
        "memberUid": memberUid,
        "univentionShareGid": univentionShareGid,
        "univentionShareUid": univentionShareUid,
    }


def check_backup(cn):  # type: (str) -> None
    print("*** Checking backup.. ")
    for _dir in glob.glob("%s/*" % BACKUP_PATH):
        if os.path.exists(_dir) and cn in _dir:
            utils.fail("%s was moved to backup" % cn)


def check_ldap(school, old_name, new_name):  # type: (str, str, str) -> None
    utils.verify_ldap_object(class_dn(old_name, school), should_exist=False)
    utils.verify_ldap_object(share_dn(old_name, school), should_exist=False)
    with ucr_test.UCSTestConfigRegistry() as ucr:
        utils.verify_ldap_object(
            class_dn(new_name, school),
            expected_attr={"ucsschoolRole": [create_ucsschool_role_string(role_school_class, school)]},
            should_exist=True,
        )
        utils.verify_ldap_object(
            share_dn(new_name, school),
            expected_attr={
                "ucsschoolRole": [create_ucsschool_role_string(role_school_class_share, school)]
            },
            should_exist=True,
        )


def share_dn(class_name, school):  # type: (str, str) -> str
    with ucr_test.UCSTestConfigRegistry() as ucr:
        return "cn=%s,cn=klassen,cn=shares,ou=%s,%s" % (class_name, school, ucr.get("ldap/base"))


def class_dn(class_name, school):  # type: (str, str) -> str
    with ucr_test.UCSTestConfigRegistry() as ucr:
        return "cn=%s,cn=klassen,cn=schueler,cn=groups,ou=%s,%s" % (
            class_name,
            school,
            ucr.get("ldap/base"),
        )


def share_path(class_name, school):  # type: (str, str) -> str
    return "/home/%s/groups/klassen/%s" % (school, class_name)


def permissions(dir_path, lo):  # type: (str, LoType) -> MegaSuperDuperPermissionTuple
    """Returns a tuple =
        (( dir_permissions(octal), owner), group ),
        { path.basename(files): ( permissions(octal), owner, group ) }
    """
    result = {}
    st = os.stat(dir_path)
    try:
        grp_name1 = grp.getgrgid(st.st_gid)[0]
        print(
            "*** Found group {!r} with gidNumber={!r} using grp.getgrgid().".format(grp_name1, st.st_gid)
        )
    except KeyError:
        # grp.getgrgid() uses nscd which uses group-to-file which might not have been updated yet.
        print("*** Could not find group with gidNumber={!r} using grp.getgrgid().".format(st.st_gid))
        grp_name1 = None
    # compare name with the one in LDAP
    filter_s = filter_format("(&(objectClass=posixGroup)(gidNumber=%s))", (str(st.st_gid),))
    res = lo.search(filter_s, attr=["cn"])
    if len(res) != 1:
        raise RuntimeError("Could not find group with fileter {!r} in LDAP.".format(filter_s))
    grp_name2 = res[0][1]["cn"][0]
    print("*** Found group {!r} with gidNumber={!r} in LDAP.".format(grp_name2, st.st_gid))
    if grp_name1:
        assert grp_name1 == grp_name2
    grp_name = grp_name1

    dir_permissions = ((oct(st.st_mode), pwd.getpwuid(st.st_uid)[0]), grp_name)
    for f in glob.glob("{}/*".format(dir_path)):
        if not os.path.islink(f):
            st = os.stat(f)
            result.update(
                {
                    os.path.basename(f): (
                        oct(st.st_mode),
                        pwd.getpwuid(st.st_uid)[0],
                        grp.getgrgid(st.st_gid)[0],
                    )
                }
            )
            if os.path.isdir(f):
                sub_result = permissions(f, lo)
                result = dict(result.items() + sub_result.items())
    return dir_permissions, result


def check_permissions(old_dir, old_dir_permissions, new_dir, new_dir_permissions):
    # type: (str, MegaSuperDuperPermissionTuple, str, MegaSuperDuperPermissionTuple) -> None
    current = old_dir_permissions[0][1]
    expected = os.path.basename(old_dir)
    if current != expected:
        utils.fail("%r is owned by the wrong group: %r, expected: %r" % (expected, current, expected))

    current = new_dir_permissions[0][1]
    expected = os.path.basename(new_dir)
    if current != expected:
        utils.fail("%r is owned by the wrong group: %r, expected: %r" % (expected, current, expected))

    if old_dir_permissions[0][0] != new_dir_permissions[0][0]:
        utils.fail(
            "Permissions are changed old= %r, new= %r"
            % (old_dir_permissions[0][0], new_dir_permissions[0][0])
        )
    if old_dir_permissions[1] != new_dir_permissions[1]:
        utils.fail(
            "Permissions are changed old= %r, new= %r" % (old_dir_permissions[1], new_dir_permissions[1])
        )


def test_rename_class(schoolenv, school, old_name, new_name, should_fail=False):
    # type: (utu.UCSTestSchool, str, str, str, Optional[bool]) -> None
    old_dir = share_path(old_name, school)

    if os.path.exists(old_dir):
        fp = tempfile.NamedTemporaryFile(suffix=".import", dir=old_dir)
    else:
        if should_fail:
            fp = tempfile.NamedTemporaryFile(suffix=".import")
        else:
            utils.fail("Share path does not exist: %s" % old_dir)
    fp.write("%s\t%s" % (old_name, new_name))
    fp.flush()
    fp.seek(0)
    print("*** Import tempfile {!r} created:\n-----\n{}\n-----".format(fp.name, fp.read()))

    if os.path.exists(old_dir):
        old_dir_permissions = permissions(old_dir, schoolenv.lo)
        old_ldap_info = ldap_info(old_name)

    # Rename the class
    print("*** Renaming class {!r} to {!r}".format(old_name, new_name))
    cmd = ["/usr/share/ucs-school-import/scripts/rename_class", fp.name]
    returncode, out, err = exec_cmd(cmd, log=True, raise_exc=False)
    print("*** returncode of 'rename_class' command: {!r}".format(returncode))
    if returncode == 0:
        utils.wait_for_replication_and_postrun()

    lo = getMachineConnection()
    print("*** SchoolClass.get_all(lo, {!r}):".format(school))
    pprint([sc.to_dict() for sc in SchoolClass.get_all(lo, school)])
    print("*** ClassShare.get_all(lo, {!r}):".format(school))
    pprint([cs.to_dict() for cs in ClassShare.get_all(lo, school)])
    pprint([(cs.name, cs.get_udm_object(lo)["path"]) for cs in ClassShare.get_all(lo, school)])
    exec_cmd(["find", "/home/{}/groups/klassen/".format(school), "-ls"], log=True)

    if "ERROR" in out and not should_fail:
        utils.fail("Error not detected:\n%s" % out)
    elif "ERROR" not in out:
        utils.wait_for_replication_and_postrun()

        # obvious check: old objects are renamed to new names in ldap
        check_ldap(school, old_name, new_name)

        # the share directory in file system should not be removed/moved to backup directory
        check_backup(old_name)

        # the share object should use the same uidNumber/gidNumber settings
        # the renamed group object should use the same gidNumber
        # the renamed group should still include the same users as before
        new_ldap_info = ldap_info(new_name)
        if old_ldap_info != new_ldap_info:
            utils.fail(
                "%s has changed after renaming the class"
                % [x for x in old_ldap_info if old_ldap_info[x] != new_ldap_info[x]][0]
            )

        # the renamed share object should be still accessible
        new_dir = share_path(new_name, school)
        if os.path.exists(new_dir):
            new_dir_permissions = permissions(new_dir, schoolenv.lo)
            check_permissions(old_dir, old_dir_permissions, new_dir, new_dir_permissions)
    print("*** OK.")


def create_two_users(schoolenv, school, class_name):  # type: (utu.UCSTestSchool, str, str) -> (str, str)
    tea, teadn = schoolenv.create_user(school, classes=class_name, is_teacher=True)
    stu, studn = schoolenv.create_user(school, classes=class_name)
    utils.wait_for_replication_and_postrun()
    return tea, stu


def main():  # type: () -> None
    with ucr_test.UCSTestConfigRegistry() as ucr:
        with utu.UCSTestSchool() as schoolenv:
            school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))

            old_name = "%s-%s" % (school, uts.random_name())
            new_name = "%s-%s" % (school, uts.random_name())
            test_rename_class(schoolenv, school, old_name, new_name, should_fail=True)

            old_name = "%s-%s" % (school, uts.random_name())
            new_name = "%s-%s" % (school, uts.random_name())
            create_two_users(schoolenv, school, old_name)
            test_rename_class(schoolenv, school, old_name, new_name)

            old_name = "%s-%s" % (school, uts.random_name())
            create_two_users(schoolenv, school, old_name)
            test_rename_class(schoolenv, school, old_name, new_name, should_fail=True)


if __name__ == "__main__":
    main()
