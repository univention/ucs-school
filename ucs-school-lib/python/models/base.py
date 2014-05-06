#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014 Univention GmbH
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
from copy import deepcopy
import tempfile
import subprocess

from ldap import explode_dn
from ldap.filter import escape_filter_chars

import univention.admin.uldap as udm_uldap
from univention.admin.uexceptions import noObject
import univention.admin.modules as udm_modules
from univention.admin.filter import conjunction, expression
from univention.management.console.modules.sanitizers import LDAPSearchSanitizer

from ucsschool.lib.schoolldap import SchoolSearchBase
from ucsschool.lib.models.meta import UCSSchoolHelperMetaClass
from ucsschool.lib.models.attributes import CommonName, SchoolAttribute, ValidationError
from ucsschool.lib.models.utils import ucr, _, logger

HOOK_SEP_CHAR = '\t'
HOOK_PATH = '/usr/share/ucs-school-import/hooks/'

class UCSSchoolHelperAbstractClass(object):
	__metaclass__ = UCSSchoolHelperMetaClass
	_cache = {}

	_search_base_cache = {}
	_initialized_udm_modules = []

	name = CommonName(_('Name'), aka=['Name'])
	school = SchoolAttribute(_('School'), aka=['School'])

	@classmethod
	def get(cls, *args, **kwargs):
		args = list(args)
		if args:
			kwargs['name'] = args.pop(0)
		if args:
			kwargs['school'] = args.pop(0)
		key = [cls.__name__] + [(k, kwargs[k]) for k in sorted(kwargs)]
		key = tuple(key)
		if key not in cls._cache:
			logger.debug('Initializing %r' % (key,))
			obj = cls(**kwargs)
			cls._cache[key] = obj
		return cls._cache[key]

	@classmethod
	def supports_school(cls):
		return 'school' in cls._attributes

	def __init__(self, **kwargs):
		self._udm_obj_searched = False
		self._udm_obj = None
		for key in self._attributes:
			setattr(self, key, kwargs.get(key))
		self.custom_dn = None
		self.old_dn = self.dn
		self.errors = {}
		self.warnings = {}

	@property
	def dn(self):
		if self.custom_dn:
			return self.custom_dn
		container = self.get_own_container()
		if self.name and container:
			name = self._meta.ldap_map_function(self.name)
			return '%s=%s,%s' % (self._meta.ldap_name_part, name, container)

	def set_dn(self, dn):
		self.custom_dn = None
		self.old_dn = dn

	def validate(self, lo, validate_unlikely_changes=False):
		from ucsschool.lib.models.school import School
		self.errors.clear()
		self.warnings.clear()
		for name, attr in self._attributes.iteritems():
			value = getattr(self, name)
			try:
				attr.validate(value)
			except ValueError as e:
				self.add_error(name, str(e))
		if self._meta.name_is_unique and not self._meta.allow_school_change:
			if self.exists_outside_school(lo):
				self.add_error('name', _('The name is already used somewhere outside the school. It may not be taken twice and has to be changed.'))
		if self.supports_school() and self.school:
			if not School.get(self.school).exists(lo):
				self.add_error('school', _('The school "%s" does not exist. Please choose an existing one or create it.') % self.school)
		if validate_unlikely_changes:
			if self.exists(lo):
				udm_obj = self.get_udm_object(lo)
				original_self = self.from_udm_obj(udm_obj, self.school, lo)
				if original_self:
					for name, attr in self._attributes.iteritems():
						if attr.unlikely_to_change:
							new_value = getattr(self, name)
							old_value = getattr(original_self, name)
							if new_value and old_value:
								if new_value != old_value:
									self.add_warning(name, _('The value changed from %(old)s. This seems unlikely.') % {'old' : old_value})

	def add_warning(self, attribute, warning_message):
		warnings = self.warnings.setdefault(attribute, [])
		if warning_message not in warnings:
			warnings.append(warning_message)

	def add_error(self, attribute, error_message):
		errors = self.errors.setdefault(attribute, [])
		if error_message not in errors:
			errors.append(error_message)

	def exists(self, lo):
		return self.get_udm_object(lo) is not None

	def exists_outside_school(self, lo):
		udm_obj = self.get_udm_object(lo)
		if udm_obj is None:
			return False
		return ('ou=%s,' % self.school) not in udm_obj.dn

	def call_hooks(self, hook_time, func_name):
		# verify path
		hook_path = self._meta.hook_path
		path = os.path.join(HOOK_PATH, '%s_%s_%s.d' % (hook_path, func_name, hook_time))
		logger.debug('%s shall be executed' % path)
		if not os.path.isdir(path) or not os.listdir(path):
			logger.debug('%s not found or empty' % path)
			return None

		dn = None
		if hook_time == 'post':
			dn = self.old_dn

		logger.debug('Building hook line: %r.build_hook_line(%r, %r)' % (self, hook_time, func_name))
		line = self.build_hook_line(hook_time, func_name)
		if not line:
			logger.debug('No line. Skipping!')
			return None
		else:
			# TODO: remove! contains password
			logger.debug('Line: %r' % line)
		line = line.strip() + '\n'

		# create temporary file with data
		with tempfile.NamedTemporaryFile() as tmpfile:
			tmpfile.write(line)
			tmpfile.flush()

			# invoke hook scripts
			# <script> <temporary file> [<ldap dn>]
			command = ['run-parts', path, '--arg', tmpfile.name]
			if dn:
				command.extend(('--arg', dn))

			ret_code = subprocess.call(command)

			return ret_code == 0

	def build_hook_line(self, hook_time, func_name):
		return None

	def _alter_udm_obj(self, udm_obj):
		for name, attr in self._attributes.iteritems():
			if attr.udm_name:
				value = getattr(self, name)
				if value is not None:
					udm_obj[attr.udm_name] = value

	def create(self, lo, validate=True):
		self.call_hooks('pre', 'create')
		success = self.create_without_hooks(lo, validate)
		if success:
			self.call_hooks('post', 'create')
		return success

	def create_without_hooks(self, lo, validate):
		logger.info('Creating %r' % self)

		if self.exists(lo):
			logger.info('%s already exists!' % self.dn)
			return False

		if validate:
			self.validate(lo)
			if self.errors:
				raise ValidationError(self.errors.copy())

		pos = udm_uldap.position(ucr.get('ldap/base'))
		pos.setDn(self.get_own_container())
		udm_obj = udm_modules.get(self._meta.udm_module).object(None, lo, pos, superordinate=self.get_superordinate())
		udm_obj.open()

		# here is the real logic
		self.do_create(udm_obj, lo)

		# get it fresh from the database (needed for udm_obj._exists ...)
		self._udm_obj_searched = False
		self.set_dn(self.dn)
		logger.info('%r successfully created' % self)
		return True

	def do_create(self, udm_obj, lo):
		self._alter_udm_obj(udm_obj)
		udm_obj.create()

	def modify(self, lo, validate=True):
		self.call_hooks('pre', 'modify')
		success = self.modify_without_hooks(lo, validate)
		if success:
			self.call_hooks('post', 'modify')
		return success

	def modify_without_hooks(self, lo, validate):
		logger.info('Modifying %r' % self)

		if validate:
			self.validate(lo, validate_unlikely_changes=True)
			if self.errors:
				raise ValidationError(self.errors.copy())

		udm_obj = self.get_udm_object(lo)
		if not udm_obj:
			logger.info('%s does not exist!' % self.old_dn)
			return False

		old_attrs = deepcopy(udm_obj.info)
		self.do_modify(udm_obj, lo)
		# get it fresh from the database
		self._udm_obj_searched = False
		self.set_dn(self.dn)
		udm_obj = self.get_udm_object(lo)
		same = old_attrs == udm_obj.info
		if udm_obj.dn != self.dn:
			udm_obj.move(self.dn)
			same = False
		if same:
			logger.info('%r not modified. Nothing changed' % self)
		else:
			logger.info('%r successfully modified' % self)
		# return not same
		return True

	def do_modify(self, udm_obj, lo):
		self._alter_udm_obj(udm_obj)
		udm_obj.modify()

	def remove(self, lo):
		self.call_hooks('pre', 'remove')
		success = self.remove_without_hooks(lo)
		if success:
			self.call_hooks('post', 'remove')
		return success

	def remove_without_hooks(self, lo):
		logger.info('Deleting %r' % self)
		udm_obj = self.get_udm_object(lo)
		if udm_obj:
			udm_obj.remove(remove_childs=True)
			self._udm_obj_searched = False
			self.set_dn(None)
			logger.info('%r successfully removed' % self)
			return True
		logger.info('%r does not exist!' % self)
		return False

	@classmethod
	def get_name_from_dn(cls, dn):
		if dn:
			return explode_dn(dn, 1)[0]

	@classmethod
	def find_field_label_from_name(cls, field):
		for name, attr in cls._attributes.items():
			if name == field:
				return attr.label

	def get_error_msg(self):
		error_msg = ''
		for key, errors in self.errors.iteritems():
			label = self.find_field_label_from_name(key)
			error_str = ''
			for error in errors:
				error_str += error
				if not (error.endswith('!') or error.endswith('.')):
					error_str += '.'
				error_str += ' '
			error_msg += '%s: %s' % (label, error_str)
		return error_msg[:-1]

	def get_udm_object(self, lo):
		if self._udm_obj_searched is False:
			dn = self.old_dn or self.dn
			if dn is None:
				logger.debug('Getting UDM object: No DN!')
				return
			if self._meta.name_is_unique:
				if self.name is None:
					return None
				udm_name = self._attributes['name'].udm_name
				name = self.get_name_from_dn(dn)
				filter_str = '%s=%s' % (udm_name, escape_filter_chars(name))
				logger.debug('Getting UDM object by filter: %s' % filter_str)
				self._udm_obj = self.get_first_udm_obj(lo, filter_str)
			else:
				try:
					logger.debug('Getting UDM object by dn: %s' % dn)
					self._udm_obj = udm_modules.lookup(self._meta.udm_module, None, lo, scope='base', base=dn)[0]
				except (noObject, IndexError):
					self._udm_obj = None
			if self._udm_obj:
				self._udm_obj.open()
			self._udm_obj_searched = True
		return self._udm_obj

	def get_superordinate(self):
		return None

	def get_own_container(self):
		if self.supports_school() and not self.school:
			return None
		return self.get_container(self.school)

	@classmethod
	def get_container(cls, school):
		raise NotImplementedError()

	@classmethod
	def get_search_base(cls, school_name):
		from ucsschool.lib.models.school import School
		if school_name not in cls._search_base_cache:
			school = School(name=school_name)
			cls._search_base_cache[school_name] = SchoolSearchBase([school.name], dn=school.dn)
		return cls._search_base_cache[school_name]

	@classmethod
	def init_udm_module(cls, lo):
		if cls._meta.udm_module in cls._initialized_udm_modules:
			return
		pos = udm_uldap.position(lo.base)
		udm_modules.init(lo, pos, udm_modules.get(cls._meta.udm_module))
		cls._initialized_udm_modules.append(cls._meta.udm_module)

	@classmethod
	def get_all(cls, lo, school, filter_str=None):
		cls.init_udm_module(lo)
		complete_filter = cls._meta.udm_filter
		filter_from_filter_str = cls.build_filter(filter_str)
		if filter_from_filter_str:
			if complete_filter:
				complete_filter = conjunction('&', [complete_filter, filter_from_filter_str])
			else:
				complete_filter = filter_from_filter_str
		complete_filter = str(complete_filter)
		logger.info('Getting all %s of %s with filter %r' % (cls.__name__, school, complete_filter))
		try:
			udm_objs = udm_modules.lookup(cls._meta.udm_module, None, lo, filter=complete_filter, base=cls.get_container(school), scope='sub')
		except noObject:
			logger.warning('Error while getting all %s of %s: %s does not exist!' % (cls.__name__, school, cls.get_container(school)))
			return []
		ret = []
		for udm_obj in udm_objs:
			udm_obj.open()
			obj = cls.from_udm_obj(udm_obj, school, lo)
			if obj:
				ret.append(obj)
		return ret

	@classmethod
	def build_filter(cls, filter_str):
		if filter_str:
			sanitizer = LDAPSearchSanitizer()
			filter_str = sanitizer.sanitize('filter_str', {'filter_str' : filter_str})
			expressions = []
			module = udm_modules.get(cls._meta.udm_module)
			for key, prop in module.property_descriptions.iteritems():
				if prop.include_in_default_search:
					expressions.append(expression(key, filter_str))
			if expressions:
				return conjunction('|', expressions)

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		cls.init_udm_module(lo)
		klass = cls.get_class_for_udm_obj(udm_obj, school)
		if klass is None:
			logger.warning('UDM object %s does not correspond to a class in UCS school lib!' % udm_obj.dn)
			return None
		if klass is not cls:
			logger.info('UDM object %s is not %s, but actually %s' % (udm_obj.dn, cls.__name__, klass.__name__))
			return klass.from_udm_obj(udm_obj, school, lo)
		attrs = {'school' : school}
		for name, attr in cls._attributes.iteritems():
			if attr.udm_name:
				attrs[name] = udm_obj[attr.udm_name]
		return cls(**attrs)

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		return cls

	def __repr__(self):
		if self.supports_school():
			return '%s(name=%r, school=%r, dn=%r)' % (self.__class__.__name__, self.name, self.school, self.custom_dn or self.old_dn)
		else:
			return '%s(name=%r, dn=%r)' % (self.__class__.__name__, self.name, self.custom_dn or self.old_dn)

	def __lt__(self, other):
		return self.name < other.name

	@classmethod
	def from_dn(cls, dn, school, lo):
		cls.init_udm_module(lo)
		try:
			udm_obj = udm_modules.lookup(cls._meta.udm_module, None, lo, filter=cls._meta.udm_filter, base=dn, scope='base')[0]
		except IndexError:
			# happens when cls._meta.udm_module does not "match" the dn
			raise noObject('Wrong objectClass')
		udm_obj.open()
		obj = cls.from_udm_obj(udm_obj, school, lo)
		if obj:
			obj.custom_dn = dn
			return obj

	@classmethod
	def get_first_udm_obj(cls, lo, filter_str):
		cls.init_udm_module(lo)
		if cls._meta.udm_filter:
			filter_str = '(&(%s)(%s))' % (cls._meta.udm_filter, filter_str)
		try:
			obj = udm_modules.lookup(cls._meta.udm_module, None, lo, scope='sub', base=ucr.get('ldap/base'), filter=str(filter_str))[0]
		except IndexError:
			return None
		else:
			obj.open()
			return obj

	def to_dict(self):
		ret = {'$dn$' : self.dn, 'objectType' : self._meta.udm_module}
		for name, attr in self._attributes.iteritems():
			if not attr.internal:
				ret[name] = getattr(self, name)
		return ret

	def _map_func_name_to_code(cls, func_name):
		if func_name == 'create':
			return 'A'
		elif func_name == 'modify':
			return 'M'
		elif func_name == 'remove':
			return 'D'

	def _build_hook_line(self, *args):
		attrs = []
		for arg in args:
			val = arg
			if arg is None:
				val = ''
			if arg is False:
				val = 0
			if arg is True:
				val = 1
			attrs.append(str(val))
		return HOOK_SEP_CHAR.join(attrs)

