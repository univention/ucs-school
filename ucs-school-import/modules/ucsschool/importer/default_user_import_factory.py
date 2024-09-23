#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2024 Univention GmbH
#
# https://www.univention.de/
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

"""Default implementation of the Abstract Factory."""

import logging
from typing import TYPE_CHECKING, Any, Iterable, Optional, TypeVar  # noqa: F401

from ucsschool.lib.models.utils import ucr

from .exceptions import InitialisationError
from .factory import load_class

if TYPE_CHECKING:
    import ucsschool.importer.mass_import.mass_import.MassImport
    import ucsschool.importer.mass_import.user_import.UserImport
    import ucsschool.importer.reader.csv_reader.CsvReader
    import ucsschool.importer.utils.username_handler.EmailHandler
    import ucsschool.importer.utils.username_handler.UsernameHandler
    import ucsschool.importer.writer.csv_writer.CsvWriter
    import ucsschool.importer.writer.new_user_password_csv_exporter.NewUserPasswordCsvExporter
    import ucsschool.importer.writer.user_import_csv_result_exporter.UserImportCsvResultExporter  # noqa: F401,E501
    import univention.config_registry.ConfigRegistry  # noqa: F401

    from .models.import_user import ImportUser

    ImportUserTV = TypeVar("ImportUserTV", bound=ImportUser)


class DefaultUserImportFactory(object):
    """
    Default implementation of the Abstract Factory.

    Subclass this and store the fully dotted class name in `config["factory"]`
    to make the importer code use your classes.
    """

    def __init__(self):  # type: () -> None
        from .configuration import Configuration

        self.config = Configuration()
        self.logger = logging.getLogger(__name__)
        self.load_methods_from_config()

    @staticmethod
    def init_wrapper(klass):
        """
        This returns a function that tries to init a class with args and kwargs.
        If that does not work, it tries to do the same, but without any arguments.
        """

        def create_class(*args, **kwargs):
            try:
                return klass(*args, **kwargs)
            except TypeError:
                return klass()

        return create_class

    def load_methods_from_config(self):  # type: () -> None
        """
        Overwrite the methods in this class with constructors or methods from
        the configuration file.

        * Configuration keys in the configuration "classes" dict are the names of the methods here
            without the prepended ``make_``.
        * It will be checked if the configured classes are really subclasses as described in the
            documentation (/usr/share/doc/ucs-school-import/user_import_configuration_readme.txt).
        * Please update the documentation if classes/methods are added.
        * Take care to honor the signature of the methods, this cannot be checked.
        """
        classes = {
            "reader": "ucsschool.importer.reader.base_reader.BaseReader",
            "mass_importer": "ucsschool.importer.mass_import.mass_import.MassImport",
            "password_exporter": "ucsschool.importer.writer.result_exporter.ResultExporter",
            "result_exporter": "ucsschool.importer.writer.result_exporter.ResultExporter",
            "user_importer": "ucsschool.importer.mass_import.user_import.UserImport",
            "unique_email_handler": "ucsschool.importer.utils.username_handler.EmailHandler",
            "username_handler": "ucsschool.importer.utils.username_handler.UsernameHandler",
            "user_writer": "ucsschool.importer.writer.base_writer.BaseWriter",
        }
        methods = ["import_user"]

        for k, v in classes.items():
            if k not in self.config["classes"]:
                continue
            make_name = "make_{}".format(k)
            if not hasattr(self, make_name):
                self.logger.error("Configuration key 'classes'->%r not supported, ignoring.", k)
                continue
            try:
                klass = load_class(self.config["classes"][k])
            except (AttributeError, ImportError, ValueError) as exc:
                self.logger.exception(
                    "Cannot load class %r, ignoring: %s", self.config["classes"][k], exc
                )
                continue
            try:
                super_klass = load_class(v)
            except (AttributeError, ImportError, ValueError) as exc:
                self.logger.exception("Loading super class %r: %s", v, exc)
                raise InitialisationError("Cannot load super class '{}'.".format(v))
            if not issubclass(klass, super_klass):
                self.logger.error(
                    "Class %s.%s is not a subclass of %s.%s, ignoring.",
                    klass.__module__,
                    klass.__name__,
                    super_klass.__module__,
                    super_klass.__name__,
                )
                continue
            setattr(self, make_name, self.init_wrapper(klass))
            self.logger.info("%s.%s is now %s.", self.__class__.__name__, make_name, klass)

        for k in methods:
            if k not in self.config["classes"]:
                continue
            make_name = "make_{}".format(k)
            if not hasattr(self, make_name):
                self.logger.error("Configuration key 'classes'->%r not supported, ignoring.", k)
                continue
            try:
                kla, dot, meth = self.config["classes"][k].rpartition(".")
                klass = load_class(kla)
            except (AttributeError, ImportError, ValueError) as exc:
                self.logger.exception(
                    "Cannot load class %r, ignoring: %s", self.config["classes"][k], exc
                )
                continue
            try:
                method = getattr(klass, meth)
            except AttributeError as exc:
                self.logger.exception("Class %r has no method %r, ignoring: %s", klass, meth, exc)
                continue
            setattr(self, make_name, method)
            self.logger.info("%s.%s is now %s.%s", self.__class__.__name__, make_name, klass, meth)

    def make_reader(self, **kwargs):  # type: (**Any) -> ucsschool.importer.reader.csv_reader.CsvReader
        """
        Creates an input data reader.

        :param dict kwarg: passed to the reader constructor
        :return: a reader object
        :rtype: BaseReader
        """
        from .reader.csv_reader import CsvReader

        if self.config["input"]["type"] == "csv":
            kwargs.update(
                {
                    "filename": self.config["input"]["filename"],
                    "header_lines": self.config["csv"]["header_lines"],
                }
            )
            return CsvReader(**kwargs)
        else:
            raise NotImplementedError()

    def make_import_user(self, cur_user_roles, *arg, **kwargs):
        # type: (Iterable, *Any, **Any) -> ImportUserTV
        """
        Creates a ImportUser [of specific type], depending on its roles.

        :param cur_user_roles: [ucsschool.lib.roles, ..]
        :type cur_user_roles: list(str)
        :param tuple arg: passed to constructor of created class
        :param dict kwarg: passed to constructor of created class
        :return: object of :py:class:`ImportUser` subclass or :py:class:`ImportUser` if `cur_user_roles`
            was empty
        :rtype: ImportUser
        """
        from ucsschool.lib.roles import role_pupil, role_staff, role_teacher

        from .models.import_user import (
            ImportStaff,
            ImportStudent,
            ImportTeacher,
            ImportTeachersAndStaff,
            ImportUser,
        )

        if not cur_user_roles:
            return ImportUser(*arg, **kwargs)
        if role_pupil in cur_user_roles:
            return ImportStudent(*arg, **kwargs)
        if role_teacher in cur_user_roles:
            if role_staff in cur_user_roles:
                return ImportTeachersAndStaff(*arg, **kwargs)
            else:
                return ImportTeacher(*arg, **kwargs)
        else:
            return ImportStaff(*arg, **kwargs)

    def make_mass_importer(self, dry_run=True):
        # type: (Optional[bool]) -> ucsschool.importer.mass_import.mass_import.MassImport
        """
        Creates a MassImport object.

        :param bool dry_run: set to False to actually commit changes to LDAP
        :return: a :py:class:`MassImport` object
        :rtype: MassImport
        """
        from .mass_import.mass_import import MassImport

        return MassImport(dry_run=dry_run)

    def make_password_exporter(self, *arg, **kwargs):
        # type: (*Any, **Any) -> ucsschool.importer.writer.new_user_password_csv_exporter.NewUserPasswordCsvExporter  # noqa: E501
        """
        Creates a ResultExporter object that can dump passwords to disk.

        :param tuple arg: passed to constructor of created class
        :param dict kwarg: passed to constructor of created class
        :return: a :py:class:`ResultExporter` object
        :rtype: NewUserPasswordCsvExporter
        """
        from .writer.new_user_password_csv_exporter import NewUserPasswordCsvExporter

        return NewUserPasswordCsvExporter(*arg, **kwargs)

    def make_result_exporter(self, *arg, **kwargs):
        # type: (*Any, **Any) -> ucsschool.importer.writer.user_import_csv_result_exporter.UserImportCsvResultExporter  # noqa: E501
        """
        Creates a ResultExporter object.

        :param tuple arg: passed to constructor of created class
        :param dict kwarg: passed to constructor of created class
        :return: a :py:class:`ResultExporter` object
        :rtype: UserImportCsvResultExporter
        """
        from .writer.user_import_csv_result_exporter import UserImportCsvResultExporter

        return UserImportCsvResultExporter(*arg, **kwargs)

    def make_user_importer(self, dry_run=True):
        # type: (Optional[bool]) -> ucsschool.importer.mass_import.user_import.UserImport
        """
        Creates a user importer.

        :param bool dry_run: set to False to actually commit changes to LDAP
        :return: a :py:class:`UserImport` object
        :rtype: UserImport
        """
        from .mass_import.user_import import UserImport

        return UserImport(dry_run=dry_run)

    def make_ucr(self):  # type: () -> univention.config_registry.ConfigRegistry
        """
        Get a initialized UCR instance.

        :return: ConfigRegistry object
        :rtype: univention.config_registry.ConfigRegistry
        """
        return ucr

    def make_unique_email_handler(self, max_length=254, dry_run=True):
        # type: (Optional[int], Optional[bool]) -> ucsschool.importer.utils.username_handler.EmailHandler
        """
        Get a EmailHandler instance.

        :param int max_length: created email adresses must not be longer than this
        :param bool dry_run: set to False to actually commit changes to LDAP
        :return: an :py:class:`EmailHandler` object
        :rtype: EmailHandler
        """
        from .utils.username_handler import EmailHandler

        return EmailHandler(max_length, dry_run)

    def make_username_handler(self, max_length, dry_run=True):
        # type: (int, Optional[bool]) -> ucsschool.importer.utils.username_handler.UsernameHandler
        """
        Get a UsernameHandler instance.

        :param int max_length: created usernames must not be longer than this
        :param bool dry_run: set to False to actually commit changes to LDAP
        :return: a :py:class:`UsernameHandler` object
        :rtype: UsernameHandler
        """
        from .utils.username_handler import UsernameHandler

        return UsernameHandler(max_length, dry_run)

    def make_user_writer(self, *arg, **kwargs):
        # type: (*Any, **Any) -> ucsschool.importer.writer.csv_writer.CsvWriter
        """
        Creates a user writer object.

        :param tuple arg: passed to constructor of created class
        :param dict kwarg: passed to constructor of created class
        :return: a :py:class:`ucsschool.importer.writer.BaseWriter` object
        :rtype: CsvWriter
        """
        from .writer.csv_writer import CsvWriter

        return CsvWriter(*arg, **kwargs)
