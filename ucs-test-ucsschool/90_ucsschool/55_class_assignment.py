#!/usr/share/ucs-test/runner /usr/bin/py.test
# -*- coding: utf-8 -*-
## desc: Check the class assignment umc module
## exposure: dangerous
## tags: [apptest, ucsschool]
## bugs: [50008]


import pytest

from ucsschool.lib.models.user import Teacher
from ucsschool.lib.models.group import SchoolClass

from univention.testing.ucsschool.ucs_test_school import UCSTestSchool
from univention.testing.umc import Client
import univention.testing.strings as uts


@pytest.fixture(scope='module')
def schoolenv():
    with UCSTestSchool() as schoolenv:
        schoolenv.schools = schoolenv.create_multiple_ous(3)
        schoolenv.school_classes = dict()
        for school, school_dn in schoolenv.schools:
            schoolenv.school_classes[school] = schoolenv.create_school_class(school, uts.random_string())
        yield schoolenv


class ChangeSchoolClassError(Exception):
    pass


class TestSchoolClassAssignmentDomainAdmin(object):

    @pytest.fixture(scope='class')
    def client(self):
        return Client.get_test_connection()

    def __flat_school_classes_dn(self, teacher):
        all_school_classes = []
        for school, school_classes in teacher.school_classes.items():
            all_school_classes += [SchoolClass(school_class, school).dn for school_class in school_classes]
        return all_school_classes

    def __test_class_assignment(self, primary_school, secondary_schools, old_class, new_classes):
        _, teacher_dn = self.schoolenv.create_teacher(
            primary_school,
            classes=old_class,
            schools=secondary_schools,
        )
        teacher = Teacher.from_dn(teacher_dn, primary_school, self.schoolenv.lo)
        original_classes = self.__flat_school_classes_dn(teacher)
        visible_classes = [c['id'] for c in self.client.umc_command('schoolgroups/get', flavor='teacher', options=[teacher_dn]).result[0]['classes']]
        result = self.client.umc_command('schoolgroups/put', flavor='teacher', options=[{'object': {
            '$dn$': teacher_dn,
            'classes': visible_classes + new_classes,
        }}])
        if result.result is False:
            raise ChangeSchoolClassError
        teacher = Teacher.from_dn(teacher_dn, primary_school, self.schoolenv.lo)
        assert set(self.__flat_school_classes_dn(teacher)) == set(original_classes + new_classes)
        self.client.umc_command('schoolgroups/put', flavor='teacher', options=[{'object': {
            '$dn$': teacher_dn,
            'classes': visible_classes,
        }}])
        teacher = Teacher.from_dn(teacher_dn, primary_school, self.schoolenv.lo)
        assert set(self.__flat_school_classes_dn(teacher)) == set(original_classes)

    def test_class_from_primary_school(self, schoolenv, client):
        schools = schoolenv.schools
        self.schoolenv = schoolenv
        self.client = client
        self.__test_class_assignment(
            schools[0][0],
            [schools[0][0], schools[1][0]],
            schoolenv.school_classes[schools[1][0]][0],
            [schoolenv.school_classes[schools[0][0]][1]],
        )

    def test_class_from_secondary_school(self, schoolenv, client):
        schools = schoolenv.schools
        self.schoolenv = schoolenv
        self.client = client
        self.__test_class_assignment(
            schools[0][0],
            [schools[0][0], schools[1][0]],
            schoolenv.school_classes[schools[0][0]][0],
            [schoolenv.school_classes[schools[1][0]][1]],
        )

    def test_classes_from_two_schools(self, schoolenv, client):
        schools = schoolenv.schools
        self.schoolenv = schoolenv
        self.client = client
        self.__test_class_assignment(
            schools[0][0],
            [schools[0][0], schools[1][0], schools[2][0]],
            schoolenv.school_classes[schools[2][0]][0],
            [schoolenv.school_classes[schools[0][0]][1], schoolenv.school_classes[schools[1][0]][1]],
        )


class TestSchoolClassAssignmentSchoolAdmin(TestSchoolClassAssignmentDomainAdmin):

    @pytest.fixture(scope='class')
    def client(self, schoolenv):
        schools = schoolenv.schools
        school_admin, school_admin_dn = schoolenv.create_school_admin(schools[1][0], schools=[schools[0][0], schools[1][0]])
        return Client(username=school_admin, password='univention')


class TestSchoolClassAssignmentSchoolAdminSecondary(TestSchoolClassAssignmentDomainAdmin):

    @pytest.fixture(scope='class')
    def client(self, schoolenv):
        schools = schoolenv.schools
        school_admin, school_admin_dn = schoolenv.create_school_admin(schools[1][0])
        return Client(username=school_admin, password='univention')

    def test_class_from_primary_school(self, schoolenv, client):
        with pytest.raises(ChangeSchoolClassError):
            super(TestSchoolClassAssignmentSchoolAdminSecondary, self).test_class_from_primary_school(schoolenv, client)

    def test_classes_from_two_schools(self, schoolenv, client):
        with pytest.raises(ChangeSchoolClassError):
            super(TestSchoolClassAssignmentSchoolAdminSecondary, self).test_classes_from_two_schools(schoolenv, client)
