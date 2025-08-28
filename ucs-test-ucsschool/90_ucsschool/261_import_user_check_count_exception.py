#!/usr/share/ucs-test/runner pytest-3 -l -s -v
## -*- coding: utf-8 -*-
## desc: Test tolerate_errors by raising it in a PyHook
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import

import copy
import os
import os.path

import pytest
from ldap.filter import escape_filter_chars

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException

TESTHOOKSOURCE = os.path.join(os.path.dirname(__file__), "test261_count_exception.pyhook")
TESTHOOKTARGET = "/usr/share/ucs-school-import/pyhooks/test261_count_exception.py"


class ImportTest(CLI_Import_v2_Tester):
    ou_C = None


@pytest.fixture(scope="module")
def import_tester():
    importTest = ImportTest()
    try:
        with utu.UCSTestSchool() as schoolenv:
            importTest.setup_testenv(schoolenv)
            importTest.create_ous(schoolenv)
            yield importTest
    finally:
        importTest.cleanup()


@pytest.fixture
def m_error_hook():
    os.symlink(
        TESTHOOKSOURCE,
        TESTHOOKTARGET,
    )
    yield
    os.remove(TESTHOOKTARGET)


@pytest.mark.parametrize("tolerate_errors,expected_users", [(-1, [0, 2, 4]), (0, [0]), (1, [0, 2])])
def test_tolerate_errors(import_tester, m_error_hook, tolerate_errors, expected_users):
    source_uid = "source_uid-{}".format(uts.random_string())
    config = copy.deepcopy(import_tester.default_config)
    config.update_entry("csv:mapping:Benutzername", "name")
    config.update_entry("csv:mapping:record_uid", "record_uid")
    config.update_entry("csv:mapping:role", "__role")
    config.update_entry("source_uid", source_uid)
    config.update_entry("user_role", None)
    config.update_entry("tolerate_errors", tolerate_errors)

    import_tester.log.info(
        '*** Importing a user from each role, two with firstname starting with "M" should be an '
        "error..."
    )
    person_list = []
    for i in range(5):
        person = Person(import_tester.ou_A.name, "teacher")
        person.update(record_uid="record_uid-{}".format(uts.random_string()), source_uid=source_uid)
        person_list.append(person)
    person_list[0].update(firstname="A{}".format(person_list[0].firstname[1:]))
    person_list[1].update(firstname="M{}".format(person_list[1].firstname[1:]))
    person_list[2].update(firstname="B{}".format(person_list[2].firstname[1:]))
    person_list[3].update(firstname="M{}".format(person_list[3].firstname[1:]))
    person_list[4].update(firstname="C{}".format(person_list[2].firstname[1:]))
    fn_csv = import_tester.create_csv_file(person_list=person_list, mapping=config["csv"]["mapping"])
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    try:
        import_tester.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
    except ImportException:
        import_tester.log.info("OK: import failed.")
    for i in expected_users:
        wait_for_drs_replication("cn={}".format(escape_filter_chars(person_list[i].username)))
    for person in [person_list[i] for i in expected_users]:
        utils.verify_ldap_object(person.dn, strict=False, should_exist=True)
    for person in [person_list[i] for i in range(len(person_list)) if i not in expected_users]:
        utils.verify_ldap_object(person.dn, strict=False, should_exist=False)
