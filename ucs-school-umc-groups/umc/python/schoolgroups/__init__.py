#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Administration of groups
#
# Copyright 2012-2015 Univention GmbH
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

from univention.lib.i18n import Translation

from univention.management.console.modules import UMC_OptionTypeError, UMC_CommandError
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import ListSanitizer, DictSanitizer, StringSanitizer
from univention.management.console.log import MODULE

import univention.admin.uexceptions as udm_exceptions

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule, Display, USER_READ, USER_WRITE, MACHINE_WRITE
from ucsschool.lib.models import User, Teacher, SchoolClass, WorkGroup

_ = Translation('ucs-school-umc-groups').translate


def only_workgroup_admin(func):
	def _decorated(self, request, *args, **kwargs):
		if request.flavor != 'workgroup-admin':
			raise UMC_CommandError('not supported')
		return func(self, request, *args, **kwargs)
	return _decorated


def get_group_class(request):
	if request.flavor in ('workgroup', 'workgroup-admin'):
		return WorkGroup
	elif request.flavor == 'teacher':
		return Teacher
	return SchoolClass


class Instance(SchoolBaseModule):

	@LDAP_Connection()
	def users(self, request, search_base=None, ldap_user_read=None, ldap_position=None):
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
		} for i in self._users(ldap_user_read, search_base, group=group, user_type=user_type, pattern=request.options.get('pattern'))]
		self.finished(request.id, result)

	@sanitize(
		pattern=StringSanitizer(default=''),
		school=StringSanitizer()
	)
	@LDAP_Connection()
	def query(self, request, search_base=None, ldap_user_read=None, ldap_position=None):
		klass = get_group_class(request)
		groups = klass.get_all(ldap_user_read, request.options['school'], filter_str=request.options['pattern'], easy_filter=True)
		self.finished(request.id, [group.to_dict() for group in groups])

	@sanitize(StringSanitizer(required=True))
	@LDAP_Connection()
	def get(self, request, search_base=None, ldap_user_read=None, ldap_position=None):
		klass = get_group_class(request)
		for group_dn in request.options:
			try:
				group = klass.from_dn(group_dn, None, ldap_user_read)
			except udm_exceptions.noObject:
				raise UMC_OptionTypeError('unknown object')

			school = group.school
			result = group.to_dict()
			
			if request.flavor == 'teacher':
				classes = SchoolClass.get_all(ldap_user_read, school, filter_str='uniqueMember=%s' % (group_dn,))
				result['classes'] = [{'id': class_.dn, 'label': class_.name} for class_ in classes]
				self.finished(request.id, [result])
				return

			if request.flavor == 'class':
				# members are teachers
				memberDNs = [usr for usr in result['users'] if User.is_teacher(school, usr)]
			elif request.flavor == 'workgroup-admin':
				memberDNs = result['users']
			else:
				memberDNs = [usr for usr in result['users'] if User.is_student(school, usr)]

			result.pop('users', None)

			# read members:
			members = []
			for member_dn in memberDNs:
				try:
					user = User.from_dn(member_dn, None, ldap_user_read)
				except udm_exceptions.noObject:
					MODULE.process('get(): skipped foreign OU user %r' % (member_dn,))
					continue
				members.append({'id': user.dn, 'label': Display.user(user.get_udm_object(ldap_user_read))})
			result['members'] = members

			self.finished(request.id, [result,])
			return

	@sanitize(DictSanitizer(dict(object=DictSanitizer({}, required=True))))
	@LDAP_Connection(USER_READ, MACHINE_WRITE)
	def put(self, request, search_base=None, ldap_machine_write=None, ldap_user_read=None, ldap_position=None):
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
			try:
				grp = klass.from_dn(group_dn, None, ldap_machine_write)
			except udm_exceptions.noObject:
				raise UMC_OptionTypeError('unknown group object')

			MODULE.info('Modifying group "%s" with members: %s' % (grp.dn, grp.users))
			MODULE.info('New members: %s' % group['members'])

			school = grp.school
			if request.flavor == 'class':
				# class -> update only the group's teachers (keep all non teachers)
				grp.users = [usr for usr in grp.users if not User.is_teacher(school, usr)] + [usr for usr in group['members'] if User.is_teacher(school, usr)]
			elif request.flavor == 'workgroup-admin':
				# workgroup (admin view) -> update teachers and students
				grp.users = group['members']
				grp.description = group['description']
				# do not allow groups to be renamed in order to avoid conflicts with shares
				# grp.name = '%(school)s-%(name)s' % group
			elif request.flavor == 'workgroup':
				# workgroup (teacher view) -> update only the group's students
				user_diff = set(group['members']) - set(grp.users)
				if any(User.is_teacher(school, dn) for dn in user_diff):
					raise UMC_CommandError('Adding teachers is not allowed')
				grp.users = [usr for usr in grp.users if not User.is_student(school, usr)] + [usr for usr in group['members'] if User.is_student(school, usr)]

			try:
				success = grp.modify(ldap_machine_write)
				MODULE.info('Modified, group has now members: %s' % (grp.users,))
			except udm_exceptions.base as exc:
				MODULE.process('An error occurred while modifying "%s": %s' % (group['$dn$'], exc.message))
				raise UMC_CommandError(_('Failed to modify group (%s).') % exc.message)

			self.finished(request.id, success)
			return

	@sanitize(DictSanitizer(dict(object=DictSanitizer({}, required=True))))
	@only_workgroup_admin
	@LDAP_Connection(USER_READ, USER_WRITE)
	def add(self, request, search_base=None, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		for group in request.options:
			group = group['object']
			try:
				grp = {}
				grp['school'] = group['school']
				grp['name'] = '%(school)s-%(name)s' % group
				grp['description'] = group['description']
				grp['users'] = group['members']

				grp = WorkGroup(**grp)

				success = grp.create(ldap_user_write)
			except udm_exceptions.base as exc:
				MODULE.process('An error occurred while creating the group "%s": %s' % (group['name'], exc.message))
				raise UMC_CommandError(_('Failed to create group (%s).') % exc.message)

			self.finished(request.id, success)
			return

	@sanitize(DictSanitizer(dict(object=ListSanitizer(min_elements=1))))
	@only_workgroup_admin
	@LDAP_Connection(USER_READ, USER_WRITE)
	def remove(self, request, search_base=None, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		"""Deletes a workgroup"""
		for group_dn in request.options:
			group_dn = group_dn['object'][0]

			group = WorkGroup.from_dn(group_dn, None, ldap_user_write)
			if not group.school:
				raise UMC_CommandError('Group must within the scope of a school OU: %s' % group_dn)

			try:
				success = group.remove(ldap_user_write)
			except udm_exceptions.base as exc:
				MODULE.error('Could not remove group "%s": %s' % (group.dn, exc))
				self.finished(request.id, [{'success': False, 'message': str(exc)}])
				return

			self.finished(request.id, [{'success': success}])
			return

	@sanitize(**{
		'$dn$': StringSanitizer(required=True),
		'classes': ListSanitizer(StringSanitizer(required=True), min_elements=1, required=True)
	})
	@LDAP_Connection(USER_READ, USER_WRITE)
	def add_teacher_to_classes(self, request, search_base=None, ldap_user_write=None, ldap_user_read=None, ldap_position=None):
		teacher = request.options['$dn$']
		classes = set(request.options['classes'])
		teacher = Teacher.from_dn(teacher, None, ldap_user_read)
		if not teacher.self_is_teacher():
			raise UMC_OptionTypeError('The user is not a teacher.')

		original_classes = set([dn for dn in ldap_user_read.searchDn('uniqueMember=%s' % (teacher.dn,)) if search_base.isClass(dn)])
		classes_to_remove = original_classes - classes
		classes_to_add = classes - original_classes

		failed = []
		for classdn in (classes_to_add | classes_to_remove):
			try:
				class_ = SchoolClass.from_dn(classdn, teacher.school, ldap_user_write)
			except udm_exceptions.noObject:
				failed.append(classdn)
				continue

			if classdn in classes_to_add and teacher.dn not in class_.users:
				class_.users.append(teacher.dn)
			elif classdn in classes_to_remove and teacher.dn in class_.users:
				class_.users.remove(teacher.dn)
			class_.users = list(class_.users)  # reference must change so that saving works
			try:
				if not class_.modify(ldap_user_write):
					failed.append(classdn)
			except udm_exceptions.base as exc:
				MODULE.error('Could not add teacher %s to class %s: %s' % (teacher.dn, classdn, exc))
				failed.append(classdn)
		self.finished(request.id, not any(failed))
