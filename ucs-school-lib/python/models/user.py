#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2016 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import os.path

from ldap.filter import escape_filter_chars

from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from ucsschool.lib.models.utils import create_passwd
from ucsschool.lib.models.attributes import Username, Firstname, Lastname, Birthday, Email, Password, Disabled, SchoolClassStringAttribute
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models.school import School
from ucsschool.lib.models.group import Group, SchoolClass
from ucsschool.lib.models.computer import AnyComputer
from ucsschool.lib.models.misc import MailDomain
from ucsschool.lib.models.utils import ucr, _, logger

class User(UCSSchoolHelperAbstractClass):
	name = Username(_('Username'), aka=['Username', 'Benutzername'])
	firstname = Firstname(_('First name'), aka=['First name', 'Vorname'], required=True, unlikely_to_change=True)
	lastname = Lastname(_('Last name'), aka=['Last name', 'Nachname'], required=True, unlikely_to_change=True)
	birthday = Birthday(_('Birthday'), aka=['Birthday', 'Geburtstag'], unlikely_to_change=True)
	email = Email(_('Email'), aka=['Email', 'E-Mail'], unlikely_to_change=True)
	password = Password(_('Password'), aka=['Password', 'Passwort'])
	disabled = Disabled(_('Disabled'), aka=['Disabled', 'Gesperrt'])
	school_class = None # not defined by default (Staff)

	type_name = None

	_profile_path_cache = {}
	_samba_home_path_cache = {}
	# _samba_home_path_cache is invalidated in School.invalidate_cache()

	roles = []

	@classmethod
	def shall_create_mail_domain(cls):
		return ucr.is_true('ucsschool/import/generate/mail/domain')

	def get_roleshare_home_subdir(self):
		from ucsschool.lib.roleshares import roleshare_home_subdir
		return roleshare_home_subdir(self.school, self.roles, ucr)

	def get_samba_home_drive(self):
		return ucr.get('ucsschool/import/set/homedrive')

	def get_samba_netlogon_script_path(self):
		return ucr.get('ucsschool/import/set/netlogon/script/path')

	def get_samba_home_path(self, lo):
		school = School.cache(self.school)
		# if defined then use UCR value
		ucr_variable = ucr.get('ucsschool/import/set/sambahome')
		if ucr_variable is not None:
			samba_home_path = r'\\%s' % ucr_variable.strip('\\')
		# in single server environments the master is always the fileserver
		elif ucr.is_true('ucsschool/singlemaster', False):
			samba_home_path = r'\\%s' % ucr.get('hostname')
		# if there's a cached result then use it
		elif school.dn not in self._samba_home_path_cache:
			samba_home_path = None
			# get windows home server from OU object
			school = self.get_school_obj(lo)
			home_share_file_server = school.home_share_file_server
			if home_share_file_server:
				samba_home_path = r'\\%s' % self.get_name_from_dn(home_share_file_server)
			self._samba_home_path_cache[school.dn] = samba_home_path
		else:
			samba_home_path = self._samba_home_path_cache[school.dn]
		if samba_home_path is not None:
			return r'%s\%s' % (samba_home_path, self.name)

	def get_profile_path(self, lo):
		ucr_variable = ucr.get('ucsschool/import/set/serverprofile/path')
		if ucr_variable is not None:
			return ucr_variable
		school = School.cache(self.school)
		if school.dn not in self._profile_path_cache:
			profile_path = r'%s\%%USERNAME%%\windows-profiles\default'
			for computer in AnyComputer.get_all(lo, self.school, 'univentionService=Windows Profile Server'):
				profile_path = profile_path % (r'\\%s' % computer.name)
				break
			else:
				profile_path = profile_path % '%LOGONSERVER%'
			self._profile_path_cache[school.dn] = profile_path
		return self._profile_path_cache[school.dn]

	def self_is_student(self):
		return self.is_student(self.school, self.dn)

	def self_is_teacher(self):
		return self.is_teacher(self.school, self.dn)

	def self_is_staff(self):
		return self.is_staff(self.school, self.dn)

	@classmethod
	def is_student(cls, school, dn):
		return cls.get_search_base(school).isStudent(dn)

	@classmethod
	def is_teacher(cls, school, dn):
		return cls.get_search_base(school).isTeacher(dn)

	@classmethod
	def is_staff(cls, school, dn):
		return cls.get_search_base(school).isStaff(dn)

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		if cls.is_student(school, udm_obj.dn):
			return Student
		if cls.is_teacher(school, udm_obj.dn):
			if cls.is_staff(school, udm_obj.dn):
				return TeachersAndStaff
			return Teacher
		if cls.is_staff(school, udm_obj.dn):
			return Staff
		return cls

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		obj = super(User, cls).from_udm_obj(udm_obj, school, lo)
		if obj:
			obj.password = None
			return obj

	def do_create(self, udm_obj, lo):
		self.create_mail_domain(lo)
		password_created = False
		if not self.password:
			logger.debug('No password given. Generating random one')
			old_password = self.password # None or ''
			self.password = create_passwd(dn=self.dn)
			password_created = True
		udm_obj['primaryGroup'] = self.primary_group_dn(lo)
		udm_obj['groups'] = self.groups_used(lo)
		subdir = self.get_roleshare_home_subdir()
		udm_obj['unixhome'] = '/home/' + os.path.join(subdir, self.name)
		udm_obj['overridePWHistory'] = '1'
		udm_obj['overridePWLength'] = '1'
		if self.disabled is None:
			udm_obj['disabled'] = 'none'
		if udm_obj.has_key('mailbox'):
			udm_obj['mailbox'] = '/var/spool/%s/' % self.name
		samba_home = self.get_samba_home_path(lo)
		if samba_home:
			udm_obj['sambahome'] = samba_home
		profile_path = self.get_profile_path(lo)
		if profile_path:
			udm_obj['profilepath'] = profile_path
		home_drive = self.get_samba_home_drive()
		if home_drive is not None:
			udm_obj['homedrive'] = home_drive
		script_path = self.get_samba_netlogon_script_path()
		if script_path is not None:
			udm_obj['scriptpath'] = script_path
		success = super(User, self).do_create(udm_obj, lo)
		if password_created:
			# to not show up in host_hooks
			self.password = old_password
		return success

	def do_modify(self, udm_obj, lo):
		self.create_mail_domain(lo)
		self.password = self.password or None
		mandatory_groups = self.groups_used(lo)
		all_schools = School.get_all(lo, respect_local_oulist=False)
		for group_dn in udm_obj['groups'][:]:
			logger.debug('Checking group %s for removal' % group_dn)
			if group_dn not in mandatory_groups:
				logger.debug('Group not mandatory! Part of a school?')
				for school in all_schools:
					if Group.is_school_group(school.name, group_dn):
						logger.debug('Yes, part of %s!' % school)
						# Okay. What now?
						#   -> "Foreign school"? -> remove
						#   -> "My school"?
						#      -> is_no_school_class (e.g. working group)? -> stay
						#      -> is_school_class and self defined its own classes? -> remove as not in mandatory
						remove = school.name != self.school
						if not remove:
							remove = self.school_class is not None and Group.is_school_class(school.name, group_dn)
						if remove:
							logger.debug('Removing it!')
							udm_obj['groups'].remove(group_dn)
						else:
							logger.debug('Leaving it alone: Part of own school and either non-school class or new school classes were not defined at all')
						break
				else:
					logger.debug('No. Leaving it alone...')
		for group_dn in mandatory_groups:
			logger.debug('Checking group %s for adding' % group_dn)
			if group_dn not in udm_obj['groups']:
				logger.debug('Group is not yet part of the user. Adding...')
				udm_obj['groups'].append(group_dn)
		return super(User, self).do_modify(udm_obj, lo)

	def _alter_udm_obj(self, udm_obj):
		if self.email is not None:
			udm_obj['e-mail'] = self.email
		udm_obj['departmentNumber'] = self.school
		ret = super(User, self)._alter_udm_obj(udm_obj)
		return ret

	def get_mail_domain(self):
		if self.email:
			domain_name = self.email.split('@')[-1]
			return MailDomain.cache(domain_name)

	def create_mail_domain(self, lo):
		mail_domain = self.get_mail_domain()
		if mail_domain is not None and not mail_domain.exists(lo):
			if self.shall_create_mail_domain():
				mail_domain.create(lo)
			else:
				logger.warning('Not allowed to create %r.' % mail_domain)

	def get_specific_groups(self, lo):
		groups = []
		for school_class in self.get_school_class_objs():
			groups.append(self.get_class_dn(school_class.name, lo))
		return groups

	def validate(self, lo, validate_unlikely_changes=False):
		super(User, self).validate(lo, validate_unlikely_changes)
		udm_obj = self.get_udm_object(lo)
		if udm_obj:
			original_class = self.get_class_for_udm_obj(udm_obj, self.school)
			if original_class is not self.__class__:
				self.add_error('name', _('It is not supported to change the role of a user. %(old_role)s %(name)s cannot become a %(new_role)s.') % {
					'old_role' : original_class.type_name,
					'name' : self.name,
					'new_role' : self.type_name
				})
		if self.email:
			name, email = escape_filter_chars(self.name), escape_filter_chars(self.email)
			if self.get_first_udm_obj(lo, '&(!(uid=%s))(mailPrimaryAddress=%s)' % (name, email)):
				self.add_error('email', _('The email address is already taken by another user. Please change the email address.'))
			# mail_domain = self.get_mail_domain(lo)
			# if not mail_domain.exists(lo) and not self.shall_create_mail_domain():
			# 	self.add_error('email', _('The mail domain is unknown. Please change the email address or create the mail domain "%s" using the Univention Directory Manager.') % mail_domain.name)

	def get_group_dn(self, group_name):
		return Group.cache(group_name, self.school).dn

	def get_class_dn(self, class_name, lo):
		# Bug #32337: check if the class exists without OU prefix
		# if it does not exist the class name with OU prefix is used
		school_class = SchoolClass.cache(class_name, self.school)
		if school_class.get_relative_name() == school_class.name:
			if not school_class.exists(lo):
				class_name = '%s-%s' % (self.school, class_name)
				school_class = SchoolClass.cache(class_name, self.school)
		return school_class.dn

	def primary_group_dn(self, lo):
		dn = self.get_group_dn('Domain Users %s' % self.school)
		return self.get_or_create_group_udm_object(dn, lo, self.school).dn

	def get_students_group_dn(self):
		prefix = ucr.get('ucsschool/ldap/default/groupprefix/pupils', 'schueler-')
		return self.get_group_dn('%s%s' % (prefix, self.school))

	def get_teachers_group_dn(self):
		prefix = ucr.get('ucsschool/ldap/default/groupprefix/teachers', 'lehrer-')
		return self.get_group_dn('%s%s' % (prefix, self.school))

	def get_staff_group_dn(self):
		prefix = ucr.get('ucsschool/ldap/default/groupprefix/staff', 'mitarbeiter-')
		return self.get_group_dn('%s%s' % (prefix, self.school))

	def groups_used(self, lo):
		group_dns = []
		group_dns.append(self.primary_group_dn(lo))
		group_dns.extend(self.get_specific_groups(lo))

		for group_dn in group_dns:
			self.get_or_create_group_udm_object(group_dn, lo, self.school)

		return group_dns

	@classmethod
	def get_or_create_group_udm_object(cls, group_dn, lo, school, fresh=False):
		name = cls.get_name_from_dn(group_dn)
		if Group.is_school_class(school, group_dn):
			group = SchoolClass.cache(name, school)
		else:
			group = Group.cache(name, school)
		if fresh:
			group._udm_obj_searched = False
		group.create(lo)
		return group

	def is_active(self):
		return self.disabled != 'all'

	def build_hook_line(self, hook_time, func_name):
		code = self._map_func_name_to_code(func_name)
		return self._build_hook_line(
				code,
				self.name,
				self.lastname,
				self.firstname,
				self.school,
				self.school_class,
				'', # TODO: rights?
				self.email,
				self.self_is_teacher(),
				self.is_active(),
				self.self_is_staff(),
				self.password,
			)

	def to_dict(self):
		ret = super(User, self).to_dict()
		display_name = []
		if self.firstname:
			display_name.append(self.firstname)
		if self.lastname:
			display_name.append(self.lastname)
		ret['display_name'] = ' '.join(display_name)
		school_classes = []
		for school_class in self.get_school_class_objs():
			school_classes.append(school_class.get_relative_name())
		if school_classes:
			ret['school_class'] = ', '.join(school_classes)
		ret['type_name'] = self.type_name
		ret['type'] = self.__class__.__name__
		ret['type'] = ret['type'][0].lower() + ret['type'][1:]
		return ret

	def get_school_class_objs(self):
		return []

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).users

	class Meta:
		udm_module = 'users/user'
		name_is_unique = True
		allow_school_change = False # code _should_ be able to handle it

class Student(User):
	school_class = SchoolClassStringAttribute(_('Class'), aka=['Class', 'Klasse'])

	type_name = _('Student')
	roles = [role_pupil]

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		obj = super(Student, cls).from_udm_obj(udm_obj, school, lo)
		if obj:
			school_class = None
			for group in udm_obj['groups']:
				if Group.is_school_class(school, group):
					school_class_name = cls.get_name_from_dn(group)
					school_class = school_class_name
					break
			obj.school_class = school_class
			return obj

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).students

	def get_specific_groups(self, lo):
		groups = super(Student, self).get_specific_groups(lo)
		groups.append(self.get_students_group_dn())
		return groups

	def get_school_class_objs(self):
		if self.school_class:
			return [SchoolClass.cache(self.school_class, self.school)]
		return []

class Teacher(User):
	school_class = SchoolClassStringAttribute(_('Class'), aka=['Class', 'Klasse'])

	type_name = _('Teacher')
	roles = [role_teacher]

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		obj = super(Teacher, cls).from_udm_obj(udm_obj, school, lo)
		if obj:
			school_class = None
			school_classes = []
			for group in udm_obj['groups']:
				if Group.is_school_class(school, group):
					school_class_name = cls.get_name_from_dn(group)
					school_class = school_class_name
					school_classes.append(school_class)
				school_class = ','.join(school_classes)
			obj.school_class = school_class
			return obj

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).teachers

	def get_specific_groups(self, lo):
		groups = super(Teacher, self).get_specific_groups(lo)
		groups.append(self.get_teachers_group_dn())
		return groups

	def get_school_class_objs(self):
		ret = []
		if self.school_class:
			for school_class in self.school_class.split(','):
				school_class = school_class.strip()
				ret.append(SchoolClass.cache(school_class, self.school))
		return ret

class Staff(User):
	type_name = _('Staff')
	roles = [role_staff]

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).staff

	def get_samba_home_path(self, lo):
		"""	Do not set sambaHomePath for staff users. """
		return None

	def get_samba_home_drive(self):
		"""	Do not set sambaHomeDrive for staff users. """
		return None

	def get_samba_netlogon_script_path(self):
		"""	Do not set sambaLogonScript for staff users. """
		return None

	def get_profile_path(self, lo):
		"""	Do not set sambaProfilePath for staff users. """
		return None

	def get_specific_groups(self, lo):
		groups = super(Staff, self).get_specific_groups(lo)
		groups.append(self.get_staff_group_dn())
		return groups

class TeachersAndStaff(Teacher):
	type_name = _('Teacher and Staff')
	roles = [role_teacher, role_staff]

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).teachersAndStaff

	def get_specific_groups(self, lo):
		groups = super(TeachersAndStaff, self).get_specific_groups(lo)
		groups.append(self.get_staff_group_dn())
		return groups

