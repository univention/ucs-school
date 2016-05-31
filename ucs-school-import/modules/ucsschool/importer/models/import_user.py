# -*- coding: utf-8 -*-
#
# Univention UCS@School
"""
Representation of a user read from a file.
"""
# Copyright 2016 Univention GmbH
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


import random
import re
import string
import datetime
from collections import defaultdict

from univention.admin import property as uadmin_property
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from ucsschool.lib.models import Staff, Student, Teacher, TeachersAndStaff, User
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.factory import Factory
from ucsschool.importer.exceptions import BadPassword, FormatError, InvalidBirthday, InvalidEmail, MissingMailDomain, MissingMandatoryAttribute, MissingSchoolName, NoUsername, NoUsernameAtAll, UniqueIdError, UnkownDisabledSetting, UnknownProperty, UsernameToLong


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
	config = None
	username_max_length = 15
	_unique_ids = defaultdict(set)
	factory = None
	ucr = None
	username_handler = None

	def __init__(self, name=None, school=None, **kwargs):
		self.action = None
		self.entry_count = -1
		self.udm_properties = dict()
		if not self.factory:
			self.factory = Factory()
			self.ucr = self.factory.make_ucr()
			self.config = Configuration()
		super(ImportUser, self).__init__(name, school, **kwargs)

	def deactivate(self):
		"""
		Deactive user account.
		"""
		self.disabled = "all"

	def expire(self, connection, expiry):
		"""
		Set the account expiration date.

		:param connection: uldap connection object
		:param expiry: str: expire date "%Y-%m-%d" or ""
		"""
		user_udm = self.get_udm_object(connection)
		user_udm["userexpiry"] = expiry
		user_udm.modify()
		# This operation partly invalidates the cached ucsschool.lib User:
		# setting the 'disabled' attribute after this would raise an ldapError.
		# Invalidating cache:
		self._udm_obj_searched = False

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

	def prepare_uids(self):
		"""
		Necessary preparation to detect if user exists in UCS.
		"""
		self.make_rid()
		self.make_sid()

	def prepare_properties(self, new_user=False):
		"""
		Necessary preparation to modify a user in UCS.

		:param new_user: bool: if new_user() should run
		"""
		self.prepare_uids()
		if new_user:
			self.make_username()
			self.make_password()
		self.make_school()
		self.make_schools()
		self.make_classes()
		self.make_email(make_username=new_user)
		self.make_firstname()
		self.make_lastname()
		self.make_birthday()
		self.make_disabled()
		# self.normalize_udm_properties()
		self.run_checks(check_username=new_user)

	def make_birthday(self):
		"""
		Set User.birthday attribute.
		"""
		pass

	def make_classes(self):
		"""
		Create school classes.
		"""
		# FIXME when/if self.school_class becomes a list instead of a string
		# if self.school_class and isinstance(self.school_class, basestring):
		# 	self.school_class = [c.strip() for c in self.school_class.split(",")]
		if isinstance(self, Staff):
			return

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
				raise UnkownDisabledSetting("Cannot find 'disabled' ('activate_new_users') setting for role '{}' or "
					"'default'.".format(self.role_sting), self.entry_count, import_user=self)
		self.disabled = "none" if activate else "all"

	def make_firstname(self):
		"""
		Normalize given name.
		"""
		self.firstname = self.normalize(self.firstname or "")

	def make_lastname(self):
		"""
		Normalize family name.
		"""
		self.lastname = self.normalize(self.lastname or "")

	def make_email(self, make_username=False):
		"""
		Create email (if not already set).

		:param make_username: bool: if make_username() should run
		"""
		if not self.email:
			maildomain = self.config.get("maildomain")
			if not maildomain:
				try:
					maildomain = self.ucr["mail/hosteddomains"].split()[0]
				except (AttributeError, IndexError):
					raise MissingMailDomain("Could not retrieve mail domain from configuration nor from UCRV "
						"mail/hosteddomains.", entry=self.entry_count, import_user=self)
			if "<firstname>" in self.config["scheme"]["email"]:
				self.make_firstname()
			if "<lastname>" in self.config["scheme"]["email"]:
				self.make_lastname()
			if make_username and ("<username>" in self.config["scheme"]["email"] or
				"<name>" in self.config["scheme"]["email"]):
					self.make_username()
			self.email = self.format_from_scheme("email", self.config["scheme"]["email"], maildomain=maildomain).lower()

	def make_password(self):
		"""
		Create random password.
		"""
		pw = list(random.choice(string.lowercase))
		pw.append(random.choice(string.uppercase))
		pw.append(random.choice(string.digits))
		pw.append(random.choice(u"@#$%^&*-_+=[]{}|\:,.?/`~();"))
		pw.extend(random.choice(string.ascii_letters + string.digits + u"@#$%^&*-_+=[]{}|\:,.?/`~();")
			for _ in range(self.config["password_length"] - 4))
		random.shuffle(pw)
		self.password = u"".join(pw)

	def make_rid(self):
		"""
		Create ucsschoolRecordUID (rid).
		"""
		if not self.record_uid:
			self.record_uid = self.format_from_scheme("rid", self.config["scheme"]["rid"])

	def make_sid(self):
		"""
		Set the ucsschoolSourceUID (sid)
		"""
		if not self.source_uid:
			self.source_uid = self.config["sourceUID"]

	def make_school(self):
		"""
		Create 'school' attribute - the position of the object in LDAP.
		"""
		if self.school:
			return
		if self.config.get("school"):
			self.school = self.config["school"]
		else:
			raise MissingSchoolName("School name was not set on the cmdline or in the configuration file and was not "
				"found in the source data.", entry=self.entry_count, import_user=self)

	def make_schools(self):
		"""
		Create list of schools this user is in.
		This should run after make_school()
		"""
		if not self.school:
			self.make_school()
		if not isinstance(self.schools, list):
			self.schools = list()
		if self.school not in self.schools:
			self.schools.append(self.school)

	def make_username(self):
		"""
		Create username.
		[ALWAYSCOUNTER] and [COUNTER2] are supported, but only one may be used
		per name.
		"""
		if self.name:
			return
		try:
			self.name = self.udm_properties["username"]
			return
		except KeyError:
			pass
		self.name = self.format_from_scheme("username", self.username_scheme)
		if not self.username_handler:
			self.username_handler = self.factory.make_username_handler(self.username_max_length)
		self.name = self.username_handler.format_username(self.name)

	@staticmethod
	def normalize(s):
		"""
		Normalize string (german umlauts etc)

		:param s: str
		:return: str: normalized s
		"""
		if isinstance(s, basestring):
			prop = uadmin_property("_replace")
			s = prop._replace("<:umlauts>{}".format(s), {})
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

	def reactivate(self, connection):
		"""
		Reactivate a deactivated user account and reset the account expiry
		setting. Run this only on existing users fetched from LDAP.

		:param connection: uldap connection object
		"""
		self.expire(connection, "")
		self.disabled = "none"

	def run_checks(self, check_username=False):
		"""
		Run some self-tests.

		:param check_username: bool: if username and password checks should run
		"""
		try:
			[self.udm_properties.get(ma) or getattr(self, ma) for ma in self.config["mandatory_attributes"]]
		except (AttributeError, KeyError) as exc:
			raise MissingMandatoryAttribute("A mandatory attribute was not set: {}.".format(exc),
				self.config["mandatory_attributes"], entry=self.entry_count, import_user=self)


		if self.record_uid in self._unique_ids["rid"]:
			raise UniqueIdError("RecordUID '{}' has already been used in this import.".format(self.record_uid),
				entry=self.entry_count, import_user=self)
		self._unique_ids["rid"].add(self.record_uid)

		if check_username:
			if not self.name:
				raise NoUsername("No username was created.", entry=self.entry_count, import_user=self)

			if len(self.name) > self.username_max_length:
				raise UsernameToLong("Username '{}' is longer than allowed.".format(self.name),
					entry=self.entry_count, import_user=self)

			if self.name in self._unique_ids["name"]:
				raise UniqueIdError("Username '{}' has already been used in this import.".format(self.name),
					entry=self.entry_count, import_user=self)
			self._unique_ids["name"].add(self.name)

			if len(self.password) < self.config["password_length"]:
				raise BadPassword("Password is shorter than {} characters.".format(self.config["password_length"]),
					entry=self.entry_count, import_user=self)

		if self.email:
			# email_pattern:
			# * must not begin with an @
			# * must have >=1 '@' (yes, more than 1 is allowed)
			# * domain must contain dot
			# * all characters are allowed (international domains)
			email_pattern = r"[^@]+@.+\..+"
			if not re.match(email_pattern, self.email):
				raise InvalidEmail("Email address '{}' has invalid format.".format(self.email), entry=self.entry_count,
					import_user=self)

			if self.email in self._unique_ids["email"]:
				raise UniqueIdError("Email address '{}' has already been used in this import.".format(self.email),
					entry=self.entry_count, import_user=self)
			self._unique_ids["email"].add(self.email)

		if self.birthday:
			try:
				self.birthday = datetime.datetime.strptime(self.birthday, "%Y-%m-%d").isoformat()
			except ValueError as exc:
				raise InvalidBirthday("Birthday has invalid format: {}.".format(exc), entry=self.entry_count,
					import_user=self)

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

		:param prop_name: str: name of property (for error logging)
		:param scheme: str: scheme to use
		:param kwargs: dict: additional data to use for formatting
		:return: str: formatted string
		"""
		all_fields = self.to_dict().copy()
		all_fields.update(self.udm_properties)
		all_fields.update(kwargs)

		prop = uadmin_property("_replace")
		res = prop._replace(scheme, all_fields)
		if not res:
			raise FormatError("Could not create {prop_name} from scheme and input data. ".format(prop_name=prop_name),
				scheme=scheme, data=all_fields, entry=self.entry_count, import_user=self)
		return res

	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		raise NotImplementedError()

	def create_without_hooks(self, lo, validate):
		success = super(ImportUser, self).create_without_hooks(lo, validate)
		self.store_udm_properties(lo)
		return success

	def modify_without_hooks(self, lo, validate=True, move_if_necessary=None):
		success = super(ImportUser, self).modify_without_hooks(lo, validate, move_if_necessary)
		self.store_udm_properties(lo)
		return success

	def store_udm_properties(self, connection):
		"""
		Copy data from self.udm_properties into UDM object of this user.

		:param connection: LDAP connection
		"""
		if not self.udm_properties:
			return
		udm_obj = self.get_udm_object(connection)
		udm_obj.info.update(self.udm_properties)
		try:
			udm_obj.modify()
		except KeyError as exc:
			raise UnknownProperty("UDM properties could not be set. Unknown property: '{}'".format(exc),
				entry=self.entry_count, import_user=self)

	def update(self, other):
		"""
		Copy attributes of other ImportUser into this one.

		IMPLEMENTME if you subclass and add attributes that are not
		ucsschool.lib.models.attributes.
		:param other: ImportUser: data source
		"""
		for k, v in other.to_dict().items():
			if k == "name" and v is None:
				continue
			setattr(self, k, v)
		self.action = other.action
		self.entry_count = other.entry_count
		self.udm_properties.update(other.udm_properties)


class ImportStaff(ImportUser, Staff):
	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		return cls


class ImportStudent(ImportUser, Student):
	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		return cls


class ImportTeacher(ImportUser, Teacher):
	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		return cls


class ImportTeachersAndStaff(ImportUser, TeachersAndStaff):
	@classmethod
	def get_class_for_udm_obj(cls, udm_obj, school):
		return cls
