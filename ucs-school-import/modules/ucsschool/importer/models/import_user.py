# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Representation of a user read from a file.
"""
# Copyright 2016-2017 Univention GmbH
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

import traceback
import re
import datetime
from collections import defaultdict
from ldap.filter import filter_format

from univention.admin.uexceptions import noObject, noProperty, valueError, valueInvalidSyntax
from univention.admin import property as uadmin_property
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from ucsschool.lib.models import School, Staff, Student, Teacher, TeachersAndStaff, User
from ucsschool.lib.models.attributes import RecordUID, SourceUID
from ucsschool.lib.models.utils import create_passwd, ucr
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.factory import Factory
from ucsschool.importer.exceptions import (
	BadPassword, EmptyFormatResultError, InvalidBirthday, InvalidClassName, InvalidEmail,
	MissingMailDomain, MissingMandatoryAttribute, MissingSchoolName, NotSupportedError, NoUsername, NoUsernameAtAll,
	UDMError, UDMValueError, UniqueIdError, UnkownDisabledSetting, UnknownProperty, UnkownSchoolName, UsernameToLong
)
from ucsschool.importer.utils.logging import get_logger
from ucsschool.lib.pyhooks import PyHooksLoader
from ucsschool.importer.utils.user_pyhook import UserPyHook
from ucsschool.importer.utils.format_pyhook import FormatPyHook


class ImportUser(User):
	"""
	Representation of a user read from a file. Abstract class, please use one
	of its subclasses ImportStaff etc.

	An import profile and a factory must have been loaded, before the class
	can be used:

	from ucsschool.importer.configuration import Configuration
	from ucsschool.importer.factory import Factory, load_class
	config = Configuration("/usr/share/ucs-school-import/config_default.json")
	fac_class = load_class(config["factory"])
	factory = Factory(fac_class())
	user = factory.make_import_user(roles)
	"""
	source_uid = SourceUID("SourceUID")
	record_uid = RecordUID("RecordUID")

	config = None
	default_username_max_length = 20
	attribute_udm_names = None
	no_overwrite_attributes = None
	_unique_ids = defaultdict(set)
	factory = None
	ucr = None
	unique_email_handler = None
	username_handler = None
	reader = None
	logger = None
	pyhooks_base_path = "/usr/share/ucs-school-import/pyhooks"
	_pyhook_cache = None
	_format_pyhook_cache = None
	# non-Attribute attributes (not in self._attributes) that can also be used
	# as arguments for object creation and will be exported by to_dict():
	_additional_props = ("action", "entry_count", "udm_properties", "input_data", "old_user", "in_hook", "roles")
	prop = uadmin_property("_replace")
	_all_school_names = None

	def __init__(self, name=None, school=None, **kwargs):
		self.action = None            # "A", "D" or "M"
		self.entry_count = 0          # line/node number of input data
		self.udm_properties = dict()  # UDM properties from input, that are not stored in Attributes
		self.input_data = list()      # raw input data created by SomeReader.read()
		self.old_user = None          # user in LDAP, when modifying
		self.in_hook = False          # if a hook is currently running

		for attr in self._additional_props:
			try:
				val = kwargs.pop(attr)
				setattr(self, attr, val)
			except KeyError:
				pass

		if not self.factory:
			self.__class__.factory = Factory()
			self.__class__.ucr = self.factory.make_ucr()
			self.__class__.config = Configuration()
			self.__class__.reader = self.factory.make_reader()
			self.__class__.logger = get_logger()
			try:
				self.__class__.default_username_max_length = self.config['username']['max_length']['default']
			except KeyError:
				pass
			self.__class__.attribute_udm_names = dict((attr.udm_name, name) for name, attr in self._attributes.items() if attr.udm_name)
			self.__class__.no_overwrite_attributes = self.ucr.get(
				"ucsschool/import/generate/user/attributes/no-overwrite",
				"homeShare homeSharePath mailHomeServer mailPrimaryAddress password profilepath sambahome uidNumber unixhome username"
			).split()
		self._lo = None
		self._userexpiry = None
		self._purge_ts = None
		super(ImportUser, self).__init__(name, school, **kwargs)

	def build_hook_line(self, hook_time, func_name):
		"""
		Recreate original input data for hook creation.

		IMPLEMENTME if the Reader class in use does not put a list with the
		original input text in self.input_data. return _build_hook_line() with
		a list as argument.
		"""
		return self._build_hook_line(*self.input_data)

	def call_hooks(self, hook_time, func_name):
		"""
		Runs PyHooks, then ucs-school-libs fork hooks.

		:param hook_time: str: "pre" or "post"
		:param func_name: str: "create", "modify", "move" or "remove"
		:return: int: return code of lib hooks
		"""
		if self._pyhook_cache is None:
			path = self.config.get('hooks_dir_pyhook', self.pyhooks_base_path)
			pyloader = PyHooksLoader(path, UserPyHook, self.logger)
			self.__class__._pyhook_cache = pyloader.get_hook_objects(self._lo)
		if hook_time == "post" and self.action in ["A", "M"]:
			# update self from LDAP
			user = self.get_by_import_id(self._lo, self.source_uid, self.record_uid)
			user_udm = user.get_udm_object(self._lo)
			# copy only those UDM properties from LDAP that were originally
			# set in self.udm_properties
			for k in self.udm_properties.keys():
				user.udm_properties[k] = user_udm[k]
			self.update(user)

		self.in_hook = True
		meth_name = "{}_{}".format(hook_time, func_name)
		try:
			for func in self._pyhook_cache.get(meth_name, []):
				self.logger.info("Running %s hook %s for %s...", meth_name, func, self)
				func(self)
		finally:
			self.in_hook = False

		try:
			self.hook_path = self.config['hooks_dir_legacy']
		except KeyError:
			pass
		return super(ImportUser, self).call_hooks(hook_time, func_name)

	def call_format_hook(self, prop_name, fields):
		if self._format_pyhook_cache is None:
			# load hooks
			path = self.config.get('hooks_dir_pyhook', self.pyhooks_base_path)
			pyloader = PyHooksLoader(path, FormatPyHook, self.logger)
			self.__class__._format_pyhook_cache = pyloader.get_hook_objects()

		res = fields
		for func in self._format_pyhook_cache.get('patch_fields_{}'.format(self.role_sting), []):
			if prop_name not in func.im_class.properties:
				# ignore properties not in Hook.properties
				continue
			self.logger.info(
				"Running patch_fields_%s hook %s for property name %r for user %s...",
				self.role_sting, func, prop_name, self)
			res = func(prop_name, res)
		return res

	def check_schools(self, lo):
		"""
		Verify that the "school" and "schools" attributes are correct.
		Check is case sensitive (Bug #42456).

		:param lo: LDAP connection object
		:return: None or raises UnkownSchoolName
		"""
		# cannot be done in run_checks, because it needs LDAP access
		schools = set(self.schools)
		schools.add(self.school)
		for school in schools:
			if school not in self.get_all_school_names(self._lo):
				raise UnkownSchoolName('School {!r} does not exist.'.format(school), input=self.input_data, entry_count=self.entry_count, import_user=self)

	def create(self, lo, validate=True):
		self._lo = lo
		self.check_schools(lo)
		if self.in_hook:
			# prevent recursion
			self.logger.warn("Running create() from within a hook.")
			return self.create_without_hooks(lo, validate)
		else:
			return super(ImportUser, self).create(lo, validate)

	@classmethod
	def get_ldap_filter_for_user_role(cls):
		if not cls.factory:
			cls.factory = Factory()
		# convert cmdline / config name to ucsschool.lib role(s)
		if not cls.config["user_role"]:
			roles = ()
		elif cls.config["user_role"] == 'student':
			roles = (role_pupil,)
		elif cls.config["user_role"] == 'teacher_and_staff':
			roles = (role_teacher, role_staff)
		else:
			roles = (cls.config["user_role"],)
		a_user = cls.factory.make_import_user(roles)
		return a_user.type_filter

	@classmethod
	def get_by_import_id(cls, connection, source_uid, record_uid, superordinate=None):
		"""
		Retrieve an ImportUser.

		:param connection: uldap object
		:param source_uid: str: source DB identifier
		:param record_uid: str: source record identifier
		:param superordinate: str: superordinate
		:return: object of ImportUser subclass from LDAP or raises noObject
		"""
		oc_filter = cls.get_ldap_filter_for_user_role()
		filter_s = filter_format(
			"(&{}(ucsschoolSourceUID=%s)(ucsschoolRecordUID=%s))".format(oc_filter),
			(source_uid, record_uid)
		)
		obj = cls.get_only_udm_obj(connection, filter_s, superordinate=superordinate)
		if not obj:
			raise noObject("No {} with source_uid={!r} and record_uid={!r} found.".format(
				cls.config.get("user_role", "user"), source_uid, record_uid))
		return cls.from_udm_obj(obj, None, connection)

	def deactivate(self):
		"""
		Deactivate user account. Caller must run modify().
		"""
		self.disabled = "all"

	def expire(self, expiry):
		"""
		Set the account expiration date. Caller must run modify().

		:param expiry: str: expire date "%Y-%m-%d" or ""
		"""
		self._userexpiry = expiry

	@classmethod
	def from_dict(cls, a_dict):
		assert isinstance(a_dict, dict)
		user_dict = a_dict.copy()
		for attr in ("$dn$", "objectType", "type", "type_name"):
			# those should be generated upon creation
			try:
				del user_dict[attr]
			except KeyError:
				pass
		roles = user_dict.pop("roles", [])
		if not cls.factory:
			cls.factory = Factory()
		return cls.factory.make_import_user(roles, **user_dict)

	def _alter_udm_obj(self, udm_obj):
		self._prevent_mapped_attributes_in_udm_properties()
		super(ImportUser, self)._alter_udm_obj(udm_obj)
		if self._userexpiry is not None:
			udm_obj["userexpiry"] = self._userexpiry
		if self._purge_ts is not None:
			udm_obj["ucsschoolPurgeTimestamp"] = self._purge_ts

		for property_, value in (self.udm_properties or {}).items():
			try:
				if property_ in self.no_overwrite_attributes and udm_obj[property_]:
					# don't overwrite attributes in ucsschool/import/generate/user/attributes/no-overwrite
					continue
				udm_obj[property_] = value
			except (KeyError, noProperty) as exc:
				raise UnknownProperty(
					"UDM property '{}' could not be set: {}".format(property_, exc),
					entry_count=self.entry_count,
					import_user=self
				)
			except (valueError, valueInvalidSyntax) as exc:
				raise UDMValueError(
					"UDM property '{}' could not be set: {}".format(property_, exc),
					entry_count=self.entry_count,
					import_user=self
				)
			except Exception as exc:
				self.logger.error(
					"Unexpected exception caught: UDM property %r could not be set for user %r in import line %r: exception: %s\n%s",
					property_, self.name, self.entry_count, exc, traceback.format_exc()
				)
				raise UDMError(
					"UDM property {!r} could not be set: {}".format(property_, exc),
					entry_count=self.entry_count,
					import_user=self
				)

	@classmethod
	def get_all_school_names(cls, lo):
		if not cls._all_school_names:
			cls._all_school_names = [s.name for s in School.get_all(lo)]
		return cls._all_school_names

	def has_purge_timestamp(self, connection):
		"""
		Check if the user account has a purge timestamp set (regardless if it is
		in the future or past).

		:param connection: uldap connection object
		:return: bool: whether the user account has a purge timestamp set
		"""
		user_udm = self.get_udm_object(connection)
		return bool(user_udm["ucsschoolPurgeTimestamp"])

	def has_expired(self, connection):
		"""
		Check if the user account has expired.

		:param connection: uldap connection object
		:return: bool: whether the user account has expired
		"""
		user_udm = self.get_udm_object(connection)
		if not user_udm["userexpiry"]:
			return False
		expiry = datetime.datetime.strptime(user_udm["userexpiry"], "%Y-%m-%d")
		return datetime.datetime.now() > expiry

	def has_expiry(self, connection):
		"""
		Check if the user account has an expiry date set (regardless if it is
		in the future or past).

		:param connection: uldap connection object
		:return: bool: whether the user account has an expiry date set
		"""
		user_udm = self.get_udm_object(connection)
		return bool(user_udm["userexpiry"])

	def prepare_all(self, new_user=False):
		"""
		Necessary preparation to modify a user in UCS.
		Runs all make_* functions.

		:param new_user: bool: if username and password should be created
		"""
		self.prepare_uids()
		self.prepare_udm_properties()
		self.prepare_attributes(new_user)
		self.run_checks(check_username=new_user)

	def prepare_attributes(self, new_user=False):
		"""
		Run make_* functions for all Attributes of ucsschool.lib.models.user.User.
		:param new_user:
		:return:
		"""
		self.make_firstname()
		self.make_lastname()
		self.make_school()
		self.make_schools()
		self.make_username()
		if new_user:
			self.make_password()
		if self.password:
			self.udm_properties["overridePWHistory"] = "1"
			self.udm_properties["overridePWLength"] = "1"
		self.make_classes()
		self.make_birthday()
		self.make_disabled()
		self.make_email()

	def prepare_udm_properties(self):
		"""
		Create self.udm_properties from schemes configured in config["scheme"].
		Existing entries will be overwritten unless listed in UCRV
		ucsschool/import/generate/user/attributes/no-overwrite.

		* Attributes (email, record_uid, [user]name etc.) are ignored, as they are
		processed separately in make_*.
		* See /usr/share/doc/ucs-school-import/user_import_configuration_readme.txt.gz
		section "scheme" for details on the configuration.
		"""
		ignore_keys = self.to_dict().keys()
		ignore_keys.extend(["mailPrimaryAddress", "recordUID", "username"])  # these are used in make_*
		for k, v in self.config["scheme"].items():
			if k in ignore_keys:
				continue
			self.udm_properties[k] = self.format_from_scheme(k, v)

	def prepare_uids(self):
		"""
		Necessary preparation to detect if user exists in UCS.
		Runs make_* functions for record_uid and source_uid Attributes of
		ImportUser.
		"""
		self.make_recordUID()
		self.make_sourceUID()

	def make_birthday(self):
		"""
		Set User.birthday attribute.
		"""
		if "birthday" in self.config["scheme"]:
			self.birthday = self.format_from_scheme("birthday", self.config["scheme"]["birthday"])

	def make_classes(self):
		"""
		Create school classes.

		* This should run after make_school().
		* If attribute already exists as a dict, it is not changed.
		* Attribute is only written if it is set to a string like
		'school1-cls2,school3-cls4'.
		"""
		if isinstance(self, Staff):
			self.school_classes = dict()
		elif isinstance(self.school_classes, dict):
			pass
		elif isinstance(self.school_classes, basestring):
			res = defaultdict(list)
			self.school_classes = self.school_classes.strip(" \n\r\t,")
			for a_class in [klass.strip() for klass in self.school_classes.split(",") if klass.strip()]:
				school, sep, cls_name = [x.strip() for x in a_class.partition("-")]
				if sep and not cls_name:
					raise InvalidClassName("Empty class name.")
				if not sep:
					# no school prefix
					if not self.school:
						self.make_school()
					cls_name = school
					school = self.school
				cls_name = self.normalize(cls_name)
				school = self.normalize(school)
				klass_name = "{}-{}".format(school, cls_name)
				if klass_name not in res[school]:
					res[school].append(klass_name)
			self.school_classes = dict(res)
		elif self.school_classes is None:
			self.school_classes = dict()
		else:
			raise RuntimeError("Unknown data in attribute 'school_classes': '{}'".format(self.school_classes))

	def make_disabled(self):
		"""
		Set User.disabled attribute.
		"""
		if self.disabled is not None:
			return

		try:
			activate = self.config["activate_new_users"][self.role_sting]
		except KeyError:
			try:
				activate = self.config["activate_new_users"]["default"]
			except KeyError:
				raise UnkownDisabledSetting(
					"Cannot find 'disabled' ('activate_new_users') setting for role '{}' or 'default'.".format(
						self.role_sting),
					self.entry_count,
					import_user=self)
		self.disabled = "none" if activate else "all"

	def make_firstname(self):
		"""
		Normalize given name if set from import data or create from scheme.
		"""
		if self.firstname:
			self.firstname = self.normalize(self.firstname)
		elif "firstname" in self.config["scheme"]:
			self.firstname = self.format_from_scheme("firstname", self.config["scheme"]["firstname"])
		else:
			self.firstname = ""

	def make_lastname(self):
		"""
		Normalize family name if set from import data or create from scheme.
		"""
		if self.lastname:
			self.lastname = self.normalize(self.lastname)
		elif "lastname" in self.config["scheme"]:
			self.lastname = self.format_from_scheme("lastname", self.config["scheme"]["lastname"])
		else:
			self.lastname = ""

	def make_email(self):
		"""
		Create email from scheme (if not already set).

		If any of the other attributes is used in the format scheme of the
		email address, its make_* function should have run before this!
		"""
		if self.email:
			return
		try:
			self.email = self.udm_properties.pop("mailPrimaryAddress")
			if self.email:
				return
		except KeyError:
			pass

		maildomain = self.config.get("maildomain")
		if not maildomain:
			try:
				maildomain = self.ucr["mail/hosteddomains"].split()[0]
			except (AttributeError, IndexError):
				if "email" in self.config["mandatory_attributes"] or "mailPrimaryAttribute" in self.config["mandatory_attributes"]:
					raise MissingMailDomain(
						"Could not retrieve mail domain from configuration nor from UCRV mail/hosteddomains.",
						entry_count=self.entry_count,
						import_user=self)
				else:
					return
		self.email = self.format_from_scheme("email", self.config["scheme"]["email"], maildomain=maildomain).lower()
		if not self.unique_email_handler:
			self.__class__.unique_email_handler = self.factory.make_unique_email_handler(dry_run=self.config['dry_run'])
		try:
			self.email = self.unique_email_handler.format_name(self.email)
		except EmptyFormatResultError:
			if 'email' in self.config['mandatory_attributes'] or 'mailPrimaryAttribute' in self.config['mandatory_attributes']:
				raise
			else:
				self.email = ''

	def make_password(self):
		"""
		Create random password (if not already set).
		"""
		if not self.password:
			self.password = create_passwd(self.config["password_length"])

	def make_recordUID(self):
		"""
		Create ucsschoolRecordUID (recordUID) (if not already set).
		"""
		if not self.record_uid:
			self.record_uid = self.format_from_scheme("recordUID", self.config["scheme"]["recordUID"])

	def make_sourceUID(self):
		"""
		Set the ucsschoolSourceUID (sourceUID) (if not already set).
		"""
		if self.source_uid:
			if self.source_uid != self.config["sourceUID"]:
				raise NotSupportedError("Source_uid '{}' differs to configured source_uid '{}'.".format(
					self.source_uid, self.config["sourceUID"]))
		else:
			self.source_uid = self.config["sourceUID"]

	def make_school(self):
		"""
		Create 'school' attribute - the position of the object in LDAP (if not already set).

		Order of detection:
		* already set (object creation or reading from input)
		* from configuration (file or cmdline)
		* first (alphanum-sorted) school in attribute schools
		"""
		if self.school:
			self.school = self.normalize(self.school)
		elif self.config.get("school"):
			self.school = self.config["school"]
		elif self.schools and isinstance(self.schools, list):
			self.school = self.normalize(sorted(self.schools)[0])
		elif self.schools and isinstance(self.schools, basestring):
			self.make_schools()  # this will recurse back, but schools will be a list then
		else:
			raise MissingSchoolName(
				"Primary school name (ou) was not set on the cmdline or in the configuration file and was not found in "
				"the input data.",
				entry_count=self.entry_count,
				import_user=self)

	def make_schools(self):
		"""
		Create list of schools this user is in.
		If possible, this should run after make_school()

		* If empty, it is set to self.school.
		* If it is a string like 'school1,school2,school3' the attribute is
		created from it.
		"""
		if self.schools and isinstance(self.schools, list):
			pass
		elif not self.schools:
			if not self.school:
				self.make_school()
			self.schools = [self.school]
		elif isinstance(self.schools, basestring):
			self.schools = self.schools.strip(",").split(",")
			self.schools = sorted([self.normalize(s.strip()) for s in self.schools])
		else:
			raise RuntimeError("Unknown data in attribute 'schools': '{}'".format(self.schools))

		if not self.school:
			self.make_school()
		if self.school not in self.schools:
			if not self.schools:
				self.schools = [self.school]
			else:
				self.school = sorted(self.schools)[0]

	def make_username(self):
		"""
		Create username if not already set in self.name or self.udm_properties["username"].
		[ALWAYSCOUNTER] and [COUNTER2] are supported, but only one may be used
		per name.
		"""
		if self.name:
			return
		try:
			self.name = self.udm_properties.pop("username")
			if self.name:
				return
		except KeyError:
			pass
		if self.old_user:
			self.name = self.old_user.name
			return

		self.name = self.format_from_scheme("username", self.username_scheme)
		if not self.name:
			raise EmptyFormatResultError("No username was created from scheme '{}'.".format(
				self.username_scheme), self.username_scheme, self.to_dict())
		if not self.username_handler:
			self.__class__.username_handler = self.factory.make_username_handler(self.username_max_length, self.config['dry_run'])
		self.name = self.username_handler.format_name(self.name)

	def modify(self, lo, validate=True, move_if_necessary=None):
		self._lo = lo
		self.check_schools(lo)
		if self.in_hook:
			# prevent recursion
			self.logger.warn("Running modify() from within a hook.")
			return self.modify_without_hooks(lo, validate, move_if_necessary)
		else:
			return super(ImportUser, self).modify(lo, validate, move_if_necessary)

	def modify_without_hooks(self, lo, validate=True, move_if_necessary=None):
		if not self.school_classes:
			# empty classes input means: don't change existing classes (Bug #42288)
			self.logger.debug("No school_classes are set, not modifying existing ones.")
			udm_obj = self.get_udm_object(lo)
			self.school_classes = self.get_school_classes(udm_obj, self)
		return super(ImportUser, self).modify_without_hooks(lo, validate, move_if_necessary)

	def move(self, lo, udm_obj=None, force=False):
		self._lo = lo
		self.check_schools(lo)
		return super(ImportUser, self).move(lo, udm_obj, force)

	@classmethod
	def normalize(cls, s):
		"""
		Normalize string (german umlauts etc)

		:param s: str
		:return: str: normalized s
		"""
		if isinstance(s, basestring):
			s = cls.prop._replace("<:umlauts>{}".format(s), {})
		return s

	def normalize_udm_properties(self):
		"""
		Normalize data in self.udm_properties.
		"""
		def normalize_recursive(item):
			if isinstance(item, dict):
				for k, v in item.items():
					item[k] = normalize_recursive(v)
				return item
			elif isinstance(item, list):
				for part in item:
					normalize_recursive(part)
				return item
			else:
				return ImportUser.normalize(item)

		for k, v in self.udm_properties.items():
			self.udm_properties[k] = normalize_recursive(v)

	def reactivate(self):
		"""
		Reactivate a deactivated user account, reset the account expiry
		setting and purge timestamp. Run this only on existing users fetched
		from LDAP.
		"""
		self.expire("")
		self.disabled = "none"
		self.set_purge_timestamp("")

	def remove(self, lo):
		self._lo = lo
		return super(ImportUser, self).remove(lo)

	def run_checks(self, check_username=False):
		"""
		Run some self-tests.

		:param check_username: bool: if username and password checks should run
		"""
		try:
			[self.udm_properties.get(ma) or getattr(self, ma) for ma in self.config["mandatory_attributes"]]
		except (AttributeError, KeyError) as exc:
			raise MissingMandatoryAttribute("A mandatory attribute was not set: {}.".format(exc), self.config["mandatory_attributes"], entry_count=self.entry_count, import_user=self)

		if self.record_uid in self._unique_ids["recordUID"]:
			raise UniqueIdError("RecordUID '{}' has already been used in this import.".format(self.record_uid), entry_count=self.entry_count, import_user=self)
		self._unique_ids["recordUID"].add(self.record_uid)

		if check_username:
			if not self.name:
				raise NoUsername("No username was created.", entry_count=self.entry_count, import_user=self)

			if len(self.name) > self.username_max_length:
				raise UsernameToLong("Username '{}' is longer than allowed.".format(self.name), entry_count=self.entry_count, import_user=self)

			if self.name in self._unique_ids["name"]:
				raise UniqueIdError("Username '{}' has already been used in this import.".format(self.name), entry_count=self.entry_count, import_user=self)
			self._unique_ids["name"].add(self.name)

			if len(self.password) < self.config["password_length"]:
				raise BadPassword("Password is shorter than {} characters.".format(self.config["password_length"]), entry_count=self.entry_count, import_user=self)

		if self.email:
			# email_pattern:
			# * must not begin with an @
			# * must have >=1 '@' (yes, more than 1 is allowed)
			# * domain must contain dot
			# * all characters are allowed (international domains)
			email_pattern = r"[^@]+@.+\..+"
			if not re.match(email_pattern, self.email):
				raise InvalidEmail("Email address '{}' has invalid format.".format(self.email), entry_count=self.entry_count, import_user=self)

			if self.email in self._unique_ids["email"]:
				raise UniqueIdError("Email address '{}' has already been used in this import.".format(self.email), entry_count=self.entry_count, import_user=self)
			self._unique_ids["email"].add(self.email)

		if self.birthday:
			try:
				datetime.datetime.strptime(self.birthday, "%Y-%m-%d")
			except ValueError as exc:
				raise InvalidBirthday("Birthday has invalid format: {}.".format(exc), entry_count=self.entry_count, import_user=self)

	def set_purge_timestamp(self, ts):
		self._purge_ts = ts

	@property
	def role_sting(self):
		"""
		Mapping from self.roles to string used in configuration.

		:return: str: one of staff, student, teacher, teacher_and_staff
		"""
		if role_pupil in self.roles:
			return "student"
		elif role_teacher in self.roles:
			if role_staff in self.roles:
				return "teacher_and_staff"
			else:
				return "teacher"
		else:
			return "staff"

	@property
	def school_classes_as_str(self):
		return ','.join(','.join(sc) for sc in self.school_classes.values())

	@property
	def username_scheme(self):
		"""
		Fetch scheme for username for role.

		:return: str: scheme for the role from configuration
		"""
		try:
			scheme = unicode(self.config["scheme"]["username"][self.role_sting])
		except KeyError:
			try:
				scheme = unicode(self.config["scheme"]["username"]["default"])
			except KeyError:
				raise NoUsernameAtAll("Cannot find scheme to create username for role '{}' or 'default'.".format(
					self.role_sting), self.entry_count, import_user=self)
		# force transcription of german umlauts
		return "<:umlauts>{}".format(scheme)

	def format_from_scheme(self, prop_name, scheme, **kwargs):
		"""
		Format property with scheme for current import_user.
		* Uses the replacement code from users:templates.
		* This does not do the counter variable replacements for username.
		* Replacement <variables> are filled in the following oder (later
		additions overwriting previous ones):
		- from raw input data
		- from Attributes of self (ImportUser & ucsschool.lib.models.user.User)
		- from self.udm_properties
		- from kwargs

		:param prop_name: str: name of property to be formatted
		:param scheme: str: scheme to use
		:param kwargs: dict: additional data to use for formatting
		:return: str: formatted string
		"""
		if self.input_data:
			all_fields = self.reader.get_data_mapping(self.input_data)
		else:
			all_fields = dict()
		all_fields.update(self.to_dict())
		all_fields.update(self.udm_properties)
		if "username" not in all_fields:
			all_fields["username"] = all_fields["name"]
		all_fields.update(kwargs)
		all_fields = self.call_format_hook(prop_name, all_fields)

		res = self.prop._replace(scheme, all_fields)
		if not res:
			self.logger.warn("Created empty '{prop_name}' from scheme '{scheme}' and input data {data}. ".format(
				prop_name=prop_name, scheme=scheme, data=all_fields))
		return res

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		"""
		IMPLEMENTME if you subclass!
		"""
		klass = super(ImportUser, cls).get_class_for_udm_obj(udm_obj, school)
		if issubclass(klass, TeachersAndStaff):
			return ImportTeachersAndStaff
		elif issubclass(klass, Teacher):
			return ImportTeacher
		elif issubclass(klass, Staff):
			return ImportStaff
		elif issubclass(klass, Student):
			return ImportStudent
		else:
			return None

	def get_school_class_objs(self):
		if isinstance(self.school_classes, basestring):
			# school_classes was set from input data
			self.make_classes()
		return super(ImportUser, self).get_school_class_objs()

	def _prevent_mapped_attributes_in_udm_properties(self):
		"""
		Make sure users do not store values for ucsschool.lib mapped Attributes
		in udm_properties.
		"""
		if not self.udm_properties:
			return

		bad_props = set(self.udm_properties.keys()).intersection(self.attribute_udm_names)
		if bad_props:
			raise NotSupportedError(
				"UDM properties '{}' must be set as attributes of the {} object (not in udm_properties).".format(
					"', '".join(bad_props), self.__class__.__name__)
			)
		if "e-mail" in self.udm_properties.keys() and not self.email:
			# this might be an mistake, so let's warn the user
			self.logger.warn(
				"UDM property 'e-mail' is used for storing contact information. The users mailbox address is stored in "
				"the 'email' attribute of the {} object (not in udm_properties).".format(self.__class__.__name__))

	def to_dict(self):
		res = super(ImportUser, self).to_dict()
		for attr in self._additional_props:
			res[attr] = getattr(self, attr)
		return res

	def update(self, other):
		"""
		Copy attributes of other ImportUser into this one.

		IMPLEMENTME if you subclass and add attributes that are not
		ucsschool.lib.models.attributes.
		:param other: ImportUser: data source
		"""
		for k, v in other.to_dict().items():
			if (k == "name" or k in self._additional_props) and not v:
				continue
			setattr(self, k, v)

	@property
	def username_max_length(self):
		try:
			res = self.config['username']['max_length'][self.role_sting]
		except KeyError:
			res = self.default_username_max_length
		return res


class ImportStaff(ImportUser, Staff):
	pass


class ImportStudent(ImportUser, Student):
	default_username_max_length = 20 - len(ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-"))


class ImportTeacher(ImportUser, Teacher):
	pass


class ImportTeachersAndStaff(ImportUser, TeachersAndStaff):
	pass
