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
from univention.testing.utils import wait_for_listener_replication


@pytest.fixture(scope='module')
def schoolenv():
	with UCSTestSchool() as schoolenv:
		hostname = schoolenv.ucr['hostname']

		schoolenv.school = schoolenv.create_ou(name_edudc=hostname)
		schoolenv.schools = [schoolenv.school] + schoolenv.create_multiple_ous(2, name_edudc=uts.random_name(), name_share_file_server=hostname)
		schoolenv.school_classes = dict()
		client = Client.get_test_connection(hostname=schoolenv.ucr['ldap/master'])
		for school, school_dn in schoolenv.schools:
			class_name = uts.random_string()
			grp_dn = 'cn={}-{},cn=klassen,cn=schueler,cn=groups,ou={},{}'.format(school, class_name, school, schoolenv.LDAP_BASE)
			client.umc_command(
				'schoolwizards/classes/add',
				flavor='schoolwizards/classes',
				options=[{
					'object': {'school': school, 'name': class_name, 'description': ''}
				}]
			)
			schoolenv.school_classes[school] = ('{}-{}'.format(school, class_name), grp_dn, )
		yield schoolenv


class ChangeSchoolClassError(Exception):
	pass


class __TestSchoolClassAssignment(object):

	@pytest.fixture(scope='class')
	def client(self):
		return Client.get_test_connection()

	def __flat_school_classes_dn(self, teacher):
		all_school_classes = []
		for school, school_classes in teacher.school_classes.items():
			all_school_classes += [SchoolClass(school_class, school).dn for school_class in school_classes]
		return all_school_classes

	def __test_class_assignment(self, primary_school, secondary_schools, old_class, new_classes):
		print(primary_school)
		print(old_class)
		print(secondary_schools)
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
		wait_for_listener_replication()
		if result.result is False:
			raise ChangeSchoolClassError
		teacher = Teacher.from_dn(teacher_dn, primary_school, self.schoolenv.lo)
		assert set(self.__flat_school_classes_dn(teacher)) == set(original_classes + new_classes)
		self.client.umc_command('schoolgroups/put', flavor='teacher', options=[{'object': {
			'$dn$': teacher_dn,
			'classes': visible_classes,
		}}])
		wait_for_listener_replication()
		teacher = Teacher.from_dn(teacher_dn, primary_school, self.schoolenv.lo)
		assert set(self.__flat_school_classes_dn(teacher)) == set(original_classes)

	def test_class_from_primary_school(self, schoolenv, client, primary_school=None, secondary_school=None):
		# Teacher is at two schools. A class from his primary school is added.
		schools = schoolenv.schools
		if not primary_school:
			primary_school = schools[0]
		if not secondary_school:
			secondary_school = schools[1]
		self.schoolenv = schoolenv
		self.client = client
		self.__test_class_assignment(
			primary_school[0],
			[primary_school[0], secondary_school[0]],
			schoolenv.school_classes[secondary_school[0]][0],
			[schoolenv.school_classes[primary_school[0]][1]],
		)

	def test_class_from_secondary_school(self, schoolenv, client, primary_school=None, secondary_school=None):
		# Teacher is at two schools. A class from his secondary school is added.
		schools = schoolenv.schools
		if not primary_school:
			primary_school = schools[0]
		if not secondary_school:
			secondary_school = schools[1]
		self.schoolenv = schoolenv
		self.client = client
		self.__test_class_assignment(
			primary_school[0],
			[primary_school[0], secondary_school[0]],
			schoolenv.school_classes[primary_school[0]][0],
			[schoolenv.school_classes[secondary_school[0]][1]],
		)

	def test_classes_from_two_schools(self, schoolenv, client, primary_school=None, secondary_school=None):
		# Teacher is at three schools. A class from his primary school and from one of his secondaries is added.
		schools = schoolenv.schools
		if not primary_school:
			primary_school = schools[0]
		if not secondary_school:
			secondary_school = schools[1]
		self.schoolenv = schoolenv
		self.client = client
		self.__test_class_assignment(
			primary_school[0],
			[primary_school[0], secondary_school[0], schools[2][0]],
			schoolenv.school_classes[schools[2][0]][0],
			[schoolenv.school_classes[primary_school[0]][1], schoolenv.school_classes[secondary_school[0]][1]],
		)


class TestSchoolClassAssignmentDomainAdmin(__TestSchoolClassAssignment):

	def test_class_from_secondary_school(self, schoolenv, client):
		__parent_func = super(TestSchoolClassAssignmentDomainAdmin, self).test_class_from_secondary_school
		if schoolenv.ucr['server/role'] == 'domaincontroller_slave':
			# Can't change school class members on differrent edu_dc
			with pytest.raises(ChangeSchoolClassError):
				__parent_func(schoolenv, client)
		else:
			__parent_func(schoolenv, client)

	def test_classes_from_two_schools(self, schoolenv, client):
		__parent_func = super(TestSchoolClassAssignmentDomainAdmin, self).test_classes_from_two_schools
		if schoolenv.ucr['server/role'] == 'domaincontroller_slave':
			# Can't change school class members on differrent edu_dc
			with pytest.raises(ChangeSchoolClassError):
				__parent_func(schoolenv, client)
		else:
			__parent_func(schoolenv, client)


class TestSchoolClassAssignmentSchoolAdmin(__TestSchoolClassAssignment):

	# The schooladmin has the same primary school as the teacher

	@pytest.fixture(scope='class')
	def client(self, schoolenv):
		school_admin, school_admin_dn = schoolenv.create_school_admin(
			schoolenv.school[0],
			is_teacher=True,
			is_staff=False,
		)
		return Client(username=school_admin, password='univention')

	def test_class_from_secondary_school(self, schoolenv, client):
		with pytest.raises(ChangeSchoolClassError):
			# Singleschool: Can't change schoool class members in differrent ou
			# Multischool: Can't change schoool class members on differrent edu_dc
			super(TestSchoolClassAssignmentSchoolAdmin, self).test_class_from_secondary_school(schoolenv, client)

	def test_classes_from_two_schools(self, schoolenv, client):
		with pytest.raises(ChangeSchoolClassError):
			# Singleschool: Can't change schoool class members in differrent ou
			# Multischool: Can't change schoool class members on differrent edu_dc
			super(TestSchoolClassAssignmentSchoolAdmin, self).test_classes_from_two_schools(schoolenv, client)


class TestSchoolClassAssignmentSchoolAdminPrimary(__TestSchoolClassAssignment):

	# The schooladmins primary school (this server) is the secondary school for the teacher

	@pytest.fixture(scope='class')
	def client(self, schoolenv):
		school_admin, school_admin_dn = schoolenv.create_school_admin(
			schoolenv.school[0],
			is_teacher=True,
			is_staff=False,
		)
		return Client(username=school_admin, password='univention')

	def test_class_from_primary_school(self, schoolenv, client):
		with pytest.raises(ChangeSchoolClassError):
			# Singleschool: Can't change schoool class members in differrent ou
			# Multischool: Can't change schoool class members on differrent edu_dc
			super(TestSchoolClassAssignmentSchoolAdminPrimary, self).test_class_from_primary_school(
				schoolenv,
				client,
				schoolenv.schools[1],
				schoolenv.school
			)

	def test_class_from_secondary_school(self, schoolenv, client):
		super(TestSchoolClassAssignmentSchoolAdminPrimary, self).test_class_from_secondary_school(
			schoolenv,
			client,
			schoolenv.schools[1],
			schoolenv.school
		)

	def test_classes_from_two_schools(self, schoolenv, client):
		with pytest.raises(ChangeSchoolClassError):
			# Singleschool: Can't change schoool class members in differrent ou
			# Multischool: Can't change schoool class members on differrent edu_dc
			super(TestSchoolClassAssignmentSchoolAdminPrimary, self).test_classes_from_two_schools(
				schoolenv,
				client,
				schoolenv.schools[1],
				schoolenv.school
			)


class TestSchoolClassAssignmentSchoolAdminSecondary(__TestSchoolClassAssignment):

	# The schooladmins secondary school is the primary school (this server) for the teacher

	@pytest.fixture(scope='class')
	def client(self, schoolenv):
		school_admin, school_admin_dn = schoolenv.create_school_admin(
			schoolenv.schools[1][0],
			is_teacher=True,
			is_staff=False,
			schools=[schoolenv.schools[1][0], schoolenv.schools[0][0]]
		)
		return Client(username=school_admin, password='univention')

	def test_class_from_secondary_school(self, schoolenv, client):
		__parent_func = super(TestSchoolClassAssignmentSchoolAdminSecondary, self).test_class_from_secondary_school
		if schoolenv.ucr['server/role'] == 'domaincontroller_slave':
			with pytest.raises(ChangeSchoolClassError):
				# Multischool: Can't change schoool class members on differrent edu_dc
				__parent_func(
					schoolenv,
					client
				)
		else:
			# Singleschool: School admin has this ou as secondary school
			__parent_func(
				schoolenv,
				client
			)

	def test_classes_from_two_schools(self, schoolenv, client):
		__parent_func = super(TestSchoolClassAssignmentSchoolAdminSecondary, self).test_classes_from_two_schools
		if schoolenv.ucr['server/role'] == 'domaincontroller_slave':
			with pytest.raises(ChangeSchoolClassError):
				# Multischool: Can't change schoool class members on differrent edu_dc
				__parent_func(
					schoolenv,
					client
				)
		else:
			# Singleschool: School admin has this ou as secondary school
			__parent_func(
				schoolenv,
				client
			)
