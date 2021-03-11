import enum
import os

try:
    from typing import Any, Dict, List, Optional, Tuple, Type
except ImportError:
    pass

import pytest

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm as udm_test
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.share import ClassShare, MarketplaceShare, WorkGroupShare
from ucsschool.lib.models.user import SchoolAdmin, Staff, Student, Teacher, TeachersAndStaff
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

MACHINE_ACCOUNT_PW_FILE = "/etc/machine.secret"


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
def user_ldap_attributes(random_username, model_ucsschool_roles, model_ldap_object_classes, user_groups):
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
            "univentionObjectType": ["users/user"],
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
            "univentionObjectType": ["groups/group"],
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
            "univentionObjectType": ["shares/share"],
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
