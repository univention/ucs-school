import enum
import logging
import os
import pwd
import random
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type  # noqa: F401

import pytest

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm as udm_test
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
from univention.testing.ucsschool.importusers import get_mail_domain

if TYPE_CHECKING:
    from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass  # noqa: F401


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
    with open(MACHINE_ACCOUNT_PW_FILE) as fp:
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
    # ucs-test-ucsschool must not depend on ucs-school-import package
    from ucsschool.importer.models.import_user import (  # noqa: F401
        ImportStaff,
        ImportStudent,
        ImportTeacher,
        ImportTeachersAndStaff,
        ImportUser,
    )

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
    # ucs-test-ucsschool must not depend on ucs-school-import package
    from ucsschool.importer.models.import_user import ImportUser

    def _func(dn, school=None):  # type: (str, Optional[str]) -> ImportUser
        user = ImportUser.from_dn(dn, school, lo)
        udm_obj = user.get_udm_object(lo)
        user.udm_properties = {k: udm_obj[k] for k in import_config["mapped_udm_properties"]}
        return user

    return _func


@pytest.fixture(scope="session")
def mail_domain():
    return get_mail_domain()


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
    def _func(ous, user_type):  # type: (List[str], UserType) -> Dict[str, List[bytes]]
        """First OU in `ous` will be the users LDAP position -> `school`."""
        assert isinstance(ous, list)
        name = random_username()[:15]
        groups = []
        for ou in ous:
            groups.extend(user_groups(user_type, ou))
        return {
            "givenName": [name[: len(name) // 2].encode("UTF-8")],
            "sn": [name[len(name) // 2 :].encode("UTF-8")],
            "uid": [name.encode("UTF-8")],
            "univentionBirthday": [
                "19{}-0{}-{}{}".format(
                    2 * uts.random_int(),
                    uts.random_int(1, 9),
                    uts.random_int(0, 2),
                    uts.random_int(1, 8),
                ).encode("UTF-8")
            ],
            "groups": [x.encode("UTF-8") for x in groups],
            "objectClass": [x.encode("UTF-8") for x in model_ldap_object_classes(user_type)],
            "ucsschoolRole": [x.encode("UTF-8") for x in model_ucsschool_roles(user_type, ous)],
            "departmentNumber": [ous[0].encode("UTF-8")],
            "ucsschoolSchool": [x.encode("UTF-8") for x in ous],
            "univentionObjectType": [model_udm_module(user_type).encode("UTF-8")],
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
            "name": attrs["uid"][0].decode("UTF-8"),
            "firstname": attrs["givenName"][0].decode("UTF-8"),
            "lastname": attrs["sn"][0].decode("UTF-8"),
            "birthday": attrs["univentionBirthday"][0].decode("UTF-8"),
            "school": ous[0],
            "schools": ous,
            "model_ucsschool_roles": [x.decode("UTF-8") for x in attrs["ucsschoolRole"]],
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
            "cn": ["{}-{}".format(ou, name).encode("UTF-8")],
            "description": ["{} {}".format(random_username(), random_username()).encode("UTF-8")],
            "mailPrimaryAddress": ["wg-{}@{}".format(name, mail_domain).encode("UTF-8")],
            "memberUid": [user_name.encode("UTF-8")],
            "objectClass": [x.encode("UTF-8") for x in model_ldap_object_classes(GroupType.WorkGroup)],
            "ucsschoolRole": [
                x.encode("UTF-8") for x in model_ucsschool_roles(GroupType.WorkGroup, [ou])
            ],
            "univentionAllowedEmailGroups": [group_dn.encode("UTF-8")],
            "univentionAllowedEmailUsers": [user_dn.encode("UTF-8")],
            "uniqueMember": [user_dn.encode("UTF-8")],
            "univentionObjectType": [model_udm_module(GroupType.WorkGroup).encode("UTF-8")],
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_school_attributes(workgroup_ldap_attributes):
    def _func(ou, ldap_attrs=None):  # type: (str, Optional[Dict[str, Any]]) -> Dict[str, Any]
        attrs = ldap_attrs or workgroup_ldap_attributes(ou)
        return {
            "name": attrs["cn"][0].decode("UTF-8"),
            "description": attrs["description"][0].decode("UTF-8"),
            "email": attrs["mailPrimaryAddress"][0].decode("UTF-8"),
            "allowed_email_senders_users": [
                x.decode("UTF-8") for x in attrs["univentionAllowedEmailUsers"]
            ],
            "allowed_email_senders_groups": [
                x.decode("UTF-8") for x in attrs["univentionAllowedEmailGroups"]
            ],
            "school": ou,
            "model_ucsschool_roles": [x.decode("UTF-8") for x in attrs["ucsschoolRole"]],
            "users": [x.decode("UTF-8") for x in attrs["uniqueMember"]],
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
            "cn": ["{}-{}".format(ou, name).encode("UTF-8")],
            "objectClass": [
                x.encode("UTF-8") for x in model_ldap_object_classes(ShareType.WorkGroupShare)
            ],
            "ucsschoolRole": [
                x.encode("UTF-8") for x in model_ucsschool_roles(ShareType.WorkGroupShare, [ou])
            ],
            "univentionObjectType": [model_udm_module(ShareType.WorkGroupShare).encode("UTF-8")],
            "univentionShareDirectoryMode": [b"0770"],
            "univentionShareHost": [share_host.encode("UTF-8")],
            "univentionSharePath": ["/home/{0}/groups/{0}-{1}".format(ou, name).encode("UTF-8")],
            "univentionShareSambaBrowseable": [b"yes"],
            "univentionShareSambaCreateMode": [b"0770"],
            "univentionShareSambaDirectoryMode": [b"0770"],
            "univentionShareSambaForceGroup": ["+{}-{}".format(ou, name).encode("UTF-8")],
            "univentionShareSambaName": ["{}-{}".format(ou, name).encode("UTF-8")],
            "univentionShareSambaNtAclSupport": [b"1"],
            "univentionShareSambaWriteable": [b"yes"],
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_share_school_attributes(workgroup_share_ldap_attributes):
    def _func(ou, ldap_attrs=None):  # type: (str, Optional[Dict[str, Any]]) -> Dict[str, Any]
        attrs = ldap_attrs or workgroup_share_ldap_attributes(ou)
        return {
            "name": attrs["cn"][0].decode("UTF-8"),
            "school": ou,
            "model_ucsschool_roles": [x.decode("UTF-8") for x in attrs["ucsschoolRole"]],
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
def restart_services():
    def _restart_services(*services):  # type: (*str) -> None
        cmd = ["/bin/systemctl", "restart"] + list(services)
        print("Restarting service(s): {!r}".format(cmd))
        rv = subprocess.call(cmd)
        print("=> return code: {}.".format(rv))

    return _restart_services


@pytest.fixture
def schedule_restart_services(restart_services):
    services_to_restart = []  # type: List[Tuple[str]]

    def _schedule_restart_services(*services):  # type: (*str) -> None
        services_to_restart.append(services)

    yield _schedule_restart_services

    for services in services_to_restart:
        restart_services(*services)


@pytest.fixture(scope="session")
def restart_umc(restart_services):
    def _restart_umc():
        restart_services(
            "univention-management-console-server",
        )
        # wait some time for UMC web server and UMC server to be ready before the next test is called
        time.sleep(5)

    return _restart_umc


@pytest.fixture
def schedule_restart_umc(schedule_restart_services):
    schedule_restart_services(
        "univention-management-console-server",
    )
    # wait some time for UMC web server and UMC server to be ready before the next test is called
    time.sleep(5)


@pytest.fixture(autouse=True)
def stop_module_process():
    # Clean up ressources
    yield
    subprocess.call(
        [
            "pkill",
            "--full",
            "/usr/bin/python3 /usr/sbin/univention-management-console-module -m ",
        ]
    )


@pytest.fixture
def copy_file():
    """Copy file to target location and cleans up afterwards."""
    cleanup_paths = {}

    def _copy_file(src, dest):
        if os.path.exists(dest):
            backup_file = dest + f".pytest_backup_file_{time.time()}"
            shutil.copy2(dest, backup_file)
        else:
            backup_file = None
        cleanup_paths[dest] = backup_file
        shutil.copy(src, dest)

    yield _copy_file
    for target, backup_file in cleanup_paths.items():
        Path(target).unlink()
        if backup_file is not None:
            shutil.move(backup_file, target)


@pytest.fixture(scope="session")
def check_pdfprinter_spool_permissions():
    def _func(username: str) -> None:
        spool_dir = f"/var/spool/cups-pdf/{username}"
        file_owner = os.stat(spool_dir).st_uid
        user_uid = pwd.getpwnam(username).pw_uid
        print(f"*** Directory {spool_dir}:  expected={user_uid}  found={file_owner}")
        assert (
            file_owner == user_uid
        ), f"Directory {spool_dir} has invalid owner: expected={user_uid}  found={file_owner}"

    return _func


@pytest.fixture(scope="session")
def list_pdfprinter_jobs():
    def _func(username: str) -> List[str]:
        path = "/var/spool/cups-pdf/%s" % (username)
        files = []
        for root, _, filenames in os.walk(path):
            files.extend([os.path.relpath(os.path.join(root, f), path) for f in filenames])
        return files

    return _func


@pytest.fixture(scope="session")
def send_pdfprinter_job(ucr, list_pdfprinter_jobs):
    def _func(
        printer_name: str,
        printhost: str,
        username: str,
        filename: str,
        waiting_time_for_printjob=60,
    ) -> None:
        """
        Sends the specified Postscript file as a new print job to the specified PDF printer.
        Then smbclient is used to check whether the print job has arrived there.
        """
        assert " " not in filename, "whitespace is currently not supported in printjob's filename."
        oldPrintJobs = list_pdfprinter_jobs(username)
        job = []
        cmds = [
            ["lpr", "-P", printer_name, "-U", username, filename],
            [
                "smbclient",
                "//%s/%s" % (printhost, printer_name),
                "-d3",
                "-U",
                "%s%%%s" % (username, "univention"),
                "-c",
                "print %s" % filename,
            ],
        ]
        # cmd = ['smbclient', "-N", "-L", "//%s/%s" % (printhost, printer_name)]
        for cmd in cmds:
            print("cmd = %s" % " ".join(cmd))
            err, out = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            ).communicate()
            # workaround for smbclient session setup failed: NT_STATUS_LOGON_FAILURE
            for waitingTime in range(150):
                err, out = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ).communicate()
                if err:
                    time.sleep(1)
                    print(" - %d - " % waitingTime, err, end=" ")
                else:
                    break
            err, out = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            ).communicate()
            assert not err, "Orderprint failure:\n%r\n%r" % (err, out)
            if "smbclient" in cmd:
                username = username.lower()
            for waitingTime in range(waiting_time_for_printjob):
                job = [x for x in list_pdfprinter_jobs(username) if x not in oldPrintJobs]
                if not job:
                    time.sleep(1)
                    print(" - %d - " % waitingTime, "Waiting for print job .. ")
                else:
                    break
            assert job, "Ordered print job was not stored in user spool directory"

    return _func


@dataclass(frozen=True)
class DNNameTuple:
    name: str
    dn: str


@pytest.fixture
def create_http_import_security_group(schoolenv):
    def _create_http_import_security_group(ou_dn, roles, allowed_ou_names, user_dns):
        """
        _create_http_import_security_group(
            "ou=school1,dc=ucs,dc=test",
            ["student", "staff", "teacher", "teacher_and_staff", "legal_guardian"],
            ["school1"],
            ["uid=user1,cn=lehrer,cn=users,ou=school1,dc=ucs,dc=test"],
        )
        """
        g1 = schoolenv.udm.create_group(
            position="cn=groups,{}".format(ou_dn),
            options=["posix", "samba", "ucsschoolImportGroup"],
            append={
                "users": user_dns,
                "ucsschoolImportRole": roles,
                "ucsschoolImportSchool": allowed_ou_names,
            },
        )

        return DNNameTuple(name=g1[1], dn=g1[0])

    return _create_http_import_security_group
