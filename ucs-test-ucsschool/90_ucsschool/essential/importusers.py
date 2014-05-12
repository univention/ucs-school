## -*- coding: utf-8 -*-

import os
import smbpasswd
import string
import subprocess
import tempfile
import univention.testing.utils as utils
import univention.testing.strings as uts

from essential.importou import remove_ou

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
		self.username = uts.random_name()
		self.school = school
		self.role = role
		self.mail = '%s@%s' % (self.username, configRegistry.get('domainname'))
		self.classes = []
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

		if configRegistry.is_true('ucsschool/ldap/district/enable'):
			self.school_base = 'ou=%(ou)s,ou=%(district)s,%(basedn)s' % {'ou': self.school, 'district': self.school[0:2], 'basedn': configRegistry.get('ldap/base')}
		else:
			self.school_base = 'ou=%(ou)s,%(basedn)s' % {'ou': self.school, 'basedn': configRegistry.get('ldap/base')}

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
		line += ','.join(self.classes)
		line += delimiter
		line += ''	# TODO: rights?
		line += delimiter
		line += self.mail # TODO: Do we need to create the mail domain object?
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
		self.classes.append('%s-%s%s' % (self.school, uts.random_int(), uts.random_string(length=1, alpha=True, numeric=False)))

	def append_random_working_group(self):
		self.classes.append('%s-%s' % (self.school, uts.random_string(length=9, alpha=True, numeric=False)))

	def is_student(self):
		return self.role == 'student'

	def is_teacher(self):
		return self.role == 'teacher'

	def is_staff(self):
		return self.role == 'staff'

	def is_teacher_staff(self):
		return self.role == 'teacher_staff'

	def expected_attributes(self):
		attr = {}
		attr['uid'] = [self.username]
		attr['givenName'] = [self.firstname]
		attr['sn'] = [self.lastname]
		attr['mailPrimaryAddress'] = [self.mail]
		attr['mail'] = [self.mail]

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

		if configRegistry.get('ucsschool/import/set/netlogon/script/path'):
			attr['sambaLogonScript'] = [configRegistry.get('ucsschool/import/set/netlogon/script/path')]
		if configRegistry.get('ucsschool/import/set/homedrive'):
			attr['sambaHomeDrive'] = [configRegistry.get('ucsschool/import/set/homedrive')]
		
		# TODO:
		#		if calculateSambahomePath(getDN(person.sNr, basedn=baseDN), object["username"]) is not None:
		#			object["sambahome"] = calculateSambahomePath(getDN(person.sNr, basedn=baseDN), object["username"])
		#		profilePath = calculateProfilePath(getDN(person.sNr, basedn=baseDN))
		#		if profilePath:
		#			object["profilepath"] = profilePath
		return attr

	def verify(self):
		print 'verify person: %s' % self.username

		if self.mode == 'D':
			utils.verify_ldap_object(self.dn, should_exist=False)
			return

		utils.verify_ldap_object(self.dn, expected_attr=self.expected_attributes(), should_exist=True)

		default_group_dn = 'cn=Domain Users %s,cn=groups,%s' % (self.school, self.school_base)
		utils.verify_ldap_object(default_group_dn, expected_attr={'uniqueMember': [self.dn], 'memberUid': [self.username]}, strict=False, should_exist=True)

		for cl in self.classes:
			cl_group_dn = 'cn=%s,cn=klassen,cn=%s,cn=groups,%s' % (cl, cn_pupils, self.school_base)
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

	def write_import(self, data):
		self.import_fd = os.open(self.import_file, os.O_RDWR|os.O_CREAT)
		os.write(self.import_fd, data)
		os.close(self.import_fd)

	def run_import(self, data):
		hooks = UserHooks()
		try:
			self.write_import(data)
			if self.use_cli_api:
				self._run_import_via_cli()
			elif self.use_python_api:
				self._run_import_via_python_api()
			pre_result = hooks.get_pre_result()
			post_result = hooks.get_post_result()
			print 'PRE  HOOK result: %s' % pre_result
			print 'POST HOOK result: %s' % post_result
			print 'SCHOOL DATA     : %s' % data
			if pre_result != post_result != data:
				raise UserHookResult()
		finally:
			hooks.cleanup()
			os.remove(self.import_file)

	def _run_import_via_cli(self):
		cmd_block = ['/usr/share/ucs-school-import/scripts/import_user', self.import_file]

		print 'cmd_block: %r' % cmd_block
		retcode = subprocess.call(cmd_block, shell=False)
		if retcode:
			raise ImportUser('Failed to execute "%s". Return code: %d.' % (string.join(cmd_block), retcode))

	def _run_import_via_python_api(self):
		raise NotImplementedError

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
			os.chmod(pre_hook, 0755)

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
			os.chmod(post_hook, 0755)

	def cleanup(self):
		for pre_hook in self.pre_hooks:
			os.remove(pre_hook)
		for post_hook in self.post_hooks:
			os.remove(post_hook)
		os.remove(self.pre_hook_result)
		os.remove(self.post_hook_result)
		
class UserImport:
	def __init__(self, nr_students=20, nr_teachers=10, nr_staff=5, nr_teacher_staff=3):
		assert (nr_students > 2)
		assert (nr_teachers > 2)
		assert (nr_staff > 2)
		assert (nr_teacher_staff > 2)

		# TODO: multi schools ?
		self.school = uts.random_name()

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
		# TODO: rename?
		# self.students[1].username = uts.random_name()
		self.students[2].firstname = uts.random_name()
		self.students[2].lastname = uts.random_name()
		self.students[2].set_inactive()

		for teacher in self.teachers:
			teacher.set_mode_to_modify()
		self.students[0].mail = '%s@%s' % (uts.random_name(), configRegistry.get('domainname'))
		# TODO: rename?
		# self.students[1].username = uts.random_name()
		self.students[2].firstname = uts.random_name()
		self.students[2].lastname = uts.random_name()

		for staff in self.staff:
			staff.set_mode_to_modify()
		self.students[0].set_inactive()
		# TODO: rename?
		# self.students[1].username = uts.random_name()
		self.students[2].firstname = uts.random_name()
		self.students[2].lastname = uts.random_name()

		for teacher_staff in self.teacher_staff:
			teacher_staff.set_mode_to_modify()
		self.students[0].set_inactive()
		# TODO: rename?
		# self.students[1].username = uts.random_name()
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


def create_and_verify_users(use_cli_api=True, use_python_api=False, nr_students=3, nr_teachers=3, nr_staff=3, nr_teacher_staff=3):
	assert(use_cli_api != use_python_api)

	print '********** Generate school data'
	user_import = UserImport(nr_students=nr_students, nr_teachers=nr_teachers, nr_staff=nr_staff, nr_teacher_staff=nr_teacher_staff)
	import_file = ImportFile(use_cli_api, use_python_api)

	print user_import

	try:
		print '********** Create users'
		import_file.run_import(str(user_import))
		user_import.verify()

		print '********** Modify users'
		user_import.modify()
		import_file.run_import(str(user_import))
		user_import.verify()

		print '********** Delete users'
		user_import.delete()
		import_file.run_import(str(user_import))
		user_import.verify()

	finally:
		remove_ou(user_import.school)


def import_users_basics(use_cli_api=True, use_python_api=False):
	create_and_verify_users(use_cli_api, use_python_api, 5, 4, 3, 3)

