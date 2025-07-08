#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# SPDX-FileCopyrightText: 2016-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""All exceptions raised by code in ucsschool.importer."""


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


class ComputerImportError(Exception):
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


class EmptyMandatoryAttribute(UcsSchoolImportError):
    def __init__(self, msg, attr_name, *args, **kwargs):
        super(EmptyMandatoryAttribute, self).__init__(msg, *args, **kwargs)
        self.attr_name = attr_name


class InitialisationError(UcsSchoolImportFatalError):
    def __init__(self, msg, log_traceback=True, *args, **kwargs):
        super(InitialisationError, self).__init__(msg, *args, **kwargs)
        self.log_traceback = log_traceback


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


class InvalidLegalWard(UcsSchoolImportError):
    pass


class InvalidLegalGuardian(UcsSchoolImportError):
    pass


class LDAPWriteAccessDenied(UcsSchoolImportFatalError):
    def __init__(self, msg=None, *args, **kwargs):
        msg = msg or "Tried to write using a read only connection (during a dry-run?)."
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


class NoUsernameAtAll(UcsSchoolImportFatalError):
    pass


class NoValueStored(UcsSchoolImportFatalError):
    pass


class ReadOnlyConfiguration(UcsSchoolImportFatalError):
    def __init__(self, *args, **kwargs):
        super(ReadOnlyConfiguration, self).__init__(
            "Changing the configuration is not allowed.", *args, **kwargs
        )


class TooManyErrors(UcsSchoolImportFatalError):
    def __init__(self, msg, errors, *args, **kwargs):
        super(TooManyErrors, self).__init__(msg, *args, **kwargs)
        self.errors = errors


class UDMError(UcsSchoolImportError):
    pass


class UDMValueError(UDMError):
    pass


class UnknownAction(UcsSchoolImportError):
    pass


class UnknownDisabledSetting(UcsSchoolImportError):
    pass


class UnknownProperty(UcsSchoolImportError):
    pass


class UnknownRole(UcsSchoolImportError):
    pass


class UnknownSchoolName(UcsSchoolImportError):
    pass


class UniqueIdError(UcsSchoolImportError):
    pass


class UsernameToLong(UcsSchoolImportError):
    pass


class UserValidationError(UcsSchoolImportError):
    """Wraps ucsschool.lib.models.attributes.ValidationError"""

    def __init__(self, msg, validation_error, *args, **kwargs):
        super(UserValidationError, self).__init__(msg, *args, **kwargs)
        self.validation_error = validation_error

    def __str__(self):
        return "{} {!r}".format(self.args[0], self.validation_error)


class WrongUserType(UcsSchoolImportError):
    """Wraps ucsschool.lib.models.base.WrongObjectType"""

    def __init__(self, msg, *args, **kwargs):
        super(WrongUserType, self).__init__(msg, *args, **kwargs)
