#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#  Wizards
#
# Copyright 2012-2019 Univention GmbH
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

import re
import functools

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.base import UMC_Error
from univention.management.console.modules.decorators import simple_response, sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, DictSanitizer, DNSanitizer, ChoicesSanitizer
from univention.admin.uexceptions import base as uldapBaseException, noObject
import univention.admin.modules as udm_modules

from ucsschool.lib.school_umc_base import SchoolBaseModule, LDAP_Connection, USER_READ, USER_WRITE, ADMIN_WRITE, SchoolSanitizer
from ucsschool.lib.models import SchoolClass, School, User, Student, Teacher, Staff, TeachersAndStaff, SchoolComputer, WindowsComputer, MacComputer, IPComputer, UCCComputer
from ucsschool.lib.models.utils import add_module_logger_to_schoollib

from univention.management.console.modules.schoolwizards.SchoolImport import SchoolImport

_ = Translation('ucs-school-umc-wizards').translate


# TODO: remove once this is implemented in uexceptions, see Bug #30088
def get_exception_msg(e):
	msg = getattr(e, 'message', '')
	if getattr(e, 'args', False):
		if e.args[0] != msg or len(e.args) != 1:
			for arg in e.args:
				msg += ' ' + arg
	return msg


USER_TYPES = {
	'student': Student,
	'teacher': Teacher,
	'staff': Staff,
	'teachersAndStaff': TeachersAndStaff,
}


COMPUTER_TYPES = {
	'windows': WindowsComputer,
	'macos': MacComputer,
	'ucc': UCCComputer,
	'ipmanagedclient': IPComputer,
}


def iter_objects_in_request(request, lo, require_dn=False):
	klass = {
		'schoolwizards/schools': School,
		'schoolwizards/users': User,
		'schoolwizards/computers': SchoolComputer,
		'schoolwizards/classes': SchoolClass,
	}[request.flavor]
	for obj_props in request.options:
		obj_props = obj_props['object']
		for key, value in obj_props.iteritems():
			if isinstance(value, basestring):
				obj_props[key] = value.strip()
		if issubclass(klass, User):
			klass = USER_TYPES.get(obj_props.get('type'), User)
		elif issubclass(klass, SchoolComputer):
			klass = COMPUTER_TYPES.get(obj_props.get('type'), SchoolComputer)
		dn = obj_props.get('$dn$')
		if 'name' not in obj_props:
			# important for get_school in district_mode!
			obj_props['name'] = klass.get_name_from_dn(dn)
		if issubclass(klass, SchoolClass):
			# workaround to be able to reuse this function everywhere
			obj_props['name'] = '%s-%s' % (obj_props['school'], obj_props['name'])
		if require_dn:
			try:
				obj = klass.from_dn(dn, obj_props.get('school'), lo)
			except noObject:
				raise UMC_Error(_('The %s %r does not exists or might have been removed in the meanwhile.') % (getattr(klass, 'type_name', klass.__name__), obj_props['name']))
			for key, value in obj_props.iteritems():
				if key in obj._attributes:
					setattr(obj, key, value)
		else:
			obj = klass(**obj_props)
		if dn:
			obj.old_dn = dn
		yield obj


def response(func):
	@functools.wraps(func)
	def _decorated(self, request, *a, **kw):
		ret = func(self, request, *a, **kw)
		self.finished(request.id, ret)
	return _decorated


def sanitize_object(**kwargs):
	def _decorator(func):
		return sanitize(DictSanitizer(dict(object=DictSanitizer(kwargs))))(func)
	return _decorator


class Instance(SchoolBaseModule, SchoolImport):

	def init(self):
		super(Instance, self).init()
		add_module_logger_to_schoollib()

	@simple_response
	def is_singlemaster(self):
		return ucr.is_true('ucsschool/singlemaster', False)

	@sanitize(
		schooldc=StringSanitizer(required=True, regex_pattern=re.compile(r'^[a-zA-Z](([a-zA-Z0-9-_]*)([a-zA-Z0-9]$))?$')),
		admindc=StringSanitizer(required=False, regex_pattern=re.compile(r'^[a-zA-Z](([a-zA-Z0-9-_]*)([a-zA-Z0-9]$))?$')),
		schoolou=StringSanitizer(required=True, regex_pattern=re.compile(r'^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$')),
	)
	@simple_response
	def move_dc(self, schooldc, schoolou):
		params = ['--dcname', schooldc, '--ou', schoolou]
		return_code, stdout = self._run_script(SchoolImport.MOVE_DC_SCRIPT, params, True)
		return {'success': return_code == 0, 'message': stdout}

	@simple_response
	def computer_types(self):
		ret = []
		computer_types = [WindowsComputer, MacComputer, IPComputer]
		try:
			import univention.admin.handlers.computers.ucc as ucc
			del ucc
		except ImportError:
			pass
		else:
			computer_types.insert(1, UCCComputer)
		for computer_type in computer_types:
			ret.append({'id': computer_type._meta.udm_module_short, 'label': computer_type.type_name})
		return ret

	@response
	@LDAP_Connection()
	def share_servers(self, request, ldap_user_read=None):
		# udm/syntax/choices UCSSchool_Server_DN
		ret = [{'id': '', 'label': ''}]
		for module in ['computers/domaincontroller_master', 'computers/domaincontroller_backup', 'computers/domaincontroller_slave', 'computers/memberserver']:
			for obj in udm_modules.lookup(module, None, ldap_user_read, scope='sub'):
				obj.open()
				ret.append({'id': obj.dn, 'label': obj.info.get('fqdn', obj.info['name'])})
		return ret

	@sanitize_object(**{
		'$dn$': DNSanitizer(required=True),
	})
	@response
	@LDAP_Connection()
	def _get_obj(self, request, ldap_user_read=None):
		ret = []
		for obj in iter_objects_in_request(request, ldap_user_read, True):
			MODULE.process('Getting %r' % (obj))
			obj = obj.from_dn(obj.old_dn, obj.school, ldap_user_read)
			ret.append(obj.to_dict())
		return ret

	@response
	@LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
	def _create_obj(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
		# Bug #44641: workaround with security implications!
		if ucr.is_true('ucsschool/wizards/schoolwizards/workaround/admin-connection'):
			ldap_user_write = ldap_admin_write

		ret = []
		for obj in iter_objects_in_request(request, ldap_user_write):
			MODULE.process('Creating %r' % (obj,))
			obj.validate(ldap_user_read)
			if obj.errors:
				ret.append({'result': {'message': obj.get_error_msg()}})
				MODULE.process('Validation failed %r' % (ret[-1],))
				continue
			try:
				if obj.create(ldap_user_write, validate=False):
					ret.append(True)
				else:
					ret.append({'result': {'message': _('"%s" already exists!') % obj.name}})
			except uldapBaseException as exc:
				ret.append({'result': {'message': get_exception_msg(exc)}})
				MODULE.process('Creation failed %r' % (ret[-1],))
		return ret

	@sanitize_object(**{
		'$dn$': DNSanitizer(required=True),
	})
	@response
	@LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
	def _modify_obj(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
		# Bug #44641: workaround with security implications!
		if ucr.is_true('ucsschool/wizards/schoolwizards/workaround/admin-connection'):
			ldap_user_write = ldap_admin_write

		ret = []
		for obj in iter_objects_in_request(request, ldap_user_write, True):
			MODULE.process('Modifying %r' % (obj))
			obj.validate(ldap_user_read)
			if obj.errors:
				ret.append({'result': {'message': obj.get_error_msg()}})
				continue
			try:
				obj.modify(ldap_user_write, validate=False)
			except uldapBaseException as exc:
				ret.append({'result': {'message': get_exception_msg(exc)}})
			else:
				ret.append(True)  # no changes? who cares?
		return ret

	@sanitize_object(**{
		'$dn$': DNSanitizer(required=True),
	})
	@response
	@LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
	def _delete_obj(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
		# Bug #44641: workaround with security implications!
		if ucr.is_true('ucsschool/wizards/schoolwizards/workaround/admin-connection'):
			ldap_user_write = ldap_admin_write

		ret = []
		for obj in iter_objects_in_request(request, ldap_user_write, True):
			obj.name = obj.get_name_from_dn(obj.old_dn)
			MODULE.process('Deleting %r' % (obj))
			if obj.remove(ldap_user_write):
				ret.append(True)
			else:
				ret.append({'result': {'message': _('"%s" does not exist!') % obj.name}})
		return ret

	def _get_all(self, klass, school, filter_str, lo):
		if school:
			schools = [School.cache(school)]
		else:
			schools = School.from_binddn(lo)
		objs = []
		for school in schools:
			try:
				objs.extend(klass.get_all(lo, school.name, filter_str=filter_str, easy_filter=True))
			except noObject as exc:
				MODULE.error('Could not get all objects of %r: %r' % (klass.__name__, exc))
		return [obj.to_dict() for obj in objs]

	@sanitize(
		school=StringSanitizer(required=True),
		type=ChoicesSanitizer(['all'] + USER_TYPES.keys(), required=True),
		filter=StringSanitizer(default=''),
	)
	@response
	@LDAP_Connection()
	def get_users(self, request, ldap_user_read=None):
		school = request.options['school']
		user_class = USER_TYPES.get(request.options['type'], User)
		return self._get_all(user_class, school, request.options.get('filter'), ldap_user_read)

	get_user = _get_obj
	modify_user = _modify_obj
	create_user = _create_obj

	@sanitize_object(**{
		'remove_from_school': SchoolSanitizer(required=True),
		'$dn$': DNSanitizer(required=True),
	})
	@response
	@LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
	def delete_user(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
		# Bug #44641: workaround with security implications!
		if ucr.is_true('ucsschool/wizards/schoolwizards/workaround/admin-connection'):
			ldap_user_write = ldap_admin_write

		ret = []
		for obj_props in request.options:
			obj_props = obj_props['object']
			try:
				obj = User.from_dn(obj_props['$dn$'], None, ldap_user_write)
			except noObject:
				raise UMC_Error(_('The %s %r does not exists or might have been removed in the meanwhile.') % (getattr(User, 'type_name', None) or User.__name__, User.get_name_from_dn(obj_props['$dn$'])))
			school = obj_props['remove_from_school']
			success = obj.remove_from_school(school, ldap_user_write)
			# obj.old_dn is None when the ucsschool lib has deleted the user after the last school was removed from it
			if success and obj.old_dn is not None:
				success = obj.modify(ldap_user_write)
			if not success:
				success = {'result': {'message': _('Failed to remove user from school.')}}
			ret.append(success)
		return ret

	@sanitize(
		school=StringSanitizer(required=True),
		type=ChoicesSanitizer(['all'] + COMPUTER_TYPES.keys(), required=True),
		filter=StringSanitizer(default=''),
	)
	@response
	@LDAP_Connection()
	def get_computers(self, request, ldap_user_read=None):
		school = request.options['school']
		computer_class = COMPUTER_TYPES.get(request.options['type'], SchoolComputer)
		return self._get_all(computer_class, school, request.options.get('filter'), ldap_user_read)

	get_computer = _get_obj
	modify_computer = _modify_obj
	@response
	@LDAP_Connection(USER_READ, USER_WRITE, ADMIN_WRITE)
	def create_computer(self, request, ldap_user_read=None, ldap_user_write=None, ldap_admin_write=None):
		# Bug #44641: workaround with security implications!
		if ucr.is_true('ucsschool/wizards/schoolwizards/workaround/admin-connection'):
			ldap_user_write = ldap_admin_write

		for option in request.options:
			MODULE.process(option)
		ignore_warnings = [option.get('object', {}).get('ignore_warning', False) for option in request.options]
		ignore_warnings.reverse()
		ret = {}
		for obj in iter_objects_in_request(request, ldap_user_write):
			ignore_warning = ignore_warnings.pop()
			obj.validate(ldap_user_read)
			if obj.errors:
				ret['error'] = obj.get_error_msg()
				MODULE.process('Validation error: {}'.format(ret['error']))
				continue
			elif obj.warnings and not ignore_warning:
				ret['warning'] = obj.get_warning_msg()
				MODULE.process('Validation warning: {}'.format(ret['warning']))
				continue
			try:
				if obj.create(ldap_user_write, validate=False):
					ret = True
				else:
					ret['error'] = _('"%s" already exists!') % obj.name
			except uldapBaseException as exc:
				ret['error'] = get_exception_msg(exc)
				MODULE.process('Creation failed {}'.format(ret['error']))
		return [{'result': ret}]
	delete_computer = _delete_obj

	@sanitize(
		school=StringSanitizer(required=True),
		filter=StringSanitizer(default=''),
	)
	@response
	@LDAP_Connection()
	def get_classes(self, request, ldap_user_read=None):
		school = request.options['school']
		return self._get_all(SchoolClass, school, request.options.get('filter'), ldap_user_read)

	get_class = _get_obj
	modify_class = _modify_obj
	create_class = _create_obj
	delete_class = _delete_obj

	@response
	@LDAP_Connection()
	def get_schools(self, request, ldap_user_read=None):
		schools = School.get_all(ldap_user_read, filter_str=request.options.get('filter'), easy_filter=True)
		return [school.to_dict() for school in schools]

	get_school = _get_obj
	modify_school = _modify_obj
	create_school = _create_obj
	delete_school = _delete_obj
