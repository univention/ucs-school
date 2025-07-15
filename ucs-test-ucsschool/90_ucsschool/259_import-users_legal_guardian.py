#!/usr/share/ucs-test/runner pytest-3 -l -s -v
## -*- coding: utf-8 -*-
## desc: test legal guardian feature
## tags: [apptest,ucsschool,ucsschool_import1,ucs-school-import,ucs-school-import]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import

import copy
import os

import pytest

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.user import LegalGuardian, Student
from univention.testing.ucsschool.importusers import Person
from univention.testing.ucsschool.importusers_cli_v2 import CLI_Import_v2_Tester, ImportException


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
def record_uid_hook():
    os.symlink(
        "/usr/share/ucs-school-import/pyhooks-available/legal_guardian_as_record_uid.py",
        "/usr/share/ucs-school-import/pyhooks/ucstest_legal_guardian_as_record_uid.py",
    )
    yield
    os.remove("/usr/share/ucs-school-import/pyhooks/ucstest_legal_guardian_as_record_uid.py")


def test_legal_guardian_no_ward(import_tester):
    source_uid = "source_uid-{}".format(uts.random_string())
    config = copy.deepcopy(import_tester.default_config)
    config.update_entry("csv:mapping:Benutzername", "name")
    config.update_entry("csv:mapping:record_uid", "record_uid")
    config.update_entry("csv:mapping:role", "__role")
    config.update_entry("scheme:username:default", "<:umlauts><firstname:lower><lastname:lower>")
    config.update_entry("source_uid", source_uid)
    config.update_entry("user_role", None)
    del config["csv"]["mapping"]["E-Mail"]

    legal_guardian = Person(import_tester.ou_A.name, "legal_guardian")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    legal_guardian.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    fn_csv = import_tester.create_csv_file(
        person_list=[legal_guardian], mapping=config["csv"]["mapping"]
    )
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    import_tester.run_import(["-c", fn_config])
    import_tester.check_new_and_removed_users(1, 0)
    legal_guardian.update_from_ldap(import_tester.lo, ["dn"])
    legalGuardian_schoollib = LegalGuardian.from_dn(
        legal_guardian.dn, legal_guardian.school, import_tester.lo
    )
    assert not legalGuardian_schoollib.legal_wards


def test_legal_guardian_with_wards(import_tester, record_uid_hook):
    source_uid = "source_uid-{}".format(uts.random_string())
    config = copy.deepcopy(import_tester.default_config)
    config.update_entry("csv:mapping:Benutzername", "name")
    config.update_entry("csv:mapping:record_uid", "record_uid")
    config.update_entry("csv:mapping:role", "__role")
    config.update_entry("scheme:username:default", "<:umlauts><firstname:lower><lastname:lower>")
    config.update_entry("source_uid", source_uid)
    config.update_entry("user_role", None)
    del config["csv"]["mapping"]["E-Mail"]

    student1 = Person(import_tester.ou_A.name, "student")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    student1.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    student2 = Person(import_tester.ou_B.name, "student")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    student2.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        schools=[import_tester.ou_B.name, import_tester.ou_A.name],
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    legal_guardian = Person(import_tester.ou_A.name, "legal_guardian")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    legal_guardian.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    fn_csv = import_tester.create_csv_file(
        person_list=[student1, student2, legal_guardian],
        mapping=config["csv"]["mapping"],
    )
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    import_tester.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
    import_tester.check_new_and_removed_users(3, 0)
    student1.update_from_ldap(import_tester.lo, ["username", "mail"])
    student2.update_from_ldap(import_tester.lo, ["username", "mail"])
    legal_guardian.update_from_ldap(import_tester.lo, ["username", "mail"])
    legal_guardian.update(
        legal_wards=[student1.record_uid, student2.record_uid],
    )
    config.update_entry("csv:mapping:legal_wards", "legal_wards")
    fn_csv = import_tester.create_csv_file(
        person_list=[legal_guardian, student1, student2],
        mapping=config["csv"]["mapping"],
    )
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    import_tester.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
    import_tester.check_new_and_removed_users(0, 0)
    legal_guardian.update_from_ldap(import_tester.lo, ["dn"])
    student1.update_from_ldap(import_tester.lo, ["dn"])
    student2.update_from_ldap(import_tester.lo, ["dn"])
    legalGuardian_schoollib = LegalGuardian.from_dn(
        legal_guardian.dn, legal_guardian.school, import_tester.lo
    )
    student1_schoollib = Student.from_dn(student1.dn, student1.school, import_tester.lo)
    student2_schoollib = Student.from_dn(student2.dn, student2.school, import_tester.lo)
    assert set(legalGuardian_schoollib.legal_wards) == {student1.dn, student2.dn}
    assert student1_schoollib.legal_guardians == [legal_guardian.dn]
    assert student2_schoollib.legal_guardians == [legal_guardian.dn]
    legal_guardian.update(
        legal_wards=[],
    )
    fn_csv = import_tester.create_csv_file(
        person_list=[legal_guardian, student1, student2],
        mapping=config["csv"]["mapping"],
    )
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    import_tester.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
    import_tester.check_new_and_removed_users(0, 0)
    legalGuardian_schoollib = LegalGuardian.from_dn(
        legal_guardian.dn, legal_guardian.school, import_tester.lo
    )
    student1_schoollib = Student.from_dn(student1.dn, student1.school, import_tester.lo)
    student2_schoollib = Student.from_dn(student2.dn, student2.school, import_tester.lo)
    assert not legalGuardian_schoollib.legal_wards
    assert not student1_schoollib.legal_guardians
    assert not student2_schoollib.legal_guardians


def test_student_with_legal_guardians(import_tester, record_uid_hook):
    source_uid = "source_uid-{}".format(uts.random_string())
    config = copy.deepcopy(import_tester.default_config)
    config.update_entry("csv:mapping:Benutzername", "name")
    config.update_entry("csv:mapping:record_uid", "record_uid")
    config.update_entry("csv:mapping:role", "__role")
    config.update_entry("scheme:username:default", "<:umlauts><firstname:lower><lastname:lower>")
    config.update_entry("source_uid", source_uid)
    config.update_entry("user_role", None)
    del config["csv"]["mapping"]["E-Mail"]

    legal_guardian1 = Person(import_tester.ou_A.name, "legal_guardian")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    legal_guardian1.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    legal_guardian2 = Person(import_tester.ou_B.name, "legal_guardian")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    legal_guardian2.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        schools=[import_tester.ou_B.name, import_tester.ou_A.name],
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    student = Person(import_tester.ou_A.name, "student")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    student.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    fn_csv = import_tester.create_csv_file(
        person_list=[legal_guardian1, legal_guardian2, student], mapping=config["csv"]["mapping"]
    )
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    import_tester.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
    import_tester.check_new_and_removed_users(3, 0)
    legal_guardian1.update_from_ldap(import_tester.lo, ["username", "mail"])
    legal_guardian2.update_from_ldap(import_tester.lo, ["username", "mail"])
    student.update(
        legal_guardians=[legal_guardian1.record_uid, legal_guardian2.record_uid],
    )
    config.update_entry("csv:mapping:legal_guardians", "legal_guardians")
    fn_csv = import_tester.create_csv_file(
        person_list=[legal_guardian1, legal_guardian2, student],
        mapping=config["csv"]["mapping"],
    )
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    import_tester.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
    import_tester.check_new_and_removed_users(0, 0)
    student.update_from_ldap(import_tester.lo, ["dn"])
    legal_guardian1.update_from_ldap(import_tester.lo, ["dn"])
    legal_guardian2.update_from_ldap(import_tester.lo, ["dn"])
    legalGuardian1_schoollib = LegalGuardian.from_dn(legal_guardian1.dn, None, import_tester.lo)
    legalGuardian2_schoollib = LegalGuardian.from_dn(legal_guardian2.dn, None, import_tester.lo)
    student_schoollib = Student.from_dn(student.dn, None, import_tester.lo)
    assert set(student_schoollib.legal_guardians) == {legal_guardian1.dn, legal_guardian2.dn}
    assert legalGuardian1_schoollib.legal_wards == [student.dn]
    assert legalGuardian2_schoollib.legal_wards == [student.dn]
    student.update(
        legal_guardians=[],
    )
    fn_csv = import_tester.create_csv_file(
        person_list=[legal_guardian1, legal_guardian2, student],
        mapping=config["csv"]["mapping"],
    )
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    import_tester.run_import(["-c", fn_config], fail_on_preexisting_pyhook=False)
    import_tester.check_new_and_removed_users(0, 0)
    legalGuardian1_schoollib = LegalGuardian.from_dn(legal_guardian1.dn, None, import_tester.lo)
    legalGuardian2_schoollib = LegalGuardian.from_dn(legal_guardian2.dn, None, import_tester.lo)
    student_schoollib = Student.from_dn(student.dn, None, import_tester.lo)
    assert not student_schoollib.legal_guardians
    assert not legalGuardian1_schoollib.legal_wards
    assert not legalGuardian2_schoollib.legal_wards


def test_legal_guardian_wards_limit(import_tester):
    source_uid = "source_uid-{}".format(uts.random_string())
    config = copy.deepcopy(import_tester.default_config)
    config.update_entry("csv:mapping:Benutzername", "name")
    config.update_entry("csv:mapping:record_uid", "record_uid")
    config.update_entry("csv:mapping:legal_wards", "legal_wards")
    config.update_entry("csv:mapping:role", "__role")
    config.update_entry("scheme:username:default", "<:umlauts><firstname:lower><lastname:lower>")
    config.update_entry("source_uid", source_uid)
    config.update_entry("user_role", None)
    del config["csv"]["mapping"]["E-Mail"]

    legal_guardian = Person(import_tester.ou_A.name, "legal_guardian")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    legal_guardian.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        legal_wards=[f"foo{i}" for i in range(12)],
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    fn_csv = import_tester.create_csv_file(
        person_list=[legal_guardian], mapping=config["csv"]["mapping"]
    )
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    with pytest.raises(ImportException) as excinfo:
        import_tester.run_import(["-c", fn_config])
        assert (
            f"ucsschool.importer.exceptions.InvalidLegalWard: "
            f"User {legal_guardian.username} has more legal wards (12) than allowed (10)"
            in str(excinfo.value)
        )


def test_student_legal_guardian_limit(import_tester):
    source_uid = "source_uid-{}".format(uts.random_string())
    config = copy.deepcopy(import_tester.default_config)
    config.update_entry("csv:mapping:Benutzername", "name")
    config.update_entry("csv:mapping:record_uid", "record_uid")
    config.update_entry("csv:mapping:legal_guardians", "legal_guardians")
    config.update_entry("csv:mapping:role", "__role")
    config.update_entry("scheme:username:default", "<:umlauts><firstname:lower><lastname:lower>")
    config.update_entry("source_uid", source_uid)
    config.update_entry("user_role", None)
    del config["csv"]["mapping"]["E-Mail"]

    student = Person(import_tester.ou_A.name, "student")
    record_uid = "record_uid-%s" % (uts.random_string(),)
    student.update(
        record_uid=record_uid,
        source_uid=source_uid,
        firstname=uts.random_username(),
        lastname=uts.random_username(),
        legal_guardians=[f"foo{i}" for i in range(6)],
        username=None,  # let the import generate the attributes value
        mail=None,  # let the import generate the attributes value
    )
    fn_csv = import_tester.create_csv_file(person_list=[student], mapping=config["csv"]["mapping"])
    config.update_entry("input:filename", fn_csv)
    fn_config = import_tester.create_config_json(values=config)
    import_tester.save_ldap_status()
    with pytest.raises(ImportException) as excinfo:
        import_tester.run_import(["-c", fn_config])
        assert (
            f"ucsschool.importer.exceptions.InvalidLegalWard: "
            f"User {student.username} has more legal guardians (6) than allowed (4)"
            in str(excinfo.value)
        )
