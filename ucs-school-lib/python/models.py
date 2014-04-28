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
from ldap.filter import escape_filter_chars
from ldap.dn import escape_dn_chars, str2dn
import random
import string
import ldap
from copy import deepcopy
import tempfile
import subprocess
import re
import ipaddr

import univention.admin.uldap as udm_uldap
from univention.admin.uexceptions import noObject, valueError, objectExists
from univention.admin.syntax import gid, string_numbers_letters_dots_spaces, uid_umlauts, iso8601Date, primaryEmailAddressValidDomain, boolean, UCSSchool_Server_DN, GroupDN, ipAddress, MAC_Address
from univention.config_registry import ConfigRegistry, handler_set
import univention.admin.modules as udm_modules
import univention.admin.objects as udm_objects

from univention.management.console.log import MODULE
from univention.lib.i18n import Translation

from ucsschool.lib.schoolldap import SchoolSearchBase

_ = Translation('python-ucs-school').translate

udm_modules.update()

ucr = ConfigRegistry()
ucr.load()

SEP_CHAR = '\t'
HOOK_PATH = '/usr/share/ucs-school-import/hooks/'
def call_hooks(obj, hook_time, func_name):
	# verify path
	module = obj._meta.udm_module_short
	path = os.path.join(HOOK_PATH, '%s_%s_%s.d' % (module, func_name, hook_time))
	if not os.path.isdir(path) or not os.listdir(path):
		return False

	dn = None
	if hook_time == 'post':
		dn = obj.old_dn

	line = obj.build_hook_line(hook_time, func_name)
	if not line:
		return None
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

# TODO: activate
def hook(func):
	func_name = func.__name__
	def _func(*args, **kwargs):
		self_obj = args[0]

		call_hooks(self_obj, 'pre', func_name)
		ret = func(*args, **kwargs)
		if ret:
			call_hooks(self_obj, 'post', func_name)
		return ret
	return _func

def generate_random(length=30):
	chars = string.ascii_letters + string.digits
	return ''.join(random.choice(chars) for x in range(length))

def flatten(list_of_lists):
	# return [item for sublist in list_of_lists for item in sublist]
	# => does not work well for strings in list
	ret = []
	for sublist in list_of_lists:
		if isinstance(sublist, (list, tuple)):
			ret.extend(flatten(sublist))
		else:
			ret.append(sublist)
	return ret

class ValidationError(Exception):
	pass

class Attribute(object):
	udm_name = None
	syntax = None
	extended = False

	def __init__(self, label, aka=None, udm_name=None, required=False, unlikely_to_change=False, internal=False):
		self.label = label
		self.aka = aka or [] # also_known_as
		self.required = required
		self.unlikely_to_change = unlikely_to_change
		self.internal = internal
		self.udm_name = udm_name or self.udm_name

	def validate(self, value):
		if self.required and not value:
			raise ValueError(_('"%s" is required. Please provide this information.') % self.label)
		if self.syntax and value:
			try:
				self.syntax.parse(value)
			except valueError as e:
				raise ValueError(str(e))

class CommonName(Attribute):
	udm_name = 'name'
	syntax = None

	def __init__(self, label, aka=None):
		super(CommonName, self).__init__(label, aka=aka, required=True)

	def validate(self, value):
		super(CommonName, self).validate(value)
		escaped = escape_dn_chars(value)
		if value != escaped:
			raise ValueError(_('May not contain special characters'))

class UserName(CommonName):
	udm_name = 'username'
	syntax = uid_umlauts

class DHCPServiceName(CommonName):
	udm_name = 'service'

class GroupName(CommonName):
	syntax = gid

class ShareName(CommonName):
	syntax = string_numbers_letters_dots_spaces

class SchoolName(CommonName):
	udm_name = 'name'

	def validate(self, value):
		super(CommonName, self).validate(value)
		if ucr.is_true('ucsschool/singlemaster', False):
			regex = re.compile('^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$')
			if not regex.match(value):
				raise ValueError(_('Invalid school name'))

class DCName(Attribute):
	def validate(self, value):
		super(DCName, self).validate(value)
		if ucr.is_true('ucsschool/singlemaster', False):
			if len(value) > 12:
				raise ValueError(_("A valid NetBIOS hostname can not be longer than 12 characters."))
			if sum([len(value), 1, len(ucr.get('domainname', ''))]) > 63:
				raise ValueError(_("The length of fully qualified domain name is greater than 63 characters."))

class Firstname(Attribute):
	udm_name = 'firstname'

class Lastname(Attribute):
	udm_name = 'lastname'

class Birthday(Attribute):
	udm_name = 'birthday'
	syntax = iso8601Date

class Email(Attribute):
	udm_name = 'mailPrimaryAddress'
	syntax = primaryEmailAddressValidDomain

class Password(Attribute):
	udm_name = 'password'

class SchoolAttribute(CommonName):
	udm_name = None

class SchoolClassStringAttribute(Attribute):
	pass

class SchoolClassAttribute(Attribute):
	pass

class Description(Attribute):
	udm_name = 'description'

class DisplayName(Attribute):
	udm_name = 'displayName'
	extended = True

class EmptyAttributes(Attribute):
	udm_name = 'emptyAttributes'
	# syntax = dhcp_dnsFixedAttributes # only set internally, no need to use.
	#   also, it is not part of the "main" syntax.py!

class ContainerPath(Attribute):
	syntax = boolean

class ShareFileServer(Attribute):
	syntax = UCSSchool_Server_DN
	extended = True

class Groups(Attribute):
	syntax = GroupDN

class IPAddress(Attribute):
	udm_name = 'ip'
	syntax = ipAddress

class SubnetMask(Attribute):
	pass

class MACAddress(Attribute):
	udm_name = 'mac'
	syntax = MAC_Address

class InventoryNumber(Attribute):
	pass

class UCSSchoolHelperOptions(object):
	def __init__(self, klass, meta=None):
		self.set_from_meta_object(meta, 'udm_module', None)
		self.set_from_meta_object(meta, 'udm_filter', '')
		self.set_from_meta_object(meta, 'name_is_unique', False)
		self.set_from_meta_object(meta, 'allow_school_change', False)
		udm_module_short = None
		if self.udm_module:
			udm_module_short = self.udm_module.split('/')[1]
		self.set_from_meta_object(meta, 'udm_module_short', udm_module_short)
		if self.udm_module:
			module = udm_modules.get(self.udm_module)
			if not module:
				# happens when the udm_module is not in the standard package
				#   i.e. computers/ucc
				return
			for key, attr in klass._attributes.iteritems():
				# sanity checks whether we specified everything correctly
				if attr.udm_name and not attr.extended:
					# extended? only available after module_init(lo)
					#   we have to trust ourselved here
					if attr.udm_name not in module.property_descriptions:
						raise RuntimeError('%s\'s attribute "%s" is has no counterpart in the module\'s property_descriptions ("%s")!' % (klass.__name__, key, attr.udm_name))
			udm_name = klass._attributes['name'].udm_name
			ldap_name = module.mapping.mapName(udm_name)
			self.ldap_name_part = ldap_name

	def set_from_meta_object(self, meta, name, default):
		value = default
		if hasattr(meta, name):
			value = getattr(meta, name)
		setattr(self, name, value)

class UCSSchoolHelperMetaClass(type):
	def __new__(mcs, cls_name, bases, attrs):
		attributes = {}
		meta = attrs.get('Meta')
		for base in bases:
			if hasattr(base, '_attributes'):
				attributes.update(base._attributes)
			if meta is None and hasattr(base, '_meta'):
				meta = base._meta
		for name, value in attrs.iteritems():
			if name in attributes:
				del attributes[name]
			if isinstance(value, Attribute):
				attributes[name] = value
		cls = super(UCSSchoolHelperMetaClass, mcs).__new__(mcs, cls_name, bases, dict(attrs))
		cls._attributes = attributes
		cls._meta = UCSSchoolHelperOptions(cls, meta)
		return cls

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
			MODULE.info('Initializing %r' % (key,))
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
			return '%s=%s,%s' % (self._meta.ldap_name_part, self.name, container)

	def set_dn(self, dn):
		self.custom_dn = None
		self.old_dn = dn

	def validate(self, lo, validate_unlikely_changes=False):
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

	def _alter_udm_obj(self, udm_obj):
		for name, attr in self._attributes.iteritems():
			if attr.udm_name:
				value = getattr(self, name)
				if value is not None:
					udm_obj[attr.udm_name] = value

	#@hook
	def create(self, lo, validate=True):
		MODULE.process('Creating %r' % self)

		if self.exists(lo):
			MODULE.process('%s already exists!' % self.dn)
			return False

		if validate:
			self.validate(lo)
			if self.errors:
				raise ValidationError(self.errors.copy())

		pos = udm_uldap.position(ucr.get('ldap/base'))
		pos.setDn(self.get_own_container())
		udm_obj = udm_modules.get(self._meta.udm_module).object(None, lo, pos)
		udm_obj.open()

		# here is the real logic
		self.do_create(udm_obj, lo)

		# get it fresh from the database (needed for udm_obj._exists ...)
		self._udm_obj_searched = False
		self.set_dn(self.dn)
		return True

	def do_create(self, udm_obj, lo):
		self._alter_udm_obj(udm_obj)
		udm_obj.create()

	#@hook
	def modify(self, lo, validate=True):
		MODULE.process('Modifying %r' % self)

		if validate:
			self.validate(lo, validate_unlikely_changes=True)
			if self.errors:
				raise ValidationError(self.errors.copy())

		udm_obj = self.get_udm_object(lo)
		if not udm_obj:
			MODULE.process('%s does not exist!' % self.old_dn)
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
		return not same

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

	def do_modify(self, udm_obj, lo):
		self._alter_udm_obj(udm_obj)
		udm_obj.modify()

	#@hook
	def remove(self, lo):
		MODULE.process('Deleting %r' % self)
		udm_obj = self.get_udm_object(lo)
		if udm_obj:
			udm_obj.remove(remove_childs=True)
			self._udm_obj_searched = False
			self.set_dn(None)
			return True
		return False

	@classmethod
	def get_name_from_dn(cls, dn):
		if dn:
			return ldap.explode_dn(dn, 1)[0]

	def get_udm_object(self, lo):
		if self._udm_obj_searched is False:
			dn = self.old_dn or self.dn
			if dn is None:
				MODULE.info('Getting UDM object: No DN!')
				return
			if self._meta.name_is_unique:
				if self.name is None:
					return None
				udm_name = self._attributes['name'].udm_name
				name = self.get_name_from_dn(dn)
				filter_str = '%s=%s' % (udm_name, escape_filter_chars(name))
				MODULE.info('Getting UDM object by filter: %s' % filter_str)
				self._udm_obj = self.get_first_udm_obj(lo, filter_str)
			else:
				try:
					MODULE.info('Getting UDM object by dn: %s' % dn)
					self._udm_obj = udm_modules.lookup(self._meta.udm_module, None, lo, scope='base', base=dn)[0]
				except (noObject, IndexError):
					self._udm_obj = None
			if self._udm_obj:
				self._udm_obj.open()
			self._udm_obj_searched = True
		return self._udm_obj

	def get_own_container(self):
		if self.supports_school() and not self.school:
			return None
		return self.get_container(self.school)

	@classmethod
	def get_container(cls, school):
		raise NotImplementedError()

	@classmethod
	def get_search_base(cls, school_name):
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
	def get_all(cls, school, lo):
		cls.init_udm_module(lo)
		ret = []
		udm_objs = udm_modules.lookup(cls._meta.udm_module, None, lo, filter=cls._meta.udm_filter, base=cls.get_container(school), scope='sub')
		for udm_obj in udm_objs:
			udm_obj.open()
			obj = cls.from_udm_obj(udm_obj, school, lo)
			if obj:
				ret.append(obj)
		return ret

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		cls.init_udm_module(lo)
		klass = cls.get_class_for_udm_obj(udm_obj, school)
		if klass is None:
			MODULE.warn('UDM object %s does not correspond to a class in UCS school lib!' % udm_obj.dn)
			return None
		if klass is not cls:
			MODULE.process('UDM object %s is not %s, but actually %s' % (udm_obj.dn, cls.__name__, klass.__name__))
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
			return '%s(name=%r, school=%r, dn=%s)' % (self.__class__.__name__, self.name, self.school, self.custom_dn or self.old_dn)
		else:
			return '%s(name=%r, dn=%s)' % (self.__class__.__name__, self.name, self.custom_dn or self.old_dn)

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
		return SEP_CHAR.join(attrs)

class User(UCSSchoolHelperAbstractClass):
	name = UserName(_('Username'), aka=['Username'])
	firstname = Firstname(_('First name'), aka=['First name'], required=True, unlikely_to_change=True)
	lastname = Lastname(_('Last name'), aka=['Last name'], required=True, unlikely_to_change=True)
	birthday = Birthday(_('Birthday'), aka=['Birthday'], unlikely_to_change=True)
	email = Email(_('Email'), aka=['Email'], unlikely_to_change=True)
	password = Password(_('Password'), aka=['Password'])

	type_name = None

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
		self.password = self.password or generate_random()
		udm_obj['primaryGroup'] = self.primary_group_dn(lo)
		udm_obj['groups'] = self.groups_used(lo)
		return super(User, self).do_create(udm_obj, lo)

	def do_modify(self, udm_obj, lo):
		self.create_mail_domain(lo)
		self.password = self.password or None
		mandatory_groups = self.groups_used(lo)
		all_schools = School.get_all(lo, respect_local_oulist=False)
		for group_dn in udm_obj['groups'][:]:
			MODULE.info('Checking group %s for removal' % group_dn)
			if group_dn not in mandatory_groups:
				MODULE.info('Group not mandatory! Part of a school?')
				for school in all_schools:
					if Group.is_school_group(school.name, group_dn):
						MODULE.info('Yes, part of %s! Removing...' % school)
						udm_obj['groups'].remove(group_dn)
						break
				else:
					MODULE.info('No. Leaving it alone...')
		for group_dn in mandatory_groups:
			MODULE.info('Checking group %s for adding' % group_dn)
			if group_dn not in udm_obj['groups']:
				MODULE.info('Group is not yet part of the user. Adding...')
				udm_obj['groups'].append(group_dn)
		return super(User, self).do_modify(udm_obj, lo)

	def create_mail_domain(self, lo):
		if self.email:
			domain_name = self.email.split('@')[-1]
			mail_domain = MailDomain.get(domain_name)
			mail_domain.create(lo)

	def get_specific_groups(self, lo):
		return []

	def validate(self, lo, validate_unlikely_changes=False):
		super(User, self).validate(lo, validate_unlikely_changes)
		if self.email:
			name, email = escape_filter_chars(self.name), escape_filter_chars(self.email)
			if self.get_first_udm_obj(lo, '&(!(uid=%s))(mailPrimaryAddress=%s)' % (name, email)):
				self.add_error('email', _('The email address is already taken by another user. Please change the email address.'))

	def get_group_dn(self, group_name):
		return Group.get(group_name, self.school).dn

	def get_class_dn(self, class_name, lo):
		# Bug #32337: check if the class exists without OU prefix
		# if it does not exist the class name with OU prefix is used
		school_class = SchoolClass.get(class_name, self.school)
		if not school_class.exists(lo):
			school_class = SchoolClass.get('%s-%s' % (self.school, class_name), self.school)
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
			group = SchoolClass.get(name, school)
		else:
			group = Group.get(name, school)
		if fresh:
			group._udm_obj_searched = False
		group.create(lo)
		return group

	def _map_func_name_to_code(cls, func_name):
		if func_name == 'create':
			return 'A'
		elif func_name == 'modify':
			return 'M'
		elif func_name == 'remove':
			return 'D'

	def build_hook_line(self, hook_time, func_name):
		code = self._map_func_name_to_code(func_name)
		name = self.name or ''
		if name:
			name = name.lower()
		return self._build_hook_line(
				code,
				name,
				self.lastname,
				self.firstname,
				self.school,
				self.school_class,
				'', # TODO: rights?
				self.email,
				self.is_teacher(),
				self.is_active(),
				self.is_staff(),
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
		ret['type_name'] = self.type_name
		ret['type'] = self.__class__.__name__
		ret['type'] = ret['type'][0].lower() + ret['type'][1:]
		return ret

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).users

	class Meta:
		udm_module = 'users/user'
		name_is_unique = True
		allow_school_change = False # code _should_ be able to handle it

class Student(User):
	school_class = SchoolClassStringAttribute(_('Class'), aka=['Class'])

	type_name = _('Student')

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		obj = super(Student, cls).from_udm_obj(udm_obj, school, lo)
		if obj:
			school_class = None
			for group in udm_obj['groups']:
				if Group.is_school_class(school, group):
					school_class_name = cls.get_name_from_dn(group)
					school_class = school_class_name.split('-')[-1]
					break
			obj.school_class = school_class
			return obj

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).students

	def get_specific_groups(self, lo):
		groups = []
		groups.append(self.get_students_group_dn())
		if self.school_class:
			groups.append(self.get_class_dn(self.school_class, lo))
		return groups

class Teacher(User):
	school_class = SchoolClassStringAttribute(_('Class'), aka=['Class'])

	type_name = _('Teacher')

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		obj = super(Teacher, cls).from_udm_obj(udm_obj, school, lo)
		if obj:
			school_class = None
			school_classes = []
			for group in udm_obj['groups']:
				if Group.is_school_class(school, group):
					school_class_name = cls.get_name_from_dn(group)
					school_class = school_class_name.split('-')[-1]
					school_classes.append(school_class)
				school_class = ','.join(school_classes)
			obj.school_class = school_class
			return obj

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).teachers

	def get_specific_groups(self, lo):
		groups = []
		groups.append(self.get_teachers_group_dn())
		if self.school_class:
			for school_class in self.school_class.split(','):
				groups.append(self.get_class_dn(school_class, lo))
		return groups

class Staff(User):
	type_name = _('Staff')

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).staff

	def get_specific_groups(self, lo):
		groups = []
		groups.append(self.get_staff_group_dn())
		return groups

class TeachersAndStaff(Teacher):
	type_name = _('Teacher and Staff')

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).teachersAndStaff

	def get_specific_groups(self, lo):
		groups = super(TeachersAndStaff, self).get_specific_groups(lo)
		groups.append(self.get_staff_group_dn())
		return groups

class Group(UCSSchoolHelperAbstractClass):
	name = GroupName(_('Name'))
	description = Description(_('Description'))

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).groups

	@classmethod
	def is_school_group(cls, school, group_dn):
		return cls.get_search_base(school).isGroup(group_dn)

	@classmethod
	def is_school_class(cls, school, group_dn):
		return cls.get_search_base(school).isClass(group_dn)

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		if cls.is_school_class(school, udm_obj.dn):
			return SchoolClass
		return cls

	def add_umc_policy(self, policy_dn, lo):
		if not policy_dn or policy_dn.lower() == 'none':
			MODULE.warn('No policy added to %r' % self)
			return
		try:
			policy = UMCPolicy.from_dn(policy_dn, self.school, lo)
		except noObject:
			MODULE.warn('Object to be referenced does not exist (or is no UMC-Policy): %s' % policy_dn)
		else:
			policy.attach(self, lo)

	class Meta:
		udm_module = 'groups/group'
		name_is_unique = True

class BasicGroup(Group):
	school = None
	container = Attribute(_('Container'), required=True)

	def __init__(self, **kwargs):
		if 'container' not in kwargs:
			kwargs['container'] = 'cn=groups,%s' % ucr.get('ldap/base')
		super(BasicGroup, self).__init__(**kwargs)

	def create(self, lo, validate=True):
		# prepare LDAP: create containers where this basic group lives if necessary
		container_dn = self.get_own_container()[:-len(ucr.get('ldap/base'))-1]
		containers = str2dn(container_dn)
		super_container_dn = ucr.get('ldap/base')
		for container_info in reversed(containers):
			dn_part, cn = container_info[0][0:2]
			if dn_part.lower() == 'ou':
				container = OU(name=cn)
			else:
				container = Container(name=cn, school='', group_path='1')
			super_container_dn = container.create_in_container(super_container_dn, lo)
		return super(BasicGroup, self).create(lo, validate)

	def get_own_container(self):
		return self.container

	@classmethod
	def get_container(cls, school=None):
		return ucr.get('ldap/base')

class SchoolClass(Group):
	def create(self, lo, validate=True):
		success = super(SchoolClass, self).create(lo, validate)
		self.create_share(lo)
		return success

	def create_share(self, lo):
		share = ClassShare.from_school_class(self)
		share.create(lo)
		return share

	def modify(self, lo, validate=True):
		share = ClassShare.from_school_class(self)
		if self.old_dn:
			old_name = self.get_name_from_dn(self.old_dn)
			if old_name != self.name:
				# recreate the share.
				# if the name changed
				# from_school_class will have initialized
				# share.old_dn incorrectly
				share = ClassShare(name=old_name, school=self.school, school_class=self)
				share.name = self.name
		udm_obj = super(SchoolClass, self).modify(lo, validate)
		if share.exists(lo):
			share.modify(lo)
		else:
			self.create_share(lo)
		return udm_obj

	def remove(self, lo):
		udm_obj = super(SchoolClass, self).remove(lo)
		share = ClassShare.from_school_class(self)
		share.remove(lo)
		return udm_obj

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).classes

	def get_relative_name(self):
		# schoolname-1a => 1a
		if self.name.startswith(self.school):
			return self.name[len(self.school) + 1:]
		return self.name

	def to_dict(self):
		ret = super(SchoolClass, self).to_dict()
		ret['name'] = self.get_relative_name()
		return ret

class ClassShare(UCSSchoolHelperAbstractClass):
	name = ShareName(_('Name'))
	school_class = SchoolClassAttribute(_('School class'), required=True, internal=True)

	@classmethod
	def from_school_class(cls, school_class):
		return cls(name=school_class.name, school=school_class.school, school_class=school_class)

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).classShares

	def do_create(self, udm_obj, lo):
		gidNumber = self.school_class.get_udm_object(lo)['gidNumber']
		udm_obj['host'] = self.get_server_fqdn(lo)
		udm_obj['path'] = '/home/groups/klassen/%s' % self.name
		udm_obj['writeable'] = '1'
		udm_obj['sambaWriteable'] = '1'
		udm_obj['sambaBrowseable'] = '1'
		udm_obj['sambaForceGroup'] = '+%s' % self.name
		udm_obj['sambaCreateMode'] = '0770'
		udm_obj['sambaDirectoryMode'] = '0770'
		udm_obj['owner'] = '0'
		udm_obj['group'] = gidNumber
		udm_obj['directorymode'] = '0770'
		MODULE.process('Creating share on "%s"' % udm_obj['host'])
		return super(ClassShare, self).do_create(udm_obj, lo)

	def do_modify(self, udm_obj, lo):
		old_name = self.get_name_from_dn(self.old_dn)
		if old_name != self.name:
			head, tail = os.path.split(udm_obj['path'])
			tail = self.name
			udm_obj['path'] = os.path.join(head, tail)
			if udm_obj['sambaName'] == old_name:
				udm_obj['sambaName'] = self.name
			if udm_obj['sambaForceGroup'] == '+%s' % old_name:
				udm_obj['sambaForceGroup'] = '+%s' % self.name
		return super(ClassShare, self).do_modify(udm_obj, lo)

	def get_server_fqdn(self, lo):
		domainname = ucr.get('domainname')
		school_dn = School.get(self.school).dn

		# fetch serverfqdn from OU
		result = lo.get(school_dn, ['ucsschoolClassShareFileServer'])
		if result:
			server_domain_name = lo.get(result['ucsschoolClassShareFileServer'][0], ['associatedDomain'])
			if server_domain_name:
				server_domain_name = server_domain_name['associatedDomain'][0]
			else:
				server_domain_name = domainname
			result = lo.get(result['ucsschoolClassShareFileServer'][0], ['cn'])
			if result:
				return '%s.%s' % (result['cn'][0], server_domain_name)

		# get alternative server (defined at ou object if a dc slave is responsible for more than one ou)
		ou_attr_ldap_access_write = lo.get(school_dn, ['univentionLDAPAccessWrite'])
		alternative_server_dn = None
		if len(ou_attr_ldap_access_write) > 0:
			alternative_server_dn = ou_attr_ldap_access_write['univentionLDAPAccessWrite'][0]
			if len(ou_attr_ldap_access_write) > 1:
				MODULE.warn('more than one corresponding univentionLDAPAccessWrite found at ou=%s' % self.school)

		# build fqdn of alternative server and set serverfqdn
		if alternative_server_dn:
			alternative_server_attr = lo.get(alternative_server_dn, ['uid'])
			if len(alternative_server_attr) > 0:
				alternative_server_uid = alternative_server_attr['uid'][0]
				alternative_server_uid = alternative_server_uid.replace('$', '')
				if len(alternative_server_uid) > 0:
					return '%s.%s' % (alternative_server_uid, domainname)

		# fallback
		return 'dc%s-01.%s' % (self.school.lower(), domainname)

	class Meta:
		udm_module = 'shares/share'

class MailDomain(UCSSchoolHelperAbstractClass):
	school = None

	@classmethod
	def get_container(cls, school=None):
		return 'cn=domain,cn=mail,%s' % ucr.get('ldap/base')

	class Meta:
		udm_module = 'mail/domain'

class School(UCSSchoolHelperAbstractClass):
	name = SchoolName(_('School name'))
	dc_name = DCName(_('DC Name'))
	class_share_file_server = ShareFileServer(_('Server for class shares'), udm_name='ucsschoolClassShareFileServer')
	home_share_file_server = ShareFileServer(_('Server for Windows home directories'), udm_name='ucsschoolHomeShareFileServer')
	display_name = DisplayName(_('Display name'))
	school = None

	def __init__(self, **kwargs):
		super(School, self).__init__(**kwargs)
		self.display_name = self.display_name or self.name

	def build_hook_line(self, hook_time, func_name):
		if func_name == 'create':
			return self._build_hook_line(self.name, self.dc_name)

	def get_district(self):
		if ucr.is_true('ucsschool/ldap/district/enable'):
			return self.name[:2]

	def get_own_container(self):
		district = self.get_district()
		if district:
			return 'ou=%s,%s' % (district, self.get_container())
		return self.get_container()

	@classmethod
	def get_container(cls, school=None):
		return ucr.get('ldap/base')

	@classmethod
	def cn_name(cls, name, default):
		ucr_var = 'ucsschool/ldap/default/container/%s' % name
		return ucr.get(ucr_var, default)

	def create_default_containers(self, lo):
		cn_pupils = self.cn_name('pupils', 'schueler')
		cn_teachers = self.cn_name('teachers', 'lehrer')
		cn_admins = self.cn_name('admins', 'admins')
		cn_classes = self.cn_name('class', 'klassen')
		cn_rooms = self.cn_name('rooms', 'raeume')
		user_containers = [cn_pupils, cn_teachers, cn_admins]
		group_containers = [cn_pupils, [cn_classes], cn_teachers, cn_rooms]
		if ucr.is_true('ucsschool/ldap/noneducational/create/objects', True):
			cn_staff = self.cn_name('staff', 'mitarbeiter')
			cn_teachers_staff = self.cn_name('teachers-and-staff', 'lehrer und mitarbeiter')
			user_containers.extend([cn_staff, cn_teachers_staff])
			group_containers.append(cn_staff)
		containers_with_path = {
			'printer_path': ['printers'],
			'user_path' : ['users', user_containers],
			'computer_path' : ['computers', ['server', ['dc']]],
			'network_path' : ['networks'],
			'group_path' : ['groups', group_containers],
			'dhcp_path' : ['dhcp'],
			'policy_path' : ['policies'],
			'share_path' : ['shares', [cn_classes]],
		}

		def _add_container(name, last_dn, base_dn, path, lo):
			if isinstance(name, (list, tuple)):
				base_dn = last_dn
				for cn in name:
					last_dn = _add_container(cn, last_dn, base_dn, path, lo)
			else:
				container = Container(name=name, school=self.name)
				setattr(container, path, '1')
				last_dn = container.create_in_container(base_dn, lo)
			return last_dn

		last_dn = self.dn
		path = None
		for path, containers in containers_with_path.iteritems():
			for cn in containers:
				last_dn = _add_container(cn, last_dn, self.dn, path, lo)

	def group_name(self, prefix_var, default_prefix):
		ucr_var = 'ucsschool/ldap/default/groupprefix/%s' % prefix_var
		name_part = ucr.get(ucr_var, default_prefix)
		school_part = self.name.lower()
		return '%s%s' % (name_part, school_part)

	def get_umc_policy_dn(self, name):
		# at least the default ones should exist due to the join script
		return ucr.get('ucsschool/ldap/default/policy/umc/%s' % name, 'cn=ucsschool-umc-%s-default,cn=UMC,cn=policies,%s' % (name, ucr.get('ldap/base')))

	def create_default_groups(self, lo):
		# DC groups
		administrative_group_container = 'cn=ucsschool,cn=groups,%s' % ucr.get('ldap/base')

		# DC-Edukativnetz
		# OU%s-DC-Edukativnetz
		# Member-Edukativnetz
		# OU%s-Member-Edukativnetz
		administrative_group_names = self.get_administrative_group_name('educational', domain_controller='both', ou_specific='both')
		if ucr.is_true('ucsschool/ldap/noneducational/create/objects', True):
			administrative_group_names.extend(self.get_administrative_group_name('noneducational', domain_controller='both', ou_specific='both')) # same with Verwaltungsnetz
		for administrative_group_name in administrative_group_names:
			group = BasicGroup.get(name=administrative_group_name, container=administrative_group_container)
			group.create(lo)

		# cn=ouadmins
		admin_group_container = 'cn=ouadmins,cn=groups,%s' % ucr.get('ldap/base')
		group = BasicGroup.get(self.group_name('admins', 'admins-'), container=admin_group_container)
		group.create(lo)
		group.add_umc_policy(self.get_umc_policy_dn('admins'), lo)

		# cn=schueler
		group = Group.get(self.group_name('pupils', 'schueler-'), self.name)
		group.create(lo)
		group.add_umc_policy(self.get_umc_policy_dn('pupils'), lo)

		# cn=lehrer
		group = Group.get(self.group_name('teachers', 'lehrer-'), self.name)
		group.create(lo)
		group.add_umc_policy(self.get_umc_policy_dn('teachers'), lo)

		# cn=mitarbeiter
		if ucr.is_true('ucsschool/ldap/noneducational/create/objects', True):
			group = Group.get(self.group_name('staff', 'mitarbeiter-'), self.name)
			group.create(lo)
			group.add_umc_policy(self.get_umc_policy_dn('staff'), lo)

	def get_share_fileserver_dn(self, set_by_self, lo):
		if set_by_self:
			hostname = set_by_self
		elif self.dc_name:
			hostname = self.dc_name
		elif ucr.is_true('ucsschool/singlemaster', False):
			hostname = ucr.get('hostname')
		else:
			hostname = 'dc%s-01' % self.name.lower()
			host = SchoolDC.get(hostname, self.name)
			return host.dn

		host = AnyComputer.get_first_udm_obj(lo, 'cn=%s' % escape_filter_chars(hostname))
		if host:
			return host.dn
		else:
			MODULE.warn('Using this host as ShareFileServer ("%s").' % ucr.get('hostname'))
			return ucr.get('ldap/hostdn')

	def get_class_share_file_server(self, lo):
		return self.get_share_fileserver_dn(self.class_share_file_server, lo)

	def get_home_share_file_server(self, lo):
		return self.get_share_fileserver_dn(self.home_share_file_server, lo)

	def get_administrative_group_name(self, group_type, domain_controller=True, ou_specific=False, as_dn=False):
		if domain_controller == 'both':
			return flatten([self.get_administrative_group_name(group_type, True, ou_specific, as_dn), self.get_administrative_group_name(group_type, False, ou_specific, as_dn)])
		if ou_specific == 'both':
			return flatten([self.get_administrative_group_name(group_type, domain_controller, False, as_dn), self.get_administrative_group_name(group_type, domain_controller, True, as_dn)])
		if group_type == 'noneducational':
			name = 'Verwaltungsnetz'
		else:
			name = 'Edukativnetz'
		if domain_controller:
			name = 'DC-%s' % name
		else:
			name = 'Member-%s' % name
		if ou_specific:
			name = 'OU%s-%s' % (self.name.lower(), name)
		if as_dn:
			return 'cn=%s,cn=ucsschool,cn=groups,%s' % (name, ucr.get('ldap/base'))
		else:
			return name

	def add_host_to_dc_group(self, lo):
		dc = SchoolDCSlave.get(self.dc_name, self.name)
		if dc.exists(lo):
			dc_udm_obj = dc.get_udm_object(lo)
			name_of_noneducational_group = self.get_administrative_group_name(group_type='noneducational')
			for grp in dc_udm_obj['groups']:
				if grp.startswith('cn=%s,' % name_of_noneducational_group):
					groups = self.get_administrative_group_name('noneducational', ou_specific='both', as_dn=True)
					break
			else:
				groups = self.get_administrative_group_name('educational', ou_specific='both', as_dn=True)
			for grp in groups:
				if grp not in dc_udm_obj['groups']:
					dc_udm_obj['groups'].append(grp)
			dc_udm_obj.modify()

	def add_domain_controllers(self, lo):
		school_dcs = ucr.get('ucsschool/ldap/default/dcs', 'edukativ').split()
		for dc in school_dcs:
			if dc == 'verwaltung':
				if not ucr.is_true('ucsschool/ldap/noneducational/create/objects', True):
					continue
				groups = self.get_administrative_group_name('noneducational', ou_specific='both', as_dn=True)
				dc_name = '%sv' % self.dc_name or 'dc%sv-01' % self.name.lower() # this is the naming convention, a trailing v for Verwaltungsnetz DCs

			else:
				dc_name = self.dc_name or 'dc%s-01' % self.name.lower()
				groups = self.get_administrative_group_name('educational', ou_specific='both', as_dn=True)
			if ucr.is_true('ucsschool/singlemaster', False):
				dc_name = ucr.get('hostname')

			server = AnyComputer.get_first_udm_obj(lo, 'cn=%s' % escape_filter_chars(dc_name))
			if not server and not self.dc_name:
				group_dn = groups[0] # cn=OU%s-DC-[Verwaltungs|Edukativ]netz,...
				try:
					hostlist = lo.get(group_dn, ['uniqueMember']).get('uniqueMember', [])
				except ldap.NO_SUCH_OBJECT:
					hostlist = []
				except Exception, e:
					MODULE.error('cannot read %s: %s' % (group_dn, e))

				if hostlist:
					continue # if at least one DC has control over this OU then jump to next 'school_dcs' item

			if server:
				if self.dc_name:
					# manual dc name has been specified by user

					# check if existing system is a DC master or DC backup
					def get_computer_objs(module, hostname):
						filter_str = 'cn=%s' % escape_filter_chars(hostname)
						return udm_modules.lookup(module, None, lo, scope='sub', base=ucr.get('ldap/base'), filter=filter_str)
					master_objs = get_computer_objs('computers/domaincontroller_master', dc_name)
					backup_objs = get_computer_objs('computers/domaincontroller_backup', dc_name)
					is_master_or_backup = master_objs or backup_objs

					# check if existing system is a DC slave
					slave_objs = get_computer_objs('computers/domaincontroller_slave', dc_name)
					is_slave = len(slave_objs) > 0

					if not is_master_or_backup and not is_slave:
						MODULE.warn('Given system name %s is already in use and no domaincontroller system. Please choose another name' % dc_name)
						return

					if is_master_or_backup and is_slave:
						MODULE.error('Implementation error: %s seems to be dc slave and dc master at the same time' % dc_name)
						return

					if len(slave_objs) > 1:
						MODULE.error('More than one system with cn=%s found' % dc_name)
						return

					if is_slave:
						obj = slave_objs[0]
						obj.open()
						for group in groups:
							if group not in obj['groups']:
								obj['groups'].append(group)
						MODULE.process('Modifying %s' % obj.dn)
						obj.modify()
			else:
				dc = SchoolDCSlave.get(dc_name, self.name, groups=groups)
				dc.create(lo)

			dhcp_service = DHCPService.get(self.name.lower(), self.name, hostname=dc_name, domainname=ucr.get('domainname'))
			dhcp_service.create(lo)
			dhcp_service.add_server(dc_name, lo)

	def create(self, lo, validate=True):
		district = self.get_district()
		if district:
			ou = OU(name=district)
			ou.create_in_container(ucr.get('ldap/base'), lo)

		self.class_share_file_server = self.get_class_share_file_server(lo)
		self.home_share_file_server = self.get_home_share_file_server(lo)

		success = super(School, self).create(lo, validate)
		if not success:
			return False

		self.create_default_containers(lo)
		self.create_default_groups(lo)
		self.add_host_to_dc_group(lo)
		self.add_domain_controllers(lo)

		# In a single server environment the default DHCP container must
		# be set to the DHCP container in the school ou. Otherwise newly
		# imported computers have the DHCP objects in the wrong DHCP container
		if ucr.is_true('ucsschool/singlemaster', False):
			if not ucr.get('dhcpd/ldap/base'):
				handler_set(['dhcpd/ldap/base=cn=dhcp,%s' % (self.dn)])

		# if requested, then create dhcp_dns policy that clears univentionDhcpDomainNameServers at OU level
		# to prevent problems with "wrong" DHCP DNS policy connected to ldap base
		if ucr.is_true('ucsschool/import/generate/policy/dhcp/dns/clearou', False):
			policy = DHCPDNSPolicy(name='dhcp-dns-clear', school=self.name, empty_attributes=['univentionDhcpDomainNameServers'])
			policy.create(lo)
			policy.attach(self, lo)

		return success

	def do_create(self, udm_obj, lo):
		udm_obj.options = ['UCSschool-School-OU']
		return super(School, self).do_create(udm_obj, lo)

	@classmethod
	def get_from_oulist(cls, lo, oulist):
		ous = [x.strip() for x in oulist.split(',')]
		schools = []
		for ou in ous:
			MODULE.info('All Schools: Getting OU %s' % ou)
			school = cls.from_dn(cls(name=ou).dn, None, lo)
			MODULE.info('All Schools: Found school: %r' % school)
			schools.append(school)
		return schools

	@classmethod
	def from_binddn(cls, lo):
		MODULE.info('All Schools: Showing all OUs which DN %s can read.' % lo.binddn)
		if lo.binddn.find('ou=') > 0:
			# we got an OU in the user DN -> school teacher or assistent
			# restrict the visibility to current school
			# (note that there can be schools with a DN such as ou=25g18,ou=25,dc=...)
			school_dn = lo.binddn[lo.binddn.find('ou='):]
			MODULE.info('Schools from binddn: Found an OU in the LDAP binddn. Restricting schools to only show %s' % school_dn)
			school = cls.from_dn(school_dn, None, lo)
			MODULE.info('Schools from binddn: Found school: %r' % school)
			return [school]
		else:
			MODULE.warn('Schools from binddn: Unable to identify OU of this account - showing all OUs!')
			return School.get_all(lo)

	@classmethod
	def get_all(cls, lo, respect_local_oulist=True):
		oulist = ucr.get('ucsschool/local/oulist')
		if oulist and respect_local_oulist:
			MODULE.info('All Schools: Schools overridden by UCR variable ucsschool/local/oulist')
			return cls.get_from_oulist(cls, lo, oulist)
		else:
			return super(School, cls).get_all(None, lo)

	def __str__(self):
		return self.name

	class Meta:
		udm_module = 'container/ou'
		udm_filter = 'objectClass=ucsschoolOrganizationalUnit'

class OU(UCSSchoolHelperAbstractClass):
	def create_in_container(self, container, lo):
		self.fake_dn(container)
		MODULE.process('Creating %r' % self)
		pos = udm_uldap.position(ucr.get('ldap/base'))
		pos.setDn(container)
		udm_obj = udm_modules.get(self._meta.udm_module).object(None, lo, pos)
		udm_obj.open()
		udm_obj['name'] = self.name
		try:
			udm_obj.create()
		except objectExists as e:
			return str(e)
		else:
			return udm_obj.dn

	def create(self, lo, validate=True):
		raise NotImplementedError()

	def modify(self, lo, validate=True):
		raise NotImplementedError()

	def remove(self, lo):
		raise NotImplementedError()

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).schoolDN

	def fake_dn(self, container):
		# set custom_dn just for log
		self.custom_dn = 'ou=%s,%s' % (self.name, container)

	class Meta:
		udm_module = 'container/ou'

class Container(OU):
	user_path = ContainerPath(_('User path'), udm_name='userPath')
	computer_path = ContainerPath(_('Computer path'), udm_name='computerPath')
	network_path = ContainerPath(_('Network path'), udm_name='networkPath')
	group_path = ContainerPath(_('Group path'), udm_name='groupPath')
	dhcp_path = ContainerPath(_('DHCP path'), udm_name='dhcpPath')
	policy_path = ContainerPath(_('Policy path'), udm_name='policyPath')
	share_path = ContainerPath(_('Share path'), udm_name='sharePath')
	printer_path = ContainerPath(_('Printer path'), udm_name='printerPath')

	def fake_dn(self, container):
		self.custom_dn = 'cn=%s,%s' % (self.name, container)

	class Meta:
		udm_module = 'container/cn'

class DHCPService(UCSSchoolHelperAbstractClass):
	name = DHCPServiceName(_('Service'))
	hostname = Attribute(_('Hostname'))
	domainname = Attribute(_('Domain'))

	def do_create(self, udm_obj, lo):
		udm_obj['option'] = ['wpad "http://%s.%s/proxy.pac"' % (self.hostname, self.domainname)]
		return super(DHCPService, self).do_create(udm_obj, lo)

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).dhcp

	def add_server(self, dc_name, lo):
		# TODO: more or less copied due to time constraints. Not adapted to "new"
		#   model style. DHCPServer or something would be necessary

		# create dhcp-server if not exsistant
		school = School.get(self.school)
		pos = udm_uldap.position(ucr.get('ldap/base'))
		dhcp_server_module = udm_modules.get('dhcp/server')
		dhcp_subnet_module = udm_modules.get('dhcp/subnet')
		objects = lo.searchDn(filter='(&(objectClass=dhcpServer)(cn=%s))' % dc_name, base=ucr.get('ldap/base'))
		if objects:
			# move existing dhcp server object to OU
			new_dhcp_server_dn = 'cn=%s,cn=%s,cn=dhcp,%s' % (dc_name, school.name.lower(), school.dn)
			if len(objects) > 1:
				MODULE.warn('More than one dhcp-server object found! Moving only one!')
			obj = udm_objects.get(dhcp_server_module, None, lo, position='', dn=objects[0])
			obj.open()
			dhcpServerContainer = ','.join(objects[0].split(',')[1:])
			if obj.dn.lower() != new_dhcp_server_dn.lower():
				attr_server = obj['server']
				MODULE.process('need to remove dhcp server: %s' % obj.dn)
				try:
					obj.remove()
				except:
					MODULE.error('Failed to remove dhcp server: %s' % (obj.dn))
				pos.setDn('cn=%s,cn=dhcp,%s' % (school.name.lower(), school.dn))
				MODULE.process('need to create dhcp server: %s' % pos.getDn())
				obj = dhcp_server_module.object(None, lo, position=pos, superordinate=self)
				obj.open()
				obj['server'] = attr_server
				try:
					obj.create()
					MODULE.process('%s created' % obj.dn)
				except:
					MODULE.error('Failed to create dhcp server: %s' % pos.getDn())
			################
			# copy subnets #
			################
			# find local interfaces
			interfaces = []
			for interface_name in set([key.split('/')[1] for key in ucr.keys() if key.startswith('interfaces/eth')]):
				try:
					address = ipaddr.IPv4Network('%s/%s' % (ucr['interfaces/%s/address' % interface_name],
					                                        ucr['interfaces/%s/netmask' % interface_name]))
					interfaces.append(address)
				except ValueError as exc:
					MODULE.process('Skipping invalid interface %s:\n%s' % (interface_name, exc))
			objects = lo.searchDn(filter = '(objectClass=univentionDhcpSubnet)', base=dhcpServerContainer)
			for object_dn in objects:
				obj = udm_objects.get(dhcp_subnet_module, None, lo, position='', dn=object_dn)
				obj.open()
				subnet = ipaddr.IPv4Network('%s/%s' % (obj['subnet'], obj['subnetmask']))
				if subnet in interfaces: # subnet matches any local subnet
					pos.setDn('cn=%s,cn=dhcp,%s' % (school.name.lower(), school.dn))
					if lo.searchDn(filter='(&(objectClass=univentionDhcpSubnet)(cn=%s))' % obj['subnet'], base=pos.getDn()):
						MODULE.process('do not need to copy dhcp subnet %s: %s (target already exists)' % (subnet, obj.dn))
					else:
						MODULE.process('need to copy dhcp subnet %s: %s' % (subnet, obj.dn))
						new_object = dhcp_subnet_module.object(None, lo, position=pos, superordinate=self)
						new_object.open()
						for key in obj.keys():
							value = obj[key]
							new_object[key] = value
						try:
							new_object.create()
							MODULE.process('%s created' % new_object.dn)
						except:
							MODULE.error('Failed to copy dhcp subnet %s to %s' % (obj.dn, pos.getDn()))
				else:
					MODULE.process('Skipping non-local subnet %s' % subnet)
		else:
			# create fresh dhcp server object
			pos.setDn('cn=%s,cn=dhcp,%s'%(school.name.lower(), school.dn))
			obj = dhcp_server_module.object(None, lo, position=pos, superordinate=self)
			obj.open()
			obj['server'] = dc_name
			MODULE.process('need to create dhcp server: %s' % obj.dn)
			try:
				obj.create()
				MODULE.process('%s created' % obj.dn)
			except:
				pass

	class Meta:
		udm_module = 'dhcp/service'

class Policy(UCSSchoolHelperAbstractClass):
	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).policies

	def attach(self, obj, lo):
		# add univentionPolicyReference if neccessary
		oc = lo.get(obj.dn, ['objectClass'])
		if 'univentionPolicyReference' not in oc.get('objectClass', []):
			try:
				lo.modify(obj.dn, [('objectClass', '', 'univentionPolicyReference')])
			except:
				MODULE.warn('Objectclass univentionPolicyReference cannot be added to %r' % obj)
				return
		# add the missing policy
		pl = lo.get(obj.dn, ['univentionPolicyReference'])
		MODULE.warn('Attaching %r to %r' % (self, obj))
		if self.dn.lower() not in map(lambda x: x.lower(), pl.get('univentionPolicyReference', [])):
			modlist = [('univentionPolicyReference', '', self.dn)]
			MODULE.process('Attaching %r to %r' % (self, obj))
			try:
				lo.modify(obj.dn, modlist)
			except:
				MODULE.warn('Policy %s cannot be referenced to %r' % (self, obj))

class UMCPolicy(Policy):
	class Meta:
		udm_module = 'policies/umc'

class DHCPDNSPolicy(Policy):
	empty_attributes = EmptyAttributes(_('Empty attributes'))

	class Meta:
		udm_module = 'policies/dhcp_dns'

class AnyComputer(UCSSchoolHelperAbstractClass):
	@classmethod
	def get_container(cls, school=None):
		return ucr.get('ldap/base')

	class Meta:
		udm_module = 'computers/computer'

class SchoolDC(UCSSchoolHelperAbstractClass):
	@classmethod
	def get_container(cls, school):
		return 'cn=dc,cn=server,%s' % cls.get_search_base(school).computers

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		try:
			univention_object_class = udm_obj['univentionObjectClass']
		except KeyError:
			univention_object_class = None
		if univention_object_class == 'computers/domaincontroller_slave':
			return SchoolDCSlave
		return cls

class SchoolDCSlave(SchoolDC):
	groups = Groups(_('Groups'))

	def do_create(self, udm_obj, lo):
		udm_obj['unixhome'] = '/dev/null'
		udm_obj['shell'] = '/bin/bash'
		udm_obj['primaryGroup'] = BasicGroup.get('DC Slave Hosts').dn
		for group in self.groups:
			if group not in udm_obj['groups']:
				udm_obj['groups'].append(group)
		return super(SchoolDCSlave, self).do_create(udm_obj, lo)

	class Meta:
		udm_module = 'computers/domaincontroller_slave'

class SchoolComputer(UCSSchoolHelperAbstractClass):
	ip_address = IPAddress(_('IP address'), required=True)
	subnet_mask = SubnetMask(_('Subnet mask'))
	mac_address = MACAddress(_('MAC address'), required=True)
	inventory_number = InventoryNumber(_('Inventory number'))

	type_name = _('Computer')

	def _alter_udm_obj(self, udm_obj):
		if isinstance(self.inventory_number, basestring):
			udm_obj['inventoryNumber'] = self.inventory_number.split(',')
		ipv4_network = self.get_ipv4_network()
		if ipv4_network and ipv4_network.ip != ipv4_network.network:
			udm_obj['ip'] = str(ipv4_network.ip)
		return super(SchoolComputer, self)._alter_udm_obj(udm_obj)

	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).computers

	def create(self, lo, validate=True):
		self.create_network(lo)
		return super(SchoolComputer, self).create(lo, validate)

	def do_create(self, udm_obj, lo):
		network = self.get_network()
		if network:
			udm_obj['network'] = network.dn
		# TODO: groups. for memberserver...
		return super(SchoolComputer, self).do_create(udm_obj, lo)

	def get_ipv4_network(self):
		return None # FIXME
		if self.subnet_mask:
			network_str = '%s/%s' % self.ip_address, self.subnet_mask
		else:
			network_str = str(self.ip_address)
		try:
			return ipaddr.IPv4Network(network_str)
		except (ipaddr.AddressValueError, ipaddr.NetmaskValueError, ValueError):
			MODULE.warn('Unparsable network: %r' % network_str)

	def get_network(self):
		ipv4_network = self.get_ipv4_network()
		if ipv4_network:
			network_name = '%s-%s' % (self.school.lower(), ipv4_network.network)
			return Network(name=network_name, school=self.school)

	def create_network(self, lo):
		network = self.get_network()
		if network:
			network.create(lo)
		return network

	def validate(self, lo, validate_unlikely_changes=False):
		super(SchoolComputer, self).validate(lo, validate_unlikely_changes)
		if self.ip_address:
			name, ip_address = escape_filter_chars(self.name), escape_filter_chars(self.ip_address)
			if AnyComputer.get_first_udm_obj(lo, '&(!(cn=%s))(ip=%s)' % (name, ip_address)):
				self.add_error('ip_address', _('The ip address is already taken by another computer. Please change the ip address.'))
		if self.mac_address:
			name, mac_address = escape_filter_chars(self.name), escape_filter_chars(self.mac_address)
			if AnyComputer.get_first_udm_obj(lo, '&(!(cn=%s))(mac=%s)' % (name, mac_address)):
				self.add_error('mac_address', _('The mac address is already taken by another computer. Please change the mac address.'))

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		oc = udm_obj.lo.get(udm_obj.dn, ['objectClass'])
		object_classes = oc.get('objectClass', [])
		if 'univentionWindows' in object_classes:
			return WindowsComputer
		if 'univentionMacOSClient' in object_classes:
			return MacComputer
		if 'univentionCorporateClient' in object_classes:
			return UCCComputer
		if 'univentionClient' in object_classes:
			return IPComputer

	@classmethod
	def from_udm_obj(cls, udm_obj, school, lo):
		obj = super(SchoolComputer, cls).from_udm_obj(udm_obj, school, lo)
		if obj:
			obj.ip_address = udm_obj['ip']
			obj.subnet_mask = '255.255.255.0' # FIXME
			obj.inventory_number = udm_obj['inventoryNumber']
			return obj

	def to_dict(self):
		ret = super(SchoolComputer, self).to_dict()
		ret['type_name'] = self.type_name
		ret['type'] = self._meta.udm_module_short
		return ret

	class Meta:
		udm_module = 'computers/computer'
		name_is_unique = True

class WindowsComputer(SchoolComputer):
	type_name = _('Windows system')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/windows'

class MacComputer(SchoolComputer):
	type_name = _('Mac OS X')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/macos'

class IPComputer(SchoolComputer):
	type_name = _('Device with IP address')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/ipmanagedclient'

class UCCComputer(SchoolComputer):
	type_name = _('Univention Corporate Client')

	class Meta(SchoolComputer.Meta):
		udm_module = 'computers/ucc'

class Network(UCSSchoolHelperAbstractClass):
	@classmethod
	def get_container(cls, school):
		return cls.get_search_base(school).networks

	class Meta:
		udm_module = 'networks/network'

