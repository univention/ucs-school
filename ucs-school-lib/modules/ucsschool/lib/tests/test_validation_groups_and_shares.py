#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.groups and shares validation
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python-ucs-school

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./......py::test_*
#
import tempfile

import pytest
from faker import Faker

try:
    from typing import Any, Dict, List, Tuple
except ImportError:
    pass
import ucsschool.lib.models.validator
from ucsschool.lib.models.utils import ucr
from ucsschool.lib.models.validator import (
    VALIDATION_LOGGER,
    ClassShareValidator,
    ComputerroomValidator,
    MarketplaceShareValidator,
    SchoolClassValidator,
    WorkGroupShareValidator,
    WorkGroupValidator,
    get_class,
    validate,
)
from ucsschool.lib.roles import (
    role_computer_room,
    role_marketplace_share,
    role_school_class,
    role_school_class_share,
    role_workgroup,
    role_workgroup_share,
)
from ucsschool.lib.schoolldap import SchoolSearchBase

fake = Faker()
SchoolSearchBase._load_containers_and_prefixes()
ldap_base = ucr["ldap/base"]
container_computerrooms = SchoolSearchBase._containerRooms
container_students = SchoolSearchBase._containerStudents

fake_ou = fake.user_name()[:10]


def filter_log_messages(logs: List[Tuple[str, int, str]], name: str) -> str:
    """
    get all log messages for logger with name
    """
    return "".join([m for n, _, m in logs if n == name])


@pytest.fixture(autouse=True)
def mock_logger_file(mocker):
    with tempfile.NamedTemporaryFile() as f:
        mocker.patch.object(ucsschool.lib.models.validator, "LOG_FILE", f.name)


def base_group(name: str) -> Dict[str, Any]:
    return {
        "dn": "",
        "props": {
            "sambaGroupType": "2",
            "serviceprovidergroup": [],
            "description": None,
            "adGroupType": "-2147483646",
            "allowedEmailUsers": [],
            "UVMMGroup": False,
            "memberOf": [],
            "nestedGroup": [],
            "name": name,
            "gidNumber": 5088,
            "hosts": [],
            "objectFlag": [],
            "sambaRID": 11177,
            "sambaPrivileges": [],
            "ucsschoolRole": [],
            "mailAddress": None,
            "allowedEmailGroups": [],
            "users": [],
        },
        "policies": {"policies/umc": []},
        "position": "",
        "options": {},
        "objectType": "groups/group",
    }


def workgroup() -> Dict[str, Any]:
    name = "{}-{}".format(fake_ou, fake.user_name())
    group = base_group(name)
    group["dn"] = "cn={},cn={},cn=groups,ou={},{}".format(name, container_students, fake_ou, ldap_base)
    group["position"] = "cn={},cn=groups,ou={},{}".format(container_students, fake_ou, ldap_base)
    group["props"]["ucsschoolRole"] = ["workgroup:school:{}".format(fake_ou)]
    return group


def schoolclass() -> Dict[str, Any]:
    name = "{}-{}".format(fake_ou, fake.user_name())
    group = base_group(name)
    group["position"] = "cn=klassen,cn={},cn=groups,ou={},{}".format(
        container_students, fake_ou, ldap_base
    )
    group["dn"] = "cn={}{}".format(name, group["position"])
    group["props"]["ucsschoolRole"] = ["school_class:school:{}".format(fake_ou)]
    return group


def computer_room() -> Dict[str, Any]:
    name = "{}-{}".format(fake_ou, fake.user_name())
    group = base_group(name)
    group["dn"] = "cn={},cn={},cn=groups,ou={},{}".format(
        name, container_computerrooms, fake_ou, ldap_base
    )
    group["position"] = "cn={},cn=groups,ou={},{}".format(container_computerrooms, fake_ou, ldap_base)
    group["props"]["ucsschoolRole"] = ["computer_room:school:{}".format(fake_ou)]
    return group


def base_share(name: str) -> Dict[str, Any]:
    return {
        "dn": "",
        "props": {
            "sambaFakeOplocks": False,
            "sambaDirectorySecurityMode": "0777",
            "sambaNtAclSupport": True,
            "appendACL": [
                "(D;OICI;WOWD;;;S-1-5-21-1983109683-1562727952-2110040105-11167)",
                "(A;OICI;0x001f01ff;;;S-1-5-21-1983109683-1562727952-2110040105-11177)",
                "(A;OICI;0x001f01ff;;;S-1-5-21-1983109683-1562727952-2110040105-11165)",
            ],
            "sambaHostsAllow": [],
            "sambaPostexec": None,
            "owner": 0,
            "sambaHideFiles": None,
            "sambaName": name,
            "sambaValidUsers": None,
            "sambaForceDirectoryMode": "0",
            "sambaCustomSettings": {},
            "sambaCreateMode": "0770",
            "group": 5088,
            "sambaForceCreateMode": "0",
            "sambaBrowseable": True,
            "sambaDosFilemode": False,
            "sambaBlockSize": None,
            "printablename": "{} (ucs-9537.wenzel-univention.intranet)".format(name),
            "sambaPreexec": None,
            "objectFlag": [],
            "sambaHideUnreadable": False,
            "sambaInheritAcls": True,
            "sambaWriteList": None,
            "sambaForceGroup": "+{}".format(name),
            "sambaInheritPermissions": True,
            "sambaSecurityMode": "0777",
            "sambaForceSecurityMode": "0",
            "sambaVFSObjects": None,
            "sambaMSDFSRoot": False,
            "sambaForceUser": None,
            "sambaOplocks": True,
            "sambaWriteable": True,
            "host": "ucs-9537.wenzel-univention.intranet",
            "sambaStrictLocking": "Auto",
            "sambaDirectoryMode": "0770",
            "path": "",
            "ucsschoolRole": [],
            "sambaHostsDeny": [],
            "sambaLocking": True,
            "sambaBlockingLocks": True,
            "sambaInvalidUsers": None,
            "name": name,
            "sambaInheritOwner": True,
            "sambaPublic": False,
            "directorymode": "0770",
            "sambaCscPolicy": "manual",
            "sambaForceDirectorySecurityMode": "0",
            "sambaLevel2Oplocks": True,
        },
        "id": "",
        "_links": {},
        "policies": {"policies/share_userquota": []},
        "position": "",
        "options": {},
        "objectType": "shares/share",
    }


def klassen_share() -> Dict[str, Any]:
    name = "{}-{}".format(fake_ou, fake.user_name())
    share = base_share(name)
    share["dn"] = "cn={},cn=klassen,cn=shares,ou={},{}".format(name, fake_ou, ldap_base)
    share["position"] = "cn=klassen,cn=shares,ou={},{}".format(fake_ou, ldap_base)
    share["props"]["ucsschoolRole"] = ["school_class_share:school:{}".format(fake_ou)]
    return share


def workgroup_share() -> Dict[str, Any]:
    name = "{}-{}".format(fake_ou, fake.user_name())
    share = base_share(name)
    share["dn"] = "cn={},cn=shares,ou={},{}".format(name, fake_ou, ldap_base)
    share["position"] = "cn=shares,ou={},{}".format(fake_ou, ldap_base)
    share["props"]["ucsschoolRole"] = ["workgroup_share:school:{}".format(fake_ou)]
    return share


def marktplatz_share() -> Dict[str, Any]:
    name = "Marktplatz"
    share = base_share(name)
    share["dn"] = "cn={},cn=shares,ou={},{}".format(name, fake_ou, ldap_base)
    share["position"] = "cn=shares,ou={},{}".format(fake_ou, ldap_base)
    share["props"]["ucsschoolRole"] = ["marketplace_share:school:{}".format(fake_ou)]
    return share


complete_role_matrix = [
    schoolclass(),
    workgroup(),
    computer_room(),
    workgroup_share(),
    klassen_share(),
    marktplatz_share(),
]

complete_role_matrix_ids = [
    role_school_class,
    role_workgroup,
    role_computer_room,
    role_workgroup_share,
    role_school_class_share,
    role_marketplace_share,
]


def check_logs(
    dict_obj: Dict[str, Any], record_tuples: Any, public_logger_name: str, expected_msg: str
) -> None:
    public_logs = filter_log_messages(record_tuples, public_logger_name)
    secret_logs = filter_log_messages(record_tuples, VALIDATION_LOGGER)
    for log in (public_logs, secret_logs):
        assert expected_msg in log
    assert "{}".format(dict_obj) in secret_logs
    assert "{}".format(dict_obj) not in public_logs


@pytest.mark.parametrize(
    "dict_obj,ObjectClass",
    zip(
        complete_role_matrix,
        [
            SchoolClassValidator,
            WorkGroupValidator,
            ComputerroomValidator,
            WorkGroupShareValidator,
            ClassShareValidator,
            MarketplaceShareValidator,
        ],
    ),
    ids=complete_role_matrix_ids,
)
def test_get_class(dict_obj, ObjectClass):
    """
    note: This code tests the get_class method for groups and shares.
    It can be refactored with the user-test if the dict_obj are moved to a separate file.
    """
    assert get_class(dict_obj) is ObjectClass


@pytest.mark.parametrize(
    "dict_obj",
    complete_role_matrix,
    ids=complete_role_matrix_ids,
)
def test_correct_object(caplog, dict_obj, random_logger):
    """
    note: This code tests if no validation errors are logged for valid groups and shares.
    It can be refactored with the user-test when the dict_obj are moved to a separate file.
    """
    validate(dict_obj, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, VALIDATION_LOGGER)
    for log in (public_logs, secret_logs):
        assert not log
    assert "{}".format(dict_obj) not in secret_logs
    assert "{}".format(dict_obj) not in public_logs


@pytest.mark.parametrize(
    "required_attribute",
    ["name", "ucsschoolRole"],
)
@pytest.mark.parametrize(
    "dict_obj",
    [
        schoolclass,
        workgroup,
        computer_room,
        workgroup_share,
        klassen_share,
        marktplatz_share,
    ],
    ids=complete_role_matrix_ids,
)
def test_missing_required_attribute(caplog, dict_obj, random_logger, required_attribute):
    _dict_obj = dict_obj()
    _dict_obj["props"][required_attribute] = []
    validate(_dict_obj, logger=random_logger)
    expected_msg = "is missing required attributes: {!r}".format([required_attribute])
    check_logs(_dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


@pytest.mark.parametrize(
    "expected_role,get_dict_obj",
    [
        (role_school_class, schoolclass),
        (role_workgroup, workgroup),
        (role_computer_room, computer_room),
        (role_workgroup_share, workgroup_share),
        (role_marketplace_share, marktplatz_share),
        (role_school_class_share, klassen_share),
    ],
    ids=complete_role_matrix_ids,
)
def test_missing_role(caplog, get_dict_obj, expected_role, random_logger):
    dict_obj = get_dict_obj()
    _role = "dummy"
    for role in list(dict_obj["props"]["ucsschoolRole"]):
        r, c, s = role.split(":")
        if r == expected_role:
            dict_obj["props"]["ucsschoolRole"] = []
            _role = role
            break

    validate(dict_obj, logger=random_logger)
    expected_msg = "is missing roles {!r}".format([_role])
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)


@pytest.mark.parametrize(
    "dict_obj",
    [
        schoolclass(),
        workgroup(),
        computer_room(),
        workgroup_share(),
        klassen_share(),
    ],
    ids=[
        role_school_class,
        role_workgroup,
        role_computer_room,
        role_workgroup_share,
        role_school_class_share,
    ],
)
def test_missing_school_prefix(caplog, dict_obj, random_logger):
    dict_obj["props"]["name"] = fake.user_name()
    validate(dict_obj, logger=random_logger)
    expected_msg = "has an incorrect school prefix for school {}.".format(fake_ou)
    check_logs(dict_obj, caplog.record_tuples, random_logger.name, expected_msg)
