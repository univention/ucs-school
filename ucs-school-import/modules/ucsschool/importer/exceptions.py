# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2018 Univention GmbH
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

"""
All exceptions raised by code in ucsschool.importer.
"""


class UcsSchoolImportError(Exception):
	is_fatal = False
	# If is_countable is set to False, the exception is displayed to
	# the user, but is not included in the evaluation of tolerate_errors.
	is_countable = True

	def __init__(self, *args, **kwargs):
		self.entry_count = kwargs.pop("entry_count", 0)
		self.input = kwargs.pop("input", None)
		self.import_user = kwargs.pop("import_user", None)
		super(UcsSchoolImportError, self).__init__(*args, **kwargs)


class UcsSchoolImportFatalError(UcsSchoolImportError):
	is_fatal = True


class UcsSchoolImportSkipImportRecord(UcsSchoolImportError):
	is_countable = False


class BadPassword(UcsSchoolImportError):
	pass


class BadValueStored(UcsSchoolImportFatalError):
	pass


class ConfigurationError(UcsSchoolImportFatalError):
	pass


class CreationError(UcsSchoolImportError):
	pass


class DeletionError(UcsSchoolImportError):
	pass


class FormatError(UcsSchoolImportError):

	def __init__(self, msg, scheme, data, *args, **kwargs):
		super(FormatError, self).__init__(msg, *args, **kwargs)
		self.scheme = scheme
		self.data = data


class EmptyFormatResultError(FormatError):
	pass


class InitialisationError(UcsSchoolImportFatalError):
	pass


class InvalidBirthday(UcsSchoolImportError):
	pass


class InvalidClassName(UcsSchoolImportError):
	pass


class InvalidEmail(UcsSchoolImportError):
	pass


class InvalidSchoolClasses(UcsSchoolImportError):
	pass


class InvalidSchools(UcsSchoolImportError):
	pass


class LDAPWriteAccessDenied(UcsSchoolImportFatalError):
	def __init__(self, msg=None, *args, **kwargs):
		msg = msg or 'Tried to write using a read only connection (during a dry-run?).'
		super(LDAPWriteAccessDenied, self).__init__(msg, *args, **kwargs)


class MissingMandatoryAttribute(UcsSchoolImportError):

	def __init__(self, msg, mandatory_attributes, *args, **kwargs):
		super(MissingMandatoryAttribute, self).__init__(msg, *args, **kwargs)
		self.mandatory_attributes = mandatory_attributes


class MissingMailDomain(UcsSchoolImportError):
	pass


class MissingSchoolName(UcsSchoolImportError):
	pass


class MissingUid(UcsSchoolImportError):
	pass


class ModificationError(UcsSchoolImportError):
	pass


class MoveError(UcsSchoolImportError):
	pass


class NameKeyExists(UcsSchoolImportFatalError):
	pass


class NoRole(UcsSchoolImportError):
	pass


class NotSupportedError(UcsSchoolImportError):
	pass


NoUsername = MissingUid


class NoUsernameAtAll(UcsSchoolImportFatalError):
	pass


class NoValueStored(UcsSchoolImportFatalError):
	pass


class ReadOnlyConfiguration(UcsSchoolImportFatalError):

	def __init__(self, *args, **kwargs):
		super(ReadOnlyConfiguration, self).__init__("Changing the configuration is not allowed.", *args, **kwargs)


class TooManyErrors(UcsSchoolImportFatalError):

	def __init__(self, msg, errors, *args, **kwargs):
		super(TooManyErrors, self).__init__(msg, *args, **kwargs)
		self.errors = errors


ToManyErrors = TooManyErrors


class UDMError(UcsSchoolImportError):
	pass


class UDMValueError(UDMError):
	pass


class UnknownAction(UcsSchoolImportError):
	pass


UnkownAction = UnknownAction


class UnknownDisabledSetting(UcsSchoolImportError):
	pass


UnkownDisabledSetting = UnknownDisabledSetting


class UnknownProperty(UcsSchoolImportError):
	pass


class UnknownRole(UcsSchoolImportError):
	pass


UnkownRole = UnknownRole


class UnknownSchoolName(UcsSchoolImportError):
	pass


UnkownSchoolName = UnknownSchoolName


class UniqueIdError(UcsSchoolImportError):
	pass


class UsernameKeyExists(NameKeyExists):
	"""
	Deprecated. Please use NameKeyExists.
	"""
	pass


class UsernameToLong(UcsSchoolImportError):
	pass


class UserValidationError(UcsSchoolImportError):
	"""
	Wraps ucsschool.lib.models.attributes.ValidationError
	"""

	def __init__(self, msg, validation_error, *args, **kwargs):
		super(UserValidationError, self).__init__(msg, *args, **kwargs)
		self.validation_error = validation_error


class WrongUserType(UcsSchoolImportError):
	"""Wraps ucsschool.lib.models.base.WrongObjectType"""
	def __init__(self, msg, *args, **kwargs):
		super(WrongUserType, self).__init__(msg, *args, **kwargs)
