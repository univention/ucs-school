## -*- coding: utf-8 -*-

import ldap
import os
import smbpasswd
import string
import subprocess
import tempfile
import univention.testing.strings as uts
import univention.testing.ucr
import univention.testing.utils as utils
import univention.testing.udm as udm_test
import univention.uldap
from ucsschool.lib.models import Student as StudentLib
from ucsschool.lib.models import Teacher as TeacherLib
from ucsschool.lib.models import Staff as StaffLib
from ucsschool.lib.models import TeachersAndStaff as TeachersAndStaffLib
from ucsschool.lib.models import School as SchoolLib
import ucsschool.lib.models.utils

from essential.importou import remove_ou, create_ou_cli, get_school_base

from univention.testing.decorators import SetTimeout
utils.verify_ldap_object = SetTimeout(utils.verify_ldap_object)

HOOK_BASEDIR = '/usr/share/ucs-school-import/hooks'


class ImportUser(Exception):
	pass


class UserHookResult(Exception):
	pass

import univention.config_registry
configRegistry = univention.config_registry.ConfigRegistry()
configRegistry.load()

cn_pupils = configRegistry.get('ucsschool/ldap/default/container/pupils', 'schueler')
cn_teachers = configRegistry.get('ucsschool/ldap/default/container/teachers', 'lehrer')
cn_teachers_staff = configRegistry.get('ucsschool/ldap/default/container/teachers-and-staff', 'lehrer und mitarbeiter')
cn_staff = configRegistry.get('ucsschool/ldap/default/container/staff', 'mitarbeiter')

grp_prefix_pupils = configRegistry.get('ucsschool/ldap/default/groupprefix/pupils', 'schueler-')
grp_prefix_teachers = configRegistry.get('ucsschool/ldap/default/groupprefix/teachers', 'lehrer-')
grp_prefix_admins = configRegistry.get('ucsschool/ldap/default/groupprefix/admins', 'admins-')
grp_prefix_staff = configRegistry.get('ucsschool/ldap/default/groupprefix/staff', 'mitarbeiter-')


class Person:

	def __init__(self, school, role):
		self.firstname = uts.random_name()
		self.lastname = uts.random_name()
		self.username = uts.random_name()
		self.school = school
		self.role = role
		self.record_uid = None
		self.source_uid = None
		self.description = None
		self.mail = '%s@%s' % (self.username, configRegistry.get('domainname'))
		self.school_classes = {}
		if self.is_student():
			self.append_random_class()
			self.append_random_working_group()
			self.cn = cn_pupils
			self.grp_prefix = grp_prefix_pupils
		elif self.is_teacher():
			self.append_random_class()
			self.append_random_class()
			self.append_random_class()
			self.append_random_working_group()
			self.append_random_working_group()
			self.cn = cn_teachers
			self.grp_prefix = grp_prefix_teachers
		elif self.is_teacher_staff():
			self.append_random_class()
			self.append_random_working_group()
			self.append_random_working_group()
			self.cn = cn_teachers_staff
			self.grp_prefix = grp_prefix_teachers
		elif self.is_staff():
			self.cn = cn_staff
			self.grp_prefix = grp_prefix_staff
		self.mode = 'A'
		self.active = True
		self.password = None

		self.school_base = get_school_base(self.school)

		self.dn = 'uid=%s,cn=%s,cn=users,%s' % (self.username, self.cn, self.school_base)

	def set_mode_to_modify(self):
		self.mode = 'M'

	def set_mode_to_delete(self):
		self.mode = 'D'

	def set_active(self):
		self.active = True

	def set_inactive(self):
		self.active = False

	def is_active(self):
		return self.active

	def update(self, **kwargs):
		for key in kwargs:
			if key == 'dn':
				self.username = ldap.explode_rdn(kwargs[key], notypes=1)[0]
				self.dn = kwargs[key]
			elif key == 'school':
				self.school = kwargs[key]
				self.school_base = get_school_base(self.school)
			elif hasattr(self, key):
				setattr(self, key, kwargs[key])
			else:
				print 'ERROR: cannot update Person(): unknown option %r=%r' % (key, kwargs[key])

	def map_to_dict(self, value_map):
		result = {
			value_map.get('firstname', '__EMPTY__'): self.firstname,
			value_map.get('lastname', '__EMPTY__'): self.lastname,
			value_map.get('username', '__EMPTY__'): self.username,
			value_map.get('schools', '__EMPTY__'): self.school,
			value_map.get('role', '__EMPTY__'): self.role,
			value_map.get('record_uid', '__EMPTY__'): self.record_uid,
			value_map.get('source_uid', '__EMPTY__'): self.source_uid,
			value_map.get('description', '__EMPTY__'): self.description,
			value_map.get('school_classes', '__EMPTY__'): ','.join([x for school_, classes in self.school_classes.iteritems() for x in classes]),
			value_map.get('email', '__EMPTY__'): self.mail,
			value_map.get('__action', '__EMPTY__'): self.mode,
		}
		if '__EMPTY__' in result.keys():
			del result['__EMPTY__']
		return result

	def __str__(self):
		delimiter = '\t'
		line = self.mode
		line += delimiter
		line += self.username
		line += delimiter
		line += self.lastname
		line += delimiter
		line += self.firstname
		line += delimiter
		line += self.school
		line += delimiter
		line += ','.join([x for school_, classes in self.school_classes.iteritems() for x in classes])
		line += delimiter
		line += ''
		line += delimiter
		line += self.mail
		line += delimiter
		if self.is_teacher() or self.is_teacher_staff():
			line += '1'
		else:
			line += '0'
		line += delimiter
		line += '1' if self.is_active() else '0'
		line += delimiter
		if self.is_staff() or self.is_teacher_staff():
			line += '1'
		else:
			line += '0'
		if self.password:
			line += delimiter
			line += self.password
		return line

	def append_random_class(self):
		self.school_classes.setdefault(self.school, []).append('%s-%s%s' % (self.school, uts.random_int(), uts.random_string(length=1, alpha=True, numeric=False)))

	def append_random_working_group(self):
		return
		# working groups cannot be specified, neither in file for CLI nor by API in Python
		self.school_classes.setdefault(self.school, []).append('%s-%s' % (self.school, uts.random_string(length=9, alpha=True, numeric=False)))

	def is_student(self):
		return self.role == 'student'

	def is_teacher(self):
		return self.role == 'teacher'

	def is_staff(self):
		return self.role == 'staff'

	def is_teacher_staff(self):
		return self.role in ('teacher_staff', 'teacher_and_staff')

	def expected_attributes(self):
		attr = {}
		attr['uid'] = [self.username]
		attr['givenName'] = [self.firstname]
		attr['sn'] = [self.lastname]
		if self.mail:
			attr['mailPrimaryAddress'] = [self.mail]
			attr['mail'] = [self.mail]
		else:
			attr['mailPrimaryAddress'] = []
			attr['mail'] = []

		if self.source_uid:
			attr['ucsschoolSourceUID'] = [self.source_uid]
		if self.record_uid:
			attr['ucsschoolRecordUID'] = [self.record_uid]
		if self.description:
			attr['description'] = [self.description]

		subdir = ''
		if configRegistry.is_true('ucsschool/import/roleshare', True):
			if self.is_student():
				subdir = os.path.join(self.school, 'schueler')
			elif self.is_teacher():
				subdir = os.path.join(self.school, 'lehrer')
			elif self.is_teacher_staff():
				subdir = os.path.join(self.school, 'lehrer')
			elif self.is_staff():
				subdir = os.path.join(self.school, 'mitarbeiter')
		attr['homeDirectory'] = ['/home/%s' % os.path.join(subdir, self.username)]

		if self.is_active():
			attr['krb5KDCFlags'] = ['126']
			attr['sambaAcctFlags'] = ['[U          ]']
			attr['shadowExpire'] = []
		else:
			attr['krb5KDCFlags'] = ['254']
			attr['sambaAcctFlags'] = ['[UD         ]']
			attr['shadowExpire'] = ['1']
		attr['departmentNumber'] = [self.school]

		if self.password:
			attr['sambaNTPassword'] = [smbpasswd.nthash(self.password)]

		if not self.is_staff():
			if configRegistry.get('ucsschool/import/set/netlogon/script/path'):
				attr['sambaLogonScript'] = [configRegistry.get('ucsschool/import/set/netlogon/script/path')]
			if configRegistry.get('ucsschool/import/set/homedrive'):
				attr['sambaHomeDrive'] = [configRegistry.get('ucsschool/import/set/homedrive')]

			samba_home_path_server = self.get_samba_home_path_server()
			if samba_home_path_server:
				attr['sambaHomePath'] = ['\\\\%s\\%s' % (samba_home_path_server, self.username)]

			profile_path_server = self.get_profile_path_server()
			if profile_path_server:
				attr['sambaProfilePath'] = [profile_path_server]
		else:
			attr['sambaLogonScript'] = []
			attr['sambaHomeDrive'] = []
			attr['sambaHomePath'] = []
			attr['sambaProfilePath'] = []

		return attr

	def get_samba_home_path_server(self):
		if configRegistry.get('ucsschool/import/set/sambahome'):
			print 'get_samba_home_path_server: UCR variable ucsschool/import/set/sambahome is set'
			return configRegistry.get('ucsschool/import/set/sambahome')
		if configRegistry.is_true('ucsschool/singlemaster', False):
			print 'get_samba_home_path_server: Singlemaster'
			return configRegistry.get('hostname')
		lo = univention.uldap.getMachineConnection()
		result = lo.search(base=self.school_base, scope=ldap.SCOPE_BASE, attr=['ucsschoolHomeShareFileServer'])
		if result:
			share_file_server_dn = result[0][1].get('ucsschoolHomeShareFileServer')[0]
			return ldap.explode_rdn(share_file_server_dn, notypes=1)[0]
		return None

	def get_profile_path_server(self):
		if configRegistry.get('ucsschool/import/set/serverprofile/path'):
			print 'get_profile_path_server: UCR variable ucsschool/import/set/serverprofile/path is set'
			return configRegistry.get('ucsschool/import/set/serverprofile/path')
		lo = univention.uldap.getMachineConnection()
		result = lo.search(base=self.school_base, filter='univentionService=Windows Profile Server', attr=['cn'])
		if result:
			server = '\\\\%s' % result[0][1].get('cn')[0]
		else:
			server = '%LOGONSERVER%'

		return server + '\\%USERNAME%\\windows-profiles\\default'

	def verify(self):
		print 'verify person: %s' % self.username
		# reload UCR
		configRegistry.load()

		if self.mode == 'D':
			utils.verify_ldap_object(self.dn, should_exist=False)
			return

		utils.verify_ldap_object(self.dn, expected_attr=self.expected_attributes(), strict=True, should_exist=True)

		default_group_dn = 'cn=Domain Users %s,cn=groups,%s' % (self.school, self.school_base)
		utils.verify_ldap_object(default_group_dn, expected_attr={'uniqueMember': [self.dn], 'memberUid': [self.username]}, strict=False, should_exist=True)

		for school, classes in self.school_classes.iteritems():
			for cl in classes:
				cl_group_dn = 'cn=%s,cn=klassen,cn=%s,cn=groups,%s' % (cl, cn_pupils, get_school_base(school))
				utils.verify_ldap_object(cl_group_dn, expected_attr={'uniqueMember': [self.dn], 'memberUid': [self.username]}, strict=False, should_exist=True)

		role_group_dn = 'cn=%s%s,cn=groups,%s' % (self.grp_prefix, self.school, self.school_base)
		utils.verify_ldap_object(role_group_dn, expected_attr={'uniqueMember': [self.dn], 'memberUid': [self.username]}, strict=False, should_exist=True)


class Student(Person):

	def __init__(self, school):
		Person.__init__(self, school, 'student')


class Teacher(Person):

	def __init__(self, school):
		Person.__init__(self, school, 'teacher')


class Staff(Person):

	def __init__(self, school):
		Person.__init__(self, school, 'staff')


class TeacherStaff(Person):

	def __init__(self, school):
		Person.__init__(self, school, 'teacher_staff')


class ImportFile:

	def __init__(self, use_cli_api, use_python_api):
		self.use_cli_api = use_cli_api
		self.use_python_api = use_python_api
		self.import_fd, self.import_file = tempfile.mkstemp()
		os.close(self.import_fd)
		self.user_import = None

	def write_import(self):
		self.import_fd = os.open(self.import_file, os.O_RDWR | os.O_CREAT)
		os.write(self.import_fd, str(self.user_import))
		os.close(self.import_fd)

	def run_import(self, user_import):
		hooks = UserHooks()
		self.user_import = user_import
		try:
			if self.use_cli_api:
				self.write_import()
				self._run_import_via_cli()
			elif self.use_python_api:
				self._run_import_via_python_api()
			pre_result = hooks.get_pre_result()
			post_result = hooks.get_post_result()
			print 'PRE  HOOK result:\n%s' % pre_result
			print 'POST HOOK result:\n%s' % post_result
			print 'SCHOOL DATA     :\n%s' % str(self.user_import)
			if pre_result != post_result != str(self.user_import):
				raise UserHookResult()
		finally:
			hooks.cleanup()
			try:
				os.remove(self.import_file)
			except OSError as e:
				print 'WARNING: %s not removed. %s' % (self.import_file, e)

	def _run_import_via_cli(self):
		cmd_block = ['/usr/share/ucs-school-import/scripts/import_user', self.import_file]

		print 'cmd_block: %r' % cmd_block
		retcode = subprocess.call(cmd_block, shell=False)
		if retcode:
			raise ImportUser('Failed to execute "%s". Return code: %d.' % (string.join(cmd_block), retcode))

	def _run_import_via_python_api(self):
		# reload UCR
		ucsschool.lib.models.utils.ucr.load()

		lo = univention.admin.uldap.getAdminConnection()[0]

		# get school from first user
		school = self.user_import.students[0].school

		school_obj = SchoolLib.cache(school, display_name=school)
		if not school_obj.exists(lo):
			school_obj.dc_name = uts.random_name()
			school_obj.create(lo)

		def _set_kwargs(user):
			kwargs = {
				'school': user.school,
				'schools': [user.school],
				'name': user.username,
				'firstname': user.firstname,
				'lastname': user.lastname,
				'school_classes': user.school_classes,
				'email': user.mail,
				'password': user.password,
				'disabled': 'none' if user.active else 'all',
			}
			return kwargs

		for user in self.user_import.students:
			kwargs = _set_kwargs(user)
			if user.mode == 'A':
				StudentLib(**kwargs).create(lo)
			elif user.mode == 'M':
				StudentLib(**kwargs).modify(lo)
			elif user.mode == 'D':
				StudentLib(**kwargs).remove(lo)

		for user in self.user_import.teachers:
			kwargs = _set_kwargs(user)
			if user.mode == 'A':
				TeacherLib(**kwargs).create(lo)
			elif user.mode == 'M':
				TeacherLib(**kwargs).modify(lo)
			elif user.mode == 'D':
				TeacherLib(**kwargs).remove(lo)

		for user in self.user_import.staff:
			kwargs = _set_kwargs(user)
			if user.mode == 'A':
				StaffLib(**kwargs).create(lo)
			elif user.mode == 'M':
				StaffLib(**kwargs).modify(lo)
			elif user.mode == 'D':
				StaffLib(**kwargs).remove(lo)

		for user in self.user_import.teacher_staff:
			kwargs = _set_kwargs(user)
			if user.mode == 'A':
				TeachersAndStaffLib(**kwargs).create(lo)
			elif user.mode == 'M':
				TeachersAndStaffLib(**kwargs).modify(lo)
			elif user.mode == 'D':
				TeachersAndStaffLib(**kwargs).remove(lo)


class UserHooks:

	def __init__(self):
		fd, self.pre_hook_result = tempfile.mkstemp()
		os.close(fd)

		fd, self.post_hook_result = tempfile.mkstemp()
		os.close(fd)

		self.pre_hooks = []
		self.post_hooks = []

		self.create_hooks()

	def get_pre_result(self):
		return open(self.pre_hook_result, 'r').read()

	def get_post_result(self):
		return open(self.post_hook_result, 'r').read()

	def create_hooks(self):
		self.pre_hooks = [
				os.path.join(os.path.join(HOOK_BASEDIR, 'user_create_pre.d'), uts.random_name()),
				os.path.join(os.path.join(HOOK_BASEDIR, 'user_remove_pre.d'), uts.random_name()),
				os.path.join(os.path.join(HOOK_BASEDIR, 'user_modify_pre.d'), uts.random_name()),
		]

		self.post_hooks = [
				os.path.join(os.path.join(HOOK_BASEDIR, 'user_create_post.d'), uts.random_name()),
				os.path.join(os.path.join(HOOK_BASEDIR, 'user_modify_post.d'), uts.random_name()),
				os.path.join(os.path.join(HOOK_BASEDIR, 'user_remove_post.d'), uts.random_name()),
		]

		for pre_hook in self.pre_hooks:
			with open(pre_hook, 'w+') as fd:
				fd.write('''#!/bin/sh
set -x
test $# = 1 || exit 1
cat $1 >>%(pre_hook_result)s
exit 0
''' % {'pre_hook_result': self.pre_hook_result})
			os.chmod(pre_hook, 0o755)

		for post_hook in self.post_hooks:
			with open(post_hook, 'w+') as fd:
				fd.write('''#!/bin/sh
set -x
dn="$2"
username="$(cat $1 | awk -F '\t' '{print $2}')"
mode="$(cat $1 | awk -F '\t' '{print $1}')"
if [ "$mode" != D ]; then
	ldap_dn="$(univention-ldapsearch uid="$username" | ldapsearch-wrapper | sed -ne 's|dn: ||p')"
	test "$dn" = "$ldap_dn" || exit 1
fi
cat $1 >>%(post_hook_result)s
exit 0
''' % {'post_hook_result': self.post_hook_result})
			os.chmod(post_hook, 0o755)

	def cleanup(self):
		for pre_hook in self.pre_hooks:
			os.remove(pre_hook)
		for post_hook in self.post_hooks:
			os.remove(post_hook)
		os.remove(self.pre_hook_result)
		os.remove(self.post_hook_result)


class UserImport:

	def __init__(self, school_name=None, nr_students=20, nr_teachers=10, nr_staff=5, nr_teacher_staff=3):
		assert (nr_students > 2)
		assert (nr_teachers > 2)
		assert (nr_staff > 2)
		assert (nr_teacher_staff > 2)

		self.school = school_name

		self.students = []
		for i in range(0, nr_students):
			self.students.append(Student(self.school))
		self.students[2].set_inactive()
		self.students[0].password = uts.random_name()

		self.teachers = []
		for i in range(0, nr_teachers):
			self.teachers.append(Teacher(self.school))
		self.teachers[1].set_inactive()
		self.teachers[1].password = uts.random_name()

		self.staff = []
		for i in range(0, nr_staff):
			self.staff.append(Staff(self.school))
		self.staff[2].set_inactive()
		self.staff[1].password = uts.random_name()

		self.teacher_staff = []
		for i in range(0, nr_teacher_staff):
			self.teacher_staff.append(TeacherStaff(self.school))
		self.teacher_staff[1].set_inactive()
		self.teacher_staff[2].password = uts.random_name()

	def __str__(self):
		lines = []

		for student in self.students:
			lines.append(str(student))

		for teacher in self.teachers:
			lines.append(str(teacher))

		for staff in self.staff:
			lines.append(str(staff))

		for teacher_staff in self.teacher_staff:
			lines.append(str(teacher_staff))

		return '\n'.join(lines)

	def verify(self):
		for student in self.students:
			student.verify()

		for teacher in self.teachers:
			teacher.verify()

		for staff in self.staff:
			staff.verify()

		for teacher_staff in self.teacher_staff:
			teacher_staff.verify()

	def modify(self):
		for student in self.students:
			student.set_mode_to_modify()
		self.students[1].mail = '%s@%s' % (uts.random_name(), configRegistry.get('domainname'))
		self.students[2].firstname = uts.random_name()
		self.students[2].lastname = uts.random_name()
		self.students[2].set_inactive()

		for teacher in self.teachers:
			teacher.set_mode_to_modify()
		self.students[0].mail = '%s@%s' % (uts.random_name(), configRegistry.get('domainname'))
		self.students[2].firstname = uts.random_name()
		self.students[2].lastname = uts.random_name()

		for staff in self.staff:
			staff.set_mode_to_modify()
		self.students[0].set_inactive()
		self.students[2].firstname = uts.random_name()
		self.students[2].lastname = uts.random_name()

		for teacher_staff in self.teacher_staff:
			teacher_staff.set_mode_to_modify()
		self.students[0].set_inactive()
		self.students[2].firstname = uts.random_name()
		self.students[2].lastname = uts.random_name()

	def delete(self):
		for student in self.students:
			student.set_mode_to_delete()

		for teacher in self.teachers:
			teacher.set_mode_to_delete()

		for staff in self.staff:
			staff.set_mode_to_delete()

		for teacher_staff in self.teacher_staff:
			teacher_staff.set_mode_to_delete()


def create_and_verify_users(use_cli_api=True, use_python_api=False, school_name=None, nr_students=3, nr_teachers=3, nr_staff=3, nr_teacher_staff=3):
	assert(use_cli_api != use_python_api)

	print '********** Generate school data'
	user_import = UserImport(school_name=school_name, nr_students=nr_students, nr_teachers=nr_teachers, nr_staff=nr_staff, nr_teacher_staff=nr_teacher_staff)
	import_file = ImportFile(use_cli_api, use_python_api)

	print user_import

	print '********** Create users'
	import_file.run_import(user_import)
	user_import.verify()

	print '********** Modify users'
	user_import.modify()
	import_file.run_import(user_import)
	user_import.verify()

	print '********** Delete users'
	user_import.delete()
	import_file.run_import(user_import)
	user_import.verify()


def create_windows_profile_server(udm, ou, name):
	properties = {
		'name': name,
		'service': 'Windows Profile Server',
	}
	school_base = get_school_base(ou)

	udm.create_object('computers/memberserver', position=school_base, **properties)


def create_home_server(udm, name):
	properties = {
		'name': name,
	}
	udm.create_object('computers/memberserver', **properties)


def import_users_basics(use_cli_api=True, use_python_api=False):
	ucr = univention.testing.ucr.UCSTestConfigRegistry()
	ucr.load()

	udm = udm_test.UCSTestUDM()

	for singlemaster in [False, True]:
		for samba_home_server in [None, 'generate']:
			for profile_path_server in [None, 'generate']:
				for home_server_at_ou in [None, 'generate']:
					for windows_profile_server in [None, 'generate']:

						if samba_home_server == 'generate':
							samba_home_server = uts.random_name()

						if profile_path_server == 'generate':
							profile_path_server = uts.random_name()

						school_name = uts.random_name()

						if home_server_at_ou:
							home_server_at_ou = uts.random_name()
							create_home_server(udm, home_server_at_ou)
							create_ou_cli(school_name, sharefileserver=home_server_at_ou)
						else:
							create_ou_cli(school_name)

						try:
							if windows_profile_server:
								windows_profile_server = uts.random_name()
								create_windows_profile_server(udm=udm, ou=school_name, name=windows_profile_server)

							univention.config_registry.handler_set([
								'ucsschool/singlemaster=%s' % ('true' if singlemaster else 'false'),
								'ucsschool/import/set/sambahome=%s' % samba_home_server,
								'ucsschool/import/set/serverprofile/path=%s' % profile_path_server,
							])

							if not samba_home_server:
								univention.config_registry.handler_unset([
									'ucsschool/import/set/sambahome',
								])

							if not profile_path_server:
								univention.config_registry.handler_unset([
									'ucsschool/import/set/serverprofile/path',
								])

							print ''
							print '**** import_users_basics:'
							print '****    singlemaster: %s' % singlemaster
							print '****    samba_home_server: %s' % samba_home_server
							print '****    profile_path_server: %s' % profile_path_server
							print '****    home_server_at_ou: %s' % home_server_at_ou
							print '****    windows_profile_server: %s' % windows_profile_server
							print ''
							create_and_verify_users(use_cli_api, use_python_api, school_name, 3, 3, 3, 3)
						finally:
							remove_ou(school_name)

	utils.wait_for_replication()
