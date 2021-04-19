import datetime
import enum
import logging
import os
import pprint
import random
import sys
import tempfile
import time

try:
    from typing import Any, Dict, List, Optional, Tuple, Type
except ImportError:
    pass

import pytest
import six
from ldap.filter import filter_format

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm as udm_test
from ucsschool.importer.configuration import Configuration, setup_configuration as _setup_configuration
from ucsschool.importer.exceptions import UcsSchoolImportError
from ucsschool.importer.factory import setup_factory as _setup_factory
from ucsschool.importer.frontend.user_import_cmdline import (
    UserImportCommandLine as _UserImportCommandLine,
)
from ucsschool.importer.models.import_user import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
    ImportUser,
)
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.share import ClassShare, MarketplaceShare, WorkGroupShare
from ucsschool.lib.models.user import SchoolAdmin, Staff, Student, Teacher, TeachersAndStaff
from ucsschool.lib.models.utils import get_file_handler
from ucsschool.lib.roles import (
    role_marketplace_share,
    role_school_admin,
    role_school_class,
    role_school_class_share,
    role_staff,
    role_student,
    role_teacher,
    role_workgroup,
    role_workgroup_share,
)

IMPORT_CONFIG = {
    "active": "/var/lib/ucs-school-import/configs/user_import.json",
    "bak": "/var/lib/ucs-school-import/configs/user_import.json.bak.{}".format(
        datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    ),
    "default": "/usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json",
}
MACHINE_ACCOUNT_PW_FILE = "/etc/machine.secret"
MAPPED_UDM_PROPERTIES = (
    "title",
    "description",
    "employeeType",
    "organisation",
    "phone",
    "uidNumber",
    "gidNumber",
)  # keep in sync with kelvin-api/tests/conftest.py::MAPPED_UDM_PROPERTIES
IMPORT_CONFIG_KWARGS = {
    "configuration_checks": ["defaults", "mapped_udm_properties"],
    "dry_run": False,
    "logfile": "/var/log/univention/ucsschool-kelvin-rest-api/http.log",
    "scheme": {
        "firstname": "<lastname>",
        "username": {"default": "<:lower>test.<firstname>[:2].<lastname>[:3]"},
    },
    "skip_tests": ["uniqueness"],
    "mapped_udm_properties": MAPPED_UDM_PROPERTIES,
    "source_uid": "TESTID",
    "verbose": True,
}
_ucs_school_import_framework_initialized = False
_ucs_school_import_framework_error = None  # type: Optional[InitialisationError]


class InitialisationError(Exception):
    pass


class UCSSchoolType(enum.Enum):
    pass


class GroupType(UCSSchoolType):
    SchoolClass = "SchoolClass"
    WorkGroup = "WorkGroup"


class ShareType(UCSSchoolType):
    ClassShare = "ClassShare"
    MarketplaceShare = "MarketplaceShare"
    WorkGroupShare = "WorkGroupShare"


class UserType(UCSSchoolType):
    SchoolAdmin = "SchoolAdmin"
    Staff = "Staff"
    Student = "Student"
    Teacher = "Teacher"
    TeachersAndStaff = "TeachersAndStaff"


@pytest.fixture(scope="session")
def model_ldap_object_classes():
    def _func(obj_type):  # type: (str) -> List[str]
        return {
            GroupType.SchoolClass: ["ucsschoolGroup"],
            GroupType.WorkGroup: ["ucsschoolGroup"],
            ShareType.ClassShare: ["ucsschoolShare"],
            ShareType.MarketplaceShare: ["ucsschoolShare"],
            ShareType.WorkGroupShare: ["ucsschoolShare"],
            UserType.SchoolAdmin: ["ucsschoolAdministrator"],
            UserType.Staff: ["ucsschoolStaff"],
            UserType.Student: ["ucsschoolStudent"],
            UserType.Teacher: ["ucsschoolTeacher"],
            UserType.TeachersAndStaff: ["ucsschoolStaff", "ucsschoolTeacher"],
        }[obj_type]

    return _func


@pytest.fixture(scope="session")
def model_school_object_class():
    def _func(obj_type):  # type: (str) -> Type[UCSSchoolHelperAbstractClass]
        return {
            GroupType.SchoolClass: SchoolClass,
            GroupType.WorkGroup: WorkGroup,
            ShareType.ClassShare: ClassShare,
            ShareType.MarketplaceShare: MarketplaceShare,
            ShareType.WorkGroupShare: WorkGroupShare,
            UserType.SchoolAdmin: SchoolAdmin,
            UserType.Staff: Staff,
            UserType.Student: Student,
            UserType.Teacher: Teacher,
            UserType.TeachersAndStaff: TeachersAndStaff,
        }[obj_type]

    return _func


@pytest.fixture(scope="session")
def model_ucsschool_roles():
    def _func(obj_type, ous):  # type: (str, List[str]) -> List[str]
        roles = {
            GroupType.SchoolClass: [role_school_class],
            GroupType.WorkGroup: [role_workgroup],
            ShareType.ClassShare: [role_school_class_share],
            ShareType.MarketplaceShare: [role_marketplace_share],
            ShareType.WorkGroupShare: [role_workgroup_share],
            UserType.SchoolAdmin: [role_school_admin],
            UserType.Staff: [role_staff],
            UserType.Student: [role_student],
            UserType.Teacher: [role_teacher],
            UserType.TeachersAndStaff: [role_staff, role_teacher],
        }[obj_type]
        return ["{}:school:{}".format(role, ou) for role in roles for ou in ous]

    return _func


@pytest.fixture(scope="session")
def model_udm_module():
    def _func(obj_type):  # type: (str) -> str
        return {
            GroupType.SchoolClass: "groups/group",
            GroupType.WorkGroup: "groups/group",
            ShareType.ClassShare: "shares/share",
            ShareType.MarketplaceShare: "shares/share",
            ShareType.WorkGroupShare: "shares/share",
            UserType.SchoolAdmin: "users/user",
            UserType.Staff: "users/user",
            UserType.Student: "users/user",
            UserType.Teacher: "users/user",
            UserType.TeachersAndStaff: "users/user",
        }[obj_type]

    return _func


@pytest.fixture(scope="session")
def model_ldap_container(ucr_ldap_base):
    def _func(obj_type, ou):  # type: (str, str) -> str
        groups_cn = "cn=groups,ou={},{}".format(ou, ucr_ldap_base)
        shares_cn = "cn=shares,ou={},{}".format(ou, ucr_ldap_base)
        users_cn = "cn=users,ou={},{}".format(ou, ucr_ldap_base)
        return {
            GroupType.SchoolClass: "cn=klassen,cn=schueler,{}".format(groups_cn),
            GroupType.WorkGroup: "cn=schueler,{}".format(groups_cn),
            ShareType.ClassShare: "cn=klassen,{}".format(shares_cn),
            ShareType.MarketplaceShare: shares_cn,
            ShareType.WorkGroupShare: shares_cn,
            UserType.SchoolAdmin: "cn=admins-{},cn=ouadmins,cn=groups,{}".format(
                ou.lower(), ucr_ldap_base
            ),
            UserType.Staff: "cn=mitarbeiter,{}".format(users_cn),
            UserType.Student: "cn=schueler,{}".format(users_cn),
            UserType.Teacher: "cn=lehrer,{}".format(users_cn),
            UserType.TeachersAndStaff: "cn=lehrer und mitarbeiter,{}".format(users_cn),
        }[obj_type]

    return _func


@pytest.fixture(scope="session")
def user_groups(ucr_ldap_base, model_ldap_container):
    def _func(user_type, ou):  # type: (str, str) -> List[str]
        groups_cn = "cn=groups,ou={},{}".format(ou, ucr_ldap_base)
        user_group = {
            UserType.SchoolAdmin: "cn=admins-{},cn=ouadmins,cn=groups,{}".format(
                ou.lower(), ucr_ldap_base
            ),
            UserType.Staff: "cn=mitarbeiter-{},{}".format(ou.lower(), groups_cn),
            UserType.Student: "cn=schueler-{},{}".format(ou.lower(), groups_cn),
            UserType.Teacher: "cn=lehrer-{},{}".format(ou.lower(), groups_cn),
            UserType.TeachersAndStaff: "cn=lehrer und mitarbeiter-{},{}".format(ou.lower(), groups_cn),
        }[user_type]
        dom_users = "cn=Domain Users {0},cn=groups,ou={0},{1}".format(ou, ucr_ldap_base)
        return [dom_users, user_group]

    return _func


@pytest.fixture(scope="session")
def random_int():
    return uts.random_int


@pytest.fixture(scope="session")
def random_username():
    return uts.random_username


@pytest.fixture(scope="session")
def ucr():
    """Instance of UCSTestConfigRegistry"""
    with ucr_test.UCSTestConfigRegistry() as ucr:
        yield ucr


@pytest.fixture(scope="session")
def fqdn(ucr):
    """hostname.domainname"""
    ret = os.environ.get("UCS_TEST_HOSTNAME")
    return ret or "{hostname}.{domainname}".format(**ucr)


@pytest.fixture(scope="session")
def admin_username(ucr):
    """Username of the Admin account"""
    ret = os.environ.get("UCS_TEST_ADMIN_USERNAME")
    if not ret:
        ret = ucr.get("tests/domainadmin/account")
        if ret:
            ret = ret.split(",")[0].split("=")[-1]
        else:
            ret = "Administrator"
    return ret


@pytest.fixture(scope="session")
def admin_password(ucr):
    """Password of the Admin account"""
    ret = os.environ.get("UCS_TEST_ADMIN_PASSWORD")
    return ret or ucr.get("tests/domainadmin/pwd", "univention")


@pytest.fixture(scope="session")
def machine_account_dn(ucr):
    return ucr["ldap/hostdn"]


@pytest.fixture(scope="session")
def machine_password():
    with open(MACHINE_ACCOUNT_PW_FILE, "r") as fp:
        return fp.read().strip()


@pytest.fixture
def schoolenv():
    with utu.UCSTestSchool() as _schoolenv:
        yield _schoolenv


@pytest.fixture
def create_ou(schoolenv, ucr_hostname):
    def _func(**kwargs):  # type: (**Any) -> Tuple[str, str]
        kwargs["name_edudc"] = kwargs.get("name_edudc") or ucr_hostname
        return schoolenv.create_ou(**kwargs)

    return _func


@pytest.fixture
def lo(schoolenv):
    return schoolenv.lo


@pytest.fixture(scope="session")
def udm_session():
    with udm_test.UCSTestUDM() as udm:
        yield udm


@pytest.fixture
def create_import_user(lo):
    def _func(**kwargs):  # type: (**Any) -> ImportUser
        kls = random.choice((ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff))
        obj = kls(**kwargs)
        res = obj.create(lo)
        if not res:
            raise RuntimeError("Creating {!r} failed with kwargs {!r}".format(kls, kwargs))
        return obj

    return _func


@pytest.fixture
def get_import_user(import_config, lo):
    def _func(dn, school=None):  # type: (str, Optional[str]) -> ImportUser
        user = ImportUser.from_dn(dn, school, lo)
        udm_obj = user.get_udm_object(lo)
        user.udm_properties = dict((k, udm_obj[k]) for k in import_config["mapped_udm_properties"])
        return user

    return _func


@pytest.fixture(scope="session")
def mail_domain(udm_session, ucr_domainname, ucr, ucr_ldap_base):
    if ucr_domainname not in ucr.get("mail/hosteddomains", "").split():
        try:
            udm_session.create_object(
                "mail/domain",
                set={"name": ucr_domainname},
                position="cn=domain,cn=mail,{}".format(ucr_ldap_base),
            )
        except udm_test.UCSTestUDM_CreateUDMObjectFailed as exc:
            print(exc)

    return ucr_domainname


@pytest.fixture(scope="session")
def ucr_domainname(ucr):
    return ucr["domainname"]


@pytest.fixture(scope="session")
def ucr_hostname(ucr):
    return ucr["hostname"]


@pytest.fixture(scope="session")
def ucr_is_singlemaster(ucr):
    return ucr.is_true("ucsschool/singlemaster", False)


@pytest.fixture(scope="session")
def ucr_ldap_base(ucr):
    return ucr["ldap/base"]


@pytest.fixture(scope="session")
def user_ldap_attributes(
    random_username, model_ucsschool_roles, model_udm_module, model_ldap_object_classes, user_groups
):
    def _func(ous, user_type):  # type: (List[str], UserType) -> Dict[str, List[str]]
        """First OU in `ous` will be the users LDAP position -> `school`."""
        assert isinstance(ous, list)
        name = random_username()[:15]
        groups = []
        for ou in ous:
            groups.extend(user_groups(user_type, ou))
        return {
            "givenName": [name[: len(name) / 2]],
            "sn": [name[len(name) / 2 :]],
            "uid": [name],
            "univentionBirthday": [
                "19{}-0{}-{}{}".format(
                    2 * uts.random_int(),
                    uts.random_int(1, 9),
                    uts.random_int(0, 2),
                    uts.random_int(1, 8),
                )
            ],
            "groups": groups,
            "objectClass": model_ldap_object_classes(user_type),
            "ucsschoolRole": model_ucsschool_roles(user_type, ous),
            "departmentNumber": [ous[0]],
            "ucsschoolSchool": ous,
            "univentionObjectType": [model_udm_module(user_type)],
        }

    return _func


@pytest.fixture(scope="session")
def user_school_attributes(user_ldap_attributes):
    def _func(ous, user_type, ldap_attrs=None):
        # type: (List[str], UserType, Optional[Dict[str, List[str]]]) -> Dict[str, str]
        """First OU in `ous` will be the users LDAP position -> `school`."""
        assert isinstance(ous, list)
        attrs = ldap_attrs or user_ldap_attributes(ous, user_type)
        return {
            "name": attrs["uid"][0],
            "firstname": attrs["givenName"][0],
            "lastname": attrs["sn"][0],
            "birthday": attrs["univentionBirthday"][0],
            "school": ous[0],
            "schools": ous,
            "model_ucsschool_roles": attrs["ucsschoolRole"],
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_ldap_attributes(
    mail_domain,
    random_username,
    ucr_ldap_base,
    model_ucsschool_roles,
    model_udm_module,
    model_ldap_container,
    model_ldap_object_classes,
):
    def _func(ou):  # type: (str) -> Dict[str, Any]
        name = random_username()
        group_dn = "cn={}-{},{}".format(ou, name, model_ldap_container(GroupType.WorkGroup, ou))
        user_name = "demo_student"
        user_dn = "uid={},cn=schueler,cn=users,ou={},{}".format(user_name, ou, ucr_ldap_base)
        return {
            "cn": ["{}-{}".format(ou, name)],
            "description": ["{} {}".format(random_username(), random_username())],
            "mailPrimaryAddress": ["wg-{}@{}".format(name, mail_domain)],
            "memberUid": [user_name],
            "objectClass": model_ldap_object_classes(GroupType.WorkGroup),
            "ucsschoolRole": model_ucsschool_roles(GroupType.WorkGroup, [ou]),
            "univentionAllowedEmailGroups": [group_dn],
            "univentionAllowedEmailUsers": [user_dn],
            "uniqueMember": [user_dn],
            "univentionObjectType": [model_udm_module(GroupType.WorkGroup)],
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_school_attributes(workgroup_ldap_attributes):
    def _func(ou, ldap_attrs=None):  # type: (str, Optional[Dict[str, Any]]) -> Dict[str, Any]
        attrs = ldap_attrs or workgroup_ldap_attributes(ou)
        return {
            "name": attrs["cn"][0],
            "description": attrs["description"][0],
            "email": attrs["mailPrimaryAddress"][0],
            "allowed_email_senders_users": attrs["univentionAllowedEmailUsers"],
            "allowed_email_senders_groups": attrs["univentionAllowedEmailGroups"],
            "school": ou,
            "model_ucsschool_roles": attrs["ucsschoolRole"],
            "users": attrs["uniqueMember"],
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_share_ldap_attributes(
    random_username,
    ucr_domainname,
    ucr_hostname,
    ucr_ldap_base,
    model_ldap_object_classes,
    model_ucsschool_roles,
    model_udm_module,
):
    def _func(ou):  # type: (str) -> Dict[str, Any]
        name = random_username()
        if ucr_is_singlemaster:
            share_host = "{}.{}".format(ucr_hostname, ucr_domainname)
        else:
            share_host = "dc{}-01.{}".format(ou, ucr_domainname)
        return {
            "cn": ["{}-{}".format(ou, name)],
            "objectClass": model_ldap_object_classes(ShareType.WorkGroupShare),
            "ucsschoolRole": model_ucsschool_roles(ShareType.WorkGroupShare, [ou]),
            "univentionObjectType": [model_udm_module(ShareType.WorkGroupShare)],
            "univentionShareDirectoryMode": ["0770"],
            "univentionShareHost": [share_host],
            "univentionSharePath": ["/home/{0}/groups/{0}-{1}".format(ou, name)],
            "univentionShareSambaBrowseable": "yes",
            "univentionShareSambaCreateMode": "0770",
            "univentionShareSambaDirectoryMode": "0770",
            "univentionShareSambaForceGroup": "+{}-{}".format(ou, name),
            "univentionShareSambaName": "{}-{}".format(ou, name),
            "univentionShareSambaNtAclSupport": "1",
            "univentionShareSambaWriteable": "yes",
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_share_school_attributes(workgroup_share_ldap_attributes):
    def _func(ou, ldap_attrs=None):  # type: (str, Optional[Dict[str, Any]]) -> Dict[str, Any]
        attrs = ldap_attrs or workgroup_share_ldap_attributes(ou)
        return {
            "name": attrs["cn"][0],
            "school": ou,
            "model_ucsschool_roles": attrs["ucsschoolRole"],
        }

    return _func


@pytest.fixture
def random_logger():
    with tempfile.NamedTemporaryFile() as f:
        handler = get_file_handler("DEBUG", f.name)
        logger = logging.getLogger(f.name)
        logger.addHandler(handler)
        logger.setLevel("DEBUG")
        yield logger


@pytest.fixture(scope="session")
def init_ucs_school_import_framework():
    def _func(**config_kwargs):
        global _ucs_school_import_framework_initialized, _ucs_school_import_framework_error

        if _ucs_school_import_framework_initialized:
            return Configuration()
        if _ucs_school_import_framework_error:
            # prevent "Changing the configuration is not allowed." error if we
            # return here after raising an InitialisationError
            etype, exc, etraceback = sys.exc_info()
            six.reraise(_ucs_school_import_framework_error, exc, etraceback)

        _config_args = IMPORT_CONFIG_KWARGS
        _config_args.update(config_kwargs)
        _ui = _UserImportCommandLine()
        _config_files = _ui.configuration_files
        logger = logging.getLogger("univention.testing.ucsschool")
        try:
            config = _setup_configuration(_config_files, **_config_args)
            if "mapped_udm_properties" not in config.get("configuration_checks", []):
                raise UcsSchoolImportError(
                    'Missing "mapped_udm_properties" in configuration checks, e.g.: '
                    '{.., "configuration_checks": ["defaults", "mapped_udm_properties"], ..}'
                )
            _ui.setup_logging(config["verbose"], config["logfile"])
            _setup_factory(config["factory"])
        except UcsSchoolImportError as exc:
            logger.exception("Error initializing UCS@school import framework: %s", exc)
            etype, exc, etraceback = sys.exc_info()
            _ucs_school_import_framework_error = InitialisationError(str(exc))
            six.reraise(etype, exc, etraceback)
        logger.info("------ UCS@school import tool configured ------")
        logger.info("Used configuration files: %s.", config.conffiles)
        logger.info("Using command line arguments: %r", _config_args)
        logger.info("Configuration is:\n%s", pprint.pformat(config))
        _ucs_school_import_framework_initialized = True
        return config

    return _func


@pytest.fixture(scope="session")
def import_config(init_ucs_school_import_framework):
    return init_ucs_school_import_framework()


class OUCloner(object):
    """
    Create a OU bypassing UDM.

    Objects are mostly OK. There might be a few inconsistencies with groups, shares and Samba IDs.

    oc = OUCloner(lo)
    oc.clone_ou("DEMOSCHOOL", "testou1234")
    """

    def __init__(self, lo):
        self.lo = lo
        self.sid_base, max_rid = self.get_max_rid()
        self.next_rid = max_rid + 2000
        max_gid, max_uid = self.get_max_gid_uid()
        self.next_gid = max_gid + 2000
        self.next_uid = max_uid + 2000

    @staticmethod
    def replace_case_sesitive_and_lower(s, ori, new):  # type: (str, str, str) -> str
        new_s = s.replace(ori, new)
        return new_s.replace(ori.lower(), new.lower())

    def get_max_rid(self):  # type: () -> Tuple[str, int]
        sid_base = self.lo.search("sambaDomainName=*", attr=["sambaSID"])[0][1]["sambaSID"][0]
        max_rid = 0
        for _, v in self.lo.search(filter_format("sambaSID=%s-*", (sid_base,)), attr=["sambaSID"]):
            rid = int(v["sambaSID"][0].rsplit("-", 1)[1])
            max_rid = max(rid, max_rid)
        return sid_base, max_rid

    def get_max_gid_uid(self):  # type: () -> Tuple[int, int]
        max_gid = max_uid = 0
        for _, v in self.lo.search(
            "(&(|(objectClass=posixAccount)(objectClass=posixGroup))(|(gidNumber=*)(uidNumber=*)))",
            attr=["gidNumber", "uidNumber"],
        ):
            try:
                gid = int(v["gidNumber"][0])
                max_gid = max(gid, max_gid)
            except KeyError:
                pass
            try:
                uid = int(v["uidNumber"][0])
                max_uid = max(uid, max_uid)
            except KeyError:
                pass
        return max_gid, max_uid

    def clone_object(self, dn_ori, attrs_ori, ori_ou, new_ou):
        # type: (str, Dict[str, List[str]], str, str) -> None
        dn_new = self.replace_case_sesitive_and_lower(dn_ori, ori_ou, new_ou)
        attrs_new = {
            self.replace_case_sesitive_and_lower(key, ori_ou, new_ou): [
                self.replace_case_sesitive_and_lower(v, ori_ou, new_ou) for v in values
            ]
            for key, values in six.iteritems(attrs_ori)
        }
        for k, v in six.iteritems(attrs_new):
            if k == "displayName":
                attrs_new[k] = "{} ({})".format(v[0], new_ou)
            elif k == "sambaSID":
                attrs_new[k] = "{}-{}".format(self.sid_base, self.next_rid)
                self.next_rid += 1
            elif k == "gidNumber" and "cn=computers" not in dn_ori:
                attrs_new[k] = str(self.next_gid)
                self.next_gid += 1
            elif k == "uid" and dn_ori.startswith("uid="):
                attrs_new[k] = "{}_{}".format(v[0], new_ou)
                dn_new = dn_new.replace("uid={},".format(v[0]), "uid={},".format(attrs_new[k]))
            elif k == "uidNumber":
                attrs_new[k] = str(self.next_uid)
                self.next_uid += 1
        print("Adding {!r}...".format(dn_new))
        self.lo.add(dn_new, attrs_new.items())

    def clone_ou(self, ori_ou, new_ou):  # type: (str, str) -> None
        t0 = time.time()
        print("Creating copy of OU {!r} as {!r}...".format(ori_ou, new_ou))
        self.clone_ou_objects(ori_ou, new_ou)
        self.clone_global_groups(ori_ou, new_ou)
        self.update_global_groups(ori_ou, new_ou)
        print("Finished in {:.2f} seconds.".format(time.time() - t0))

    def clone_ou_objects(self, ori_ou, new_ou):  # type: (str, str) -> None
        filter_s = filter_format("ou=%s,%s", (ori_ou, self.lo.base))
        ori_data = self.lo.search(base=filter_s, scope="sub")
        ori_data.sort(key=lambda x: len(x[0]))
        # create users last, so their primary group already exists
        ori_data.sort(key=lambda x: x[0].startswith("uid="))
        for dn_ori, attrs_ori in ori_data:
            self.clone_object(dn_ori, attrs_ori, ori_ou, new_ou)

    def clone_global_groups(self, ori_ou, new_ou):  # type: (str, str) -> None
        group_dns = [
            dn.format(ou=ori_ou, basedn=self.lo.base)
            for dn in (
                "cn=OU{ou}-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{basedn}",
                "cn=OU{ou}-Member-Edukativnetz,cn=ucsschool,cn=groups,{basedn}",
                "cn=OU{ou}-Klassenarbeit,cn=ucsschool,cn=groups,{basedn}",
                "cn=OU{ou}-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{basedn}",
                "cn=OU{ou}-DC-Edukativnetz,cn=ucsschool,cn=groups,{basedn}",
            )
        ]
        group_dns.append(
            "cn=admins-{ou},cn=ouadmins,cn=groups,{basedn}".format(
                ou=ori_ou.lower(), basedn=self.lo.base
            )
        )
        for dn_ori in group_dns:
            attrs_ori = self.lo.get(dn_ori)
            self.clone_object(dn_ori, attrs_ori, ori_ou, new_ou)

    def update_global_groups(self, ori_ou, new_ou):  # type: (str, str) -> None
        for group_dn in (
            dn.format(self.lo.base)
            for dn in (
                "cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}",
                "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}",
                "cn=Member-Edukativnetz,cn=ucsschool,cn=groups,{}",
                "cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}",
            )
        ):
            attrs_ori = self.lo.get(group_dn, attr=["memberUid", "uniqueMember"])
            attrs_new = {}
            for key, ori_values in six.iteritems(attrs_ori):
                new_values = [
                    self.replace_case_sesitive_and_lower(v, ori_ou, new_ou) for v in ori_values
                ]
                if new_values != ori_values:
                    # DN of original value was replaced but should be kept. Keep original order.
                    new_values = ori_values + [v for v in new_values if v not in ori_values]
                    attrs_new[key] = new_values
            if attrs_new:
                ml = [(k, v, attrs_new[k]) for k, v in six.iteritems(attrs_ori)]
                print("Modifying {!r}...".format(group_dn))
                self.lo.modify(group_dn, ml)
            else:
                print("Unchanged: {!r}.".format(group_dn))
