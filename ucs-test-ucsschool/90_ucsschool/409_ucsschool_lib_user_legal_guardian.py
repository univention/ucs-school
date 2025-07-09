#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: test ucsschool.lib.models.user.User ucsschool_roles
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1,ucs-school-lib]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

import pytest

import univention.admin.uexceptions
import univention.testing.strings as uts
from ucsschool.lib.models.attributes import ValidationError
from ucsschool.lib.models.user import LegalGuardian, Student


def test_create_legal_guardian(schoolenv):

    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])

    _, legal_guardian_dn = schoolenv.create_legal_guardian(ou_name=ou_name)

    legal_guardian = LegalGuardian.from_dn(legal_guardian_dn, ou_name, schoolenv.lo)
    legal_guardian.validate(schoolenv.lo)

    assert legal_guardian.roles == ["legal_guardian"]
    assert legal_guardian.dn.endswith(
        f"cn=gesetzliche vertreter,cn=users,ou={ou_name},{schoolenv.ucr['ldap/base']}"
    )
    assert (
        f"cn=gesetzliche vertreter-{ou_name},cn=groups,ou={ou_name},{schoolenv.ucr['ldap/base']}"
        in legal_guardian.get_specific_groups([ou_name])
    )
    assert (
        f"cn=gesetzliche vertreter-{ou_name},cn=groups,ou={ou_name},{schoolenv.ucr['ldap/base']}"
        in legal_guardian.get_legal_guardians_groups([ou_name])
    )
    assert (
        f"cn=gesetzliche vertreter,cn=users,ou={ou_name},{schoolenv.ucr['ldap/base']}"
        == legal_guardian.get_container(ou_name)
    )


def test_create_student_with_legal_guardian(schoolenv):

    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])

    _, legal_guardian_dn_1 = schoolenv.create_legal_guardian(ou_name=ou_name)

    _, legal_guardian_dn_2 = schoolenv.create_legal_guardian(ou_name=ou_name)

    class_name, class_dn = schoolenv.create_school_class(ou_name)
    _, student_dn = schoolenv.create_student(
        ou_name=ou_name,
        legal_guardians=[legal_guardian_dn_1, legal_guardian_dn_2],
        classes=class_name,
    )
    student = Student.from_dn(student_dn, ou_name, schoolenv.lo)
    legal_guardian_1 = LegalGuardian.from_dn(legal_guardian_dn_1, ou_name, schoolenv.lo)
    legal_guardian_2 = LegalGuardian.from_dn(legal_guardian_dn_2, ou_name, schoolenv.lo)

    assert set(student.legal_guardians) == {legal_guardian_dn_1, legal_guardian_dn_2}
    assert set(legal_guardian_1.legal_wards) == {student_dn}
    assert set(legal_guardian_2.legal_wards) == {student_dn}


def test_create_legal_guardian_with_legal_ward(schoolenv):

    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    class_name, class_dn = schoolenv.create_school_class(ou_name)
    _, student_dn = schoolenv.create_student(
        ou_name=ou_name,
        classes=class_name,
    )

    _, legal_guardian_dn = schoolenv.create_legal_guardian(ou_name=ou_name, legal_wards=[student_dn])

    student = Student.from_dn(student_dn, ou_name, schoolenv.lo)
    legal_guardian = LegalGuardian.from_dn(legal_guardian_dn, ou_name, schoolenv.lo)

    assert set(student.legal_guardians) == {legal_guardian_dn}
    assert set(legal_guardian.legal_wards) == {student_dn}


def test_create_legal_guardian_with_missing_legal_ward(schoolenv):
    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])

    with pytest.raises(univention.admin.uexceptions.base, match=".*Could not find student.*"):
        _, legal_guardian_dn = schoolenv.create_legal_guardian(
            ou_name=ou_name,
            legal_wards=["uid=idonotexist,cn=users,dc=ucs,dc=test"],
        )


def test_create_student_with_missing_legal_guardian(schoolenv):
    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])

    legal_guardian_uid_1 = uts.random_username()
    _, legal_guardian_dn_1 = schoolenv.create_legal_guardian(
        ou_name=ou_name, username=legal_guardian_uid_1
    )

    legal_guardian_dn_2 = "uid=idonotexist,cn=users,dc=ucs,dc=test"

    with pytest.raises(ValidationError, match=".*The following legal guardians do not exist.*"):
        _, student_dn = schoolenv.create_student(
            ou_name=ou_name, legal_guardians=[legal_guardian_dn_1, legal_guardian_dn_2]
        )


def test_create_student_without_legal_guardian(schoolenv):
    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    class_name, class_dn = schoolenv.create_school_class(ou_name)
    _, student_dn = schoolenv.create_student(ou_name=ou_name, legal_guardians=[], classes=class_name)
    student = Student.from_dn(student_dn, ou_name, schoolenv.lo)
    assert student.dn == student_dn
    assert student.legal_guardians == []


def test_create_student_with_bad_dn(schoolenv):
    """The legal guardian attribute must only accept DNs"""
    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    class_name, class_dn = schoolenv.create_school_class(ou_name)

    with pytest.raises(ValidationError, match=".*Not a valid LDAP DN.*"):
        schoolenv.create_student(ou_name=ou_name, legal_guardians=["abdefg"], classes=class_name)


def test_create_student_with_too_many_legal_guardians(schoolenv):
    """A student should not have more then 4 legal guardians"""
    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])

    legal_guardian_dns = [schoolenv.create_legal_guardian(ou_name=ou_name)[1] for _ in range(5)]

    class_name, class_dn = schoolenv.create_school_class(ou_name)

    with pytest.raises(
        univention.admin.uexceptions.base,
        match=".*is above the maximum allowed number of legal guardians.*",
    ):
        _, student_dn = schoolenv.create_student(
            ou_name=ou_name,
            legal_guardians=legal_guardian_dns,
            classes=class_name,
        )


def test_update_legal_guardian(schoolenv):
    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    class_name, class_dn = schoolenv.create_school_class(ou_name)
    _, student_dn = schoolenv.create_student(ou_name=ou_name, legal_guardians=[], classes=class_name)
    _, legal_guardian_dn = schoolenv.create_legal_guardian(ou_name=ou_name)
    student = Student.from_dn(student_dn, ou_name, schoolenv.lo)
    assert student.dn == student_dn
    assert student.legal_guardians == []
    student.legal_guardians = [legal_guardian_dn]
    student.modify(schoolenv.lo)
    student = Student.from_dn(student_dn, ou_name, schoolenv.lo)
    assert student.legal_guardians == [legal_guardian_dn]
    legal_guardian = LegalGuardian.from_dn(legal_guardian_dn, ou_name, schoolenv.lo)
    assert legal_guardian.legal_wards == [student_dn]


def test_update_legal_ward(schoolenv):
    ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr["hostname"])
    class_name, class_dn = schoolenv.create_school_class(ou_name)
    _, student_dn = schoolenv.create_student(ou_name=ou_name, legal_guardians=[], classes=class_name)
    _, legal_guardian_dn = schoolenv.create_legal_guardian(ou_name=ou_name)
    legal_guardian = LegalGuardian.from_dn(legal_guardian_dn, ou_name, schoolenv.lo)
    assert legal_guardian.dn == legal_guardian_dn
    assert legal_guardian.legal_wards == []
    legal_guardian.legal_wards = [student_dn]
    legal_guardian.modify(schoolenv.lo)
    student = Student.from_dn(student_dn, ou_name, schoolenv.lo)
    assert student.legal_guardians == [legal_guardian_dn]
    legal_guardian = LegalGuardian.from_dn(legal_guardian_dn, ou_name, schoolenv.lo)
    assert legal_guardian.legal_wards == [student_dn]
