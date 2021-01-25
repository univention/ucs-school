#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.users to_dict conversion
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: dangerous
## packages:
##   - python-ucs-school

import logging

#
# Hint: When debugging interactively, disable output capturing:
# $ pytest -s -l -v ./......py::test_create
#
import tempfile

import pytest

try:
    from typing import Dict
except ImportError:
    pass
import univention.testing.strings as uts
from ucsschool.lib.models import validator as validator
from ucsschool.lib.models.utils import get_file_handler, ucr
from ucsschool.lib.models.validator import (
    CLASS_SHARE_CLASS_NAME,
    COMPUTERROOM_CLASS_NAME,
    LOGGER_NAME,
    MARKTPLATZ_SHARE_CLASS_NAME,
    SCHOOLCLASS_CLASS_NAME,
    WORKGOUP_SHARE_CLASS_NAME,
    WORKGROUP_CLASS_NAME,
    container_computerrooms,
    container_exam_students,
    container_staff,
    container_students,
    container_teachers,
    container_teachers_and_staff,
    exam_students_group,
    get_role_container,
    role_mapping,
    staff_group_regex,
    teachers_group_regex,
    ucr_get,
    validate,
)

ldap_base = ucr_get("ldap/base")


def filter_log_messages(logs, name):
    return "".join([m for n, _, m in logs if n == name])


@pytest.fixture
def random_logger():
    def _func():
        handler = get_file_handler("DEBUG", tempfile.mkstemp()[1])
        logger = logging.getLogger(uts.random_username())
        logger.addHandler(handler)
        logger.setLevel("DEBUG")
        return logger

    return _func


@pytest.fixture(autouse=True)
def mock_logger_file(mocker):
    with tempfile.NamedTemporaryFile() as file:
        mocker.patch.object(validator, "LOG_FILE", file.name)


def base_group_dict(name):  # type(str, str) -> Dict
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
            "name": "{}".format(name),
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
        "id": "{}".format(name),
        "_links": {},
        "policies": {"policies/umc": []},
        "position": "",
        "options": [],
        "objectType": "groups/group",
    }


def workgroup_as_dict():  # type(None) -> Dict
    name = "DEMOSCHOOL-{}".format(uts.random_name())
    group = base_group_dict(name)
    group["dn"] = "cn={},cn={},cn=groups,ou=DEMOSCHOOL,{}".format(name, container_students, ldap_base)
    group["position"] = "cn={},cn=groups,ou=DEMOSCHOOL,{}".format(container_students, ldap_base)
    group["props"]["ucsschoolRole"] = ["workgroup:school:DEMOSCHOOL"]
    return group


def klasse_as_dict():  # type(None) -> Dict
    name = "DEMOSCHOOL-{}".format(uts.random_name())
    group = base_group_dict(name)
    group["dn"] = "cn={},cn={},cn=groups,ou=DEMOSCHOOL,{}".format(name, container_students, ldap_base)
    group["position"] = "cn=klassen,cn={},cn=groups,ou=DEMOSCHOOL,{}".format(
        container_students, ldap_base
    )
    group["props"]["ucsschoolRole"] = ["school_class:school:DEMOSCHOOL"]
    return group


def computer_room_as_dict():  # type(None) -> Dict
    name = "DEMOSCHOOL-{}".format(uts.random_name())
    group = base_group_dict(name)
    group["dn"] = "cn={},cn={},cn=groups,ou=DEMOSCHOOL,{}".format(
        name, container_computerrooms, ldap_base
    )
    group["position"] = "cn={},cn=groups,ou=DEMOSCHOOL,{}".format(container_computerrooms, ldap_base)
    group["props"]["ucsschoolRole"] = ["computer_room:school:DEMOSCHOOL"]
    return group


def base_share_dict(name):  # type(str) -> Dict
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
        "options": [],
        "objectType": "shares/share",
    }


def klassen_share_as_dict():  # type(None) -> Dict
    name = uts.random_name()
    share = base_share_dict(name)
    share["dn"] = "cn={},cn=klassen,cn=shares,ou=DEMOSCHOOL,{}".format(name, ldap_base)
    share["position"] = "cn=klassen,cn=shares,ou=DEMOSCHOOL,{}".format(ldap_base)
    share["props"]["ucsschoolRole"] = ["school_class_share:school:DEMOSCHOOL"]
    return share


def workgroup_share_as_dict():  # type(None) -> Dict
    name = uts.random_name()
    share = base_share_dict(name)
    share["dn"] = "cn={},cn=shares,ou=DEMOSCHOOL,{}".format(name, ldap_base)
    share["position"] = "cn=shares,ou=DEMOSCHOOL,{}".format(ldap_base)
    share["props"]["ucsschoolRole"] = ["workgroup_share:school:DEMOSCHOOL"]
    return share


def marktplatz_share_as_dict():  # type(None) -> Dict
    name = uts.random_name()
    share = base_share_dict(name)
    share["dn"] = "cn=Marktplatz,cn=shares,ou=DEMOSCHOOL,{}".format(ldap_base)
    share["position"] = "cn=shares,ou=DEMOSCHOOL,{}".format(ldap_base)
    share["props"]["ucsschoolRole"] = ["marketplace_share:school:DEMOSCHOOL"]
    return share


@pytest.mark.parametrize(
    "class_name,get_group_a,get_group_b",
    [
        (SCHOOLCLASS_CLASS_NAME, klasse_as_dict, workgroup_as_dict),
        (SCHOOLCLASS_CLASS_NAME, klasse_as_dict, marktplatz_share_as_dict),
        (WORKGROUP_CLASS_NAME, workgroup_as_dict, klasse_as_dict),
        (WORKGROUP_CLASS_NAME, workgroup_as_dict, computer_room_as_dict),
        (COMPUTERROOM_CLASS_NAME, computer_room_as_dict, klasse_as_dict),
        (COMPUTERROOM_CLASS_NAME, computer_room_as_dict, marktplatz_share_as_dict),
        (CLASS_SHARE_CLASS_NAME, klassen_share_as_dict, marktplatz_share_as_dict),
        (CLASS_SHARE_CLASS_NAME, klassen_share_as_dict, klasse_as_dict),
        (WORKGOUP_SHARE_CLASS_NAME, workgroup_share_as_dict, computer_room_as_dict),
        (MARKTPLATZ_SHARE_CLASS_NAME, marktplatz_share_as_dict, computer_room_as_dict),
        (MARKTPLATZ_SHARE_CLASS_NAME, marktplatz_share_as_dict, klassen_share_as_dict),
    ],
)
def test_correct_ldap_position(caplog, get_group_a, get_group_b, class_name, random_logger):
    random_logger = random_logger()
    group_a = get_group_a()
    group_b = get_group_b()
    group_a["position"] = group_b["position"]
    validate(group_a, class_name=class_name, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "has wrong position in ldap" in log
    assert "{}".format(group_a) in secret_logs


@pytest.mark.parametrize(
    "class_name,dict_obj",
    [
        (SCHOOLCLASS_CLASS_NAME, klasse_as_dict),
        (WORKGROUP_CLASS_NAME, workgroup_as_dict),
        (COMPUTERROOM_CLASS_NAME, computer_room_as_dict),
        (WORKGOUP_SHARE_CLASS_NAME, workgroup_share_as_dict),
        (MARKTPLATZ_SHARE_CLASS_NAME, marktplatz_share_as_dict),
        (CLASS_SHARE_CLASS_NAME, klassen_share_as_dict),
    ],
)
@pytest.mark.parametrize(
    "required_attribute", ["name", "ucsschoolRole",],
)
def test_missing_required_attribute(caplog, dict_obj, class_name, random_logger, required_attribute):
    random_logger = random_logger()
    _dict_obj = dict_obj()
    _dict_obj["props"][required_attribute] = []
    validate(_dict_obj, class_name=class_name, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "is missing required attributes: {}".format(required_attribute) in log
    assert "{}".format(_dict_obj) in secret_logs


@pytest.mark.parametrize(
    "class_name,dict_obj",
    [
        (SCHOOLCLASS_CLASS_NAME, klasse_as_dict()),
        (WORKGROUP_CLASS_NAME, workgroup_as_dict()),
        (COMPUTERROOM_CLASS_NAME, computer_room_as_dict()),
        (WORKGOUP_SHARE_CLASS_NAME, workgroup_share_as_dict()),
        (MARKTPLATZ_SHARE_CLASS_NAME, marktplatz_share_as_dict()),
        (CLASS_SHARE_CLASS_NAME, klassen_share_as_dict()),
    ],
)
def test_missing_role(caplog, dict_obj, class_name, random_logger):
    random_logger = random_logger()
    for role in dict_obj["props"]["ucsschoolRole"]:
        r, c, s = role.split(":")
        if r == role_mapping[class_name]:
            dict_obj["props"]["ucsschoolRole"].remove(role)
    validate(dict_obj, class_name=class_name, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "does not have {}-role.".format(role_mapping[class_name]) in log
    assert "{}".format(dict_obj) in secret_logs


@pytest.mark.parametrize(
    "class_name,dict_obj",
    [
        (SCHOOLCLASS_CLASS_NAME, klasse_as_dict()),
        (WORKGROUP_CLASS_NAME, workgroup_as_dict()),
        (COMPUTERROOM_CLASS_NAME, computer_room_as_dict()),
        (WORKGOUP_SHARE_CLASS_NAME, workgroup_share_as_dict()),
        (CLASS_SHARE_CLASS_NAME, klassen_share_as_dict()),
    ],
)
def test_missing_school_prefix(caplog, dict_obj, class_name, random_logger):
    random_logger = random_logger()
    dict_obj["props"]["name"] = uts.random_name()
    validate(dict_obj, class_name=class_name, logger=random_logger)
    public_logs = filter_log_messages(caplog.record_tuples, random_logger.name)
    secret_logs = filter_log_messages(caplog.record_tuples, LOGGER_NAME)
    for log in (public_logs, secret_logs):
        assert "has an incorrect school prefix for school DEMOSCHOOL." in log
    assert "{}".format(dict_obj) in secret_logs
