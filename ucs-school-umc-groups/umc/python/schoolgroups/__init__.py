#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Administration of groups
#
# Copyright 2012-2016 Univention GmbH
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

from ldap.filter import filter_format
from univention.lib.i18n import Translation

from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import ListSanitizer, DictSanitizer, StringSanitizer
from univention.management.console.log import MODULE

import univention.admin.uexceptions as udm_exceptions

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule, Display, USER_READ, USER_WRITE, MACHINE_WRITE
from ucsschool.lib.models import User, Teacher, TeachersAndStaff, SchoolClass, WorkGroup

_ = Translation('ucs-school-umc-groups').translate


def only_workgroup_admin(func):
	def _decorated(self, request, *args, **kwargs):
		if request.flavor != 'workgroup-admin':
			raise UMC_Error('not supported')
		return func(self, request, *args, **kwargs)
	return _decorated


def get_group_class(request):
	if request.flavor in ('workgroup', 'workgroup-admin'):
		return WorkGroup
	elif request.flavor == 'teacher':
		return Teacher
	return SchoolClass


class Instance(SchoolBaseModule):

	@sanitize(
		school=StringSanitizer(required=True),
		pattern=StringSanitizer(default=''),
	)
	@LDAP_Connection()
	def users(self, request, ldap_user_read=None, ldap_position=None):
		# parse group parameter
		group = request.options.get('group')
		user_type = None
		if not group or group == 'None':
			group = None
		elif group.lower() in ('teacher', 'student'):
			user_type = group.lower()
			group = None

		result = [{
			'id': i.dn,
			'label': Display.user(i)
		} for i in self._users(ldap_user_read, request.options['school'], group=group, user_type=user_type, pattern=request.options['pattern'])]
		self.finished(request.id, result)

	@sanitize(
		pattern=StringSanitizer(default=''),
		school=StringSanitizer()
	)
	@LDAP_Connection()
	def query(self, request, ldap_user_read=None, ldap_position=None):
		klasses = [get_group_class(request)]
		if klasses[0] is Teacher:
			klasses.append(TeachersAndStaff)
		groups = []
		for klass in klasses:
			groups.extend(klass.get_all(ldap_user_read, request.options['school'], filter_str=request.options['pattern'], easy_filter=True))
		self.finished(request.id, [group.to_dict() for group in groups])

	@sanitize(StringSanitizer(required=True))
	@LDAP_Connection()
	def get(self, request, ldap_user_read=None, ldap_position=None):
		klass = get_group_class(request)
		for group_dn in request.options:
			break
		try:
			group = klass.from_dn(group_dn, None, ldap_user_read)
		except udm_exceptions.noObject:
			raise UMC_Error('unknown object')

		school = group.school
		result = group.to_dict()

		if request.flavor == 'teacher':
			classes = SchoolClass.get_all(ldap_user_read, school, filter_str=filter_format('uniqueMember=%s', (group_dn,)))
			result['classes'] = [{'id': class_.dn, 'label': class_.get_relative_name()} for class_ in classes]
			self.finished(request.id, [result])
			return

		members = []
		for member_dn in result.pop('users', []):
			try:
				user = User.from_dn(member_dn, None, ldap_user_read)
			except udm_exceptions.noObject:
				MODULE.process('Could not open (foreign) user %r: no permissions/does not exists/not a user' % (member_dn,))
				members.append({'id': member_dn, 'label': member_dn})  # add entry so it doesn't get removed when modifying via 'workgroup-admin'
				continue
			if request.flavor == 'class' and not user.self_is_teacher():
				continue  # only display teachers
			elif request.flavor == 'workgroup' and not self.self_is_student():
				continue  # only display students
			members.append({'id': user.dn, 'label': Display.user(user.get_udm_object(ldap_user_read))})
		result['members'] = members

		self.finished(request.id, [result,])

	@sanitize(DictSanitizer(dict(object=DictSanitizer({}, required=True))))
	@LDAP_Connection(USER_READ, MACHINE_WRITE)
	def put(self, request, ldap_machine_write=None, ldap_user_read=None, ldap_position=None):
		"""Returns the objects for the given IDs

		requests.options = [ { object : ..., options : ... }, ... ]

		return: True|<error message>
		"""

		if request.flavor == 'teacher':
			request.options = request.options[0]['object']
			return self.add_teacher_to_classes(request)

		klass = get_group_class(request)
		for group in request.options:
			group = group['object']
			group_dn = group['$dn$']
			break

		try:
			grp = klass.from_dn(group_dn, None, ldap_machine_write)
		except udm_exceptions.noObject:
			raise UMC_Error('unknown group object')

		MODULE.info('Modifying group "%s" with members: %s' % (grp.dn, grp.users))
		MODULE.info('New members: %s' % group['members'])

		if request.flavor == 'workgroup-admin':
			# do not allow groups to be renamed in order to avoid conflicts with shares
			# grp.name = '%(school)s-%(name)s' % group
			grp.description = group['description']

		# Workgroup admin view → update teachers and students
		# Class view → update only the group's teachers (keep all non teachers)
		# Workgroup teacher view → update only the group's students
		# FIXME: teachers are allowed to add users from e.g. completly foreign schools to this group.
		# FIXME: restrict workgroup-admin to only be able to add students or teachers (users). forbid e.g. computer accounts

		users = []
		if request.flavor == 'workgroup-admin':
			users = group['members']
		else:
			# keep specific users from the group
			for userdn in grp.users:
				try:
					user = User.from_dn(userdn, None, ldap_machine_write)
				except udm_exceptions.noObject:  # no permissions/is not a user/does not exists → keep the old value
					users.append(userdn)
					continue
				if request.flavor == 'class' and not user.self_is_teacher():
					users.append(userdn)
				if request.flavor == 'workgroup' and not user.self_is_student():
					user.append(userdn)
			# add only certain users to the group
			for userdn in group['members']:
				try:
					user = User.from_dn(userdn, None, ldap_machine_write)
				except udm_exceptions.noObject as exc:
					MODULE.error('Not adding not existing user %r to group: %r.' % (userdn, exc))
					continue
				if request.flavor == 'class' and user.self_is_teacher():
					users.append(user.dn)
				elif request.flavor == 'workgroup' and user.self_is_student():
					users.append(user.dn)
				else:
					MODULE.error('Attempted to add illegal user %r into %r.' % (user.dn, grp.dn))

		grp.users = list(set(users))
		try:
			success = grp.modify(ldap_machine_write)
			MODULE.info('Modified, group has now members: %s' % (grp.users,))
		except udm_exceptions.base as exc:
			MODULE.process('An error occurred while modifying "%s": %s' % (group['$dn$'], exc.message))
			raise UMC_Error(_('Failed to modify group (%s).') % exc.message)

		self.finished(request.id, success)

	@sanitize(DictSanitizer(dict(object=DictSanitizer({}, required=True))))
	@only_workgroup_admin
	@LDAP_Connection(USER_READ, USER_WRITE)
	def add(self, request, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		for group in request.options:
			group = group['object']
			break
		try:
			grp = {}
			grp['school'] = group['school']
			grp['name'] = '%(school)s-%(name)s' % group
			grp['description'] = group['description']
			grp['users'] = group['members']

			grp = WorkGroup(**grp)

			success = grp.create(ldap_user_write)
			if not success and grp.exists(ldap_user_read):
				raise UMC_Error(_('The workgroup %r already exists!') % grp.name)
		except udm_exceptions.base as exc:
			MODULE.process('An error occurred while creating the group "%s": %s' % (group['name'], exc.message))
			raise UMC_Error(_('Failed to create group (%s).') % exc.message)

		self.finished(request.id, success)

	@sanitize(DictSanitizer(dict(object=ListSanitizer(min_elements=1))))
	@only_workgroup_admin
	@LDAP_Connection(USER_READ, USER_WRITE)
	def remove(self, request, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		"""Deletes a workgroup"""
		for group_dn in request.options:
			group_dn = group_dn['object'][0]
			break

		group = WorkGroup.from_dn(group_dn, None, ldap_user_write)
		if not group.school:
			raise UMC_Error('Group must within the scope of a school OU: %s' % group_dn)

		try:
			success = group.remove(ldap_user_write)
		except udm_exceptions.base as exc:
			MODULE.error('Could not remove group "%s": %s' % (group.dn, exc))
			self.finished(request.id, [{'success': False, 'message': str(exc)}])
			return

		self.finished(request.id, [{'success': success}])

	@sanitize(**{
		'$dn$': StringSanitizer(required=True),
		'classes': ListSanitizer(StringSanitizer(required=True), required=True),
		'school': StringSanitizer(required=True),
	})
	@LDAP_Connection(USER_READ, MACHINE_WRITE)
	def add_teacher_to_classes(self, request, ldap_machine_write=None, ldap_user_read=None, ldap_position=None):
		teacher = request.options['$dn$']
		classes = set(request.options['classes'])
		try:
			teacher = Teacher.from_dn(teacher, None, ldap_machine_write)
			if not teacher.self_is_teacher():
				raise udm_exceptions.noObject()
		except udm_exceptions.noObject:
			raise UMC_Error('The user is not a teacher.')

		original_classes = set([x.dn for x in SchoolClass.get_all(ldap_machine_write, request.options['school'], filter_format('uniqueMember=%s', (teacher.dn,)))])
		classes_to_remove = original_classes - classes
		classes_to_add = classes - original_classes

		failed = []
		for classdn in (classes_to_add | classes_to_remove):
			try:
				class_ = SchoolClass.from_dn(classdn, teacher.school, ldap_machine_write)
			except udm_exceptions.noObject:
				failed.append(classdn)
				continue

			if classdn in classes_to_add and teacher.dn not in class_.users:
				class_.users.append(teacher.dn)
			elif classdn in classes_to_remove and teacher.dn in class_.users:
				class_.users.remove(teacher.dn)
			try:
				if not class_.modify(ldap_machine_write):
					failed.append(classdn)
			except udm_exceptions.base as exc:
				MODULE.error('Could not add teacher %s to class %s: %s' % (teacher.dn, classdn, exc))
				failed.append(classdn)
		self.finished(request.id, not any(failed))
