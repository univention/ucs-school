# -*- coding: utf-8 -*-
#
# Univention UCS@School
"""
All exceptions raise by code in ucsschool.importer.
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


class UcsSchoolImportError(Exception):
	is_fatal = False

	def __init__(self, *args, **kwargs):
		self.entry = kwargs.pop("entry", 0)
		self.input = kwargs.pop("input", None)
		self.import_user = kwargs.pop("import_user", None)
		super(UcsSchoolImportError, self).__init__(*args, **kwargs)


class UcsSchoolImportFatalError(UcsSchoolImportError):
	is_fatal = True


class BadPassword(UcsSchoolImportError):
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


class InitialisationError(UcsSchoolImportFatalError):
	pass


class InvalidBirthday(UcsSchoolImportError):
	pass


class InvalidClassName(UcsSchoolImportError):
	pass


class InvalidEmail(UcsSchoolImportError):
	pass


class LookupError(UcsSchoolImportError):
	pass


class MissingMandatoryAttribute(UcsSchoolImportError):
	def __init__(self, msg, mandatory_attributes, *args, **kwargs):
		super(MissingMandatoryAttribute, self).__init__(msg, *args, **kwargs)
		self.mandatory_attributes = mandatory_attributes


class MissingMailDomain(UcsSchoolImportError):
	pass


class MissingSchoolName(UcsSchoolImportError):
	pass


class ModificationError(UcsSchoolImportError):
	pass


class NotSupportedError(UcsSchoolImportError):
	pass


class NoUsername(UcsSchoolImportError):
	pass


class NoUsernameAtAll(UcsSchoolImportFatalError):
	pass


class ReadOnlyConfiguration(UcsSchoolImportFatalError):
	def __init__(self, *args, **kwargs):
		super(ReadOnlyConfiguration, self).__init__("Changing the configuration is not allowed.", *args, **kwargs)


class ToManyErrors(UcsSchoolImportFatalError):
	def __init__(self, msg, errors, *args, **kwargs):
		super(ToManyErrors, self).__init__(msg, *args, **kwargs)
		self.errors = errors


class UnkownAction(UcsSchoolImportError):
	pass


class UnknownDeleteSetting(UcsSchoolImportError):
	pass


class UnkownDisabledSetting(UcsSchoolImportError):
	pass


class UnknownProperty(UcsSchoolImportError):
	pass


class UnkownRole(UcsSchoolImportError):
	pass


class UniqueIdError(UcsSchoolImportError):
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
