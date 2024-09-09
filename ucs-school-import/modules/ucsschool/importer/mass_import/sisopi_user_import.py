#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2018-2024 Univention GmbH
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

"""Single source database, partial import user import class."""

import copy
from typing import TYPE_CHECKING, Optional  # noqa: F401

from ldap.filter import filter_format

from ucsschool.lib.models.attributes import ValidationError

from ..exceptions import InvalidSchools, UserValidationError
from .user_import import UserImport

if TYPE_CHECKING:
    from ..models.import_user import ImportUser  # noqa: F401


class SingleSourcePartialUserImport(UserImport):
    """
    Currently used by MassImport like this:

    1. read_input()
    2. detect_users_to_delete()
    3. delete_users()
    4. create_and_modify_users()
    5. log_stats()
    6. get_result_data()

    In the SingleSourcePartialImport scenario the following is done:

    * Deletion: if a user is a member of the school being imported and is not
      part of the import data set, then only this school is removed from its
      ``schools`` attribute. If it was the last school, then the limbo school
      is added, and thus user object is moved there. A user never gets truly
      deleted in this scenario.
    * Creation: if a user is to be created, then first a search is done if it
      exists in *any* school (including the limbo school). If if exists
      somewhere, the school being imported is added to its ``schools`` attribute.
      If it was the limbo school, it's removed from it and thus moved from it
      to the school being imported.
      A new user object is only created, if it doesn't exist anywhere in the
      domain.
    """

    def __init__(self, dry_run=True):
        """:param bool dry_run: set to False to actually commit changes to LDAP"""
        super(SingleSourcePartialUserImport, self).__init__(dry_run)
        self.limbo_ou = self.config.get("limbo_ou")

    def prepare_imported_user(self, imported_user, old_user):
        # type: (ImportUser, Optional[ImportUser]) -> ImportUser
        """
        Prepare attributes of ``imported_user`` object. Optionally save existing
        user (``old_user``) object reference in ``imported_user.old_user``.
        Sets ``imported_user.action`` according to ``is_new_user``.

        In case of SingleSourcePartialImport, when a user exists:

        * when user is in limbo OU: move to new school
        * when user is any other OU: keep old ``school`` and add new school to ``schools``

        :param ImportUser imported_user: object to prepare attributes of
        :param old_user: imported_user equivalent already existing in LDAP or None
        :type old_user: ImportUser or None
        :return: ImportUser object with attributes prepared
        :rtype: ImportUser
        """
        # security check
        if (
            imported_user.school
            and imported_user.school != self.config["school"]
            or imported_user.schools
            and imported_user.schools not in (self.config["school"], [self.config["school"]])
        ):
            raise InvalidSchools(
                "In the SingleSourcePartialImport scenario it is not allowed to import into any other "
                "school that the one configured ({!r}). Found school={!r} schools={!r}.".format(
                    self.config["school"], imported_user.school, imported_user.schools
                ),
                entry_count=imported_user.entry_count,
                input=imported_user.input_data,
                import_user=imported_user,
            )

        if old_user:
            imported_user.old_user = copy.deepcopy(old_user)
            if old_user.school == self.limbo_ou:
                self.logger.info(
                    "User %r is in limbo school %r, moving to %r.",
                    old_user,
                    self.limbo_ou,
                    self.config["school"],
                )
                imported_user.school = self.config["school"]
                imported_user.schools = [self.config["school"]]
                imported_user.reactivate()
            else:
                self.logger.debug(
                    'config["school"]=%r config["limbo_ou"]=%r imported_user.school=%r '
                    "imported_user.schools=%r old_user.school=%r old_user.schools=%r",
                    self.config["school"],
                    self.limbo_ou,
                    imported_user.school,
                    imported_user.schools,
                    old_user.school,
                    old_user.schools,
                )
                if (
                    imported_user.school
                    and imported_user.school != old_user.school
                    or self.config["school"] not in old_user.schools
                ):
                    self.logger.info(
                        "User %r exists in other school(s). Adding %r to 'schools', not moving.",
                        old_user,
                        self.config["school"],
                    )
                imported_user.school = old_user.school
                imported_user.schools = old_user.schools
                if self.config["school"] not in old_user.schools:
                    imported_user.schools.append(self.config["school"])
                new_classes = copy.deepcopy(old_user.school_classes)
                new_classes.update(imported_user.school_classes)
                imported_user.school_classes = new_classes

        return super(SingleSourcePartialUserImport, self).prepare_imported_user(imported_user, old_user)

    def get_existing_users_search_filter(self):
        """
        Create LDAP filter with which to find existing users.

        In the case of SingleSourcePartialImport, we look at::

            user.source_uid == config[source_uid] && config[school] in user.schools

        :return: LDAP filter
        :rtype: str
        """
        oc_filter = self.factory.make_import_user([]).get_ldap_filter_for_user_role()
        return filter_format(
            "(&{}(ucsschoolSourceUID=%s)(ucsschoolRecordUID=*)(ucsschoolSchool=%s))".format(oc_filter),
            (self.config["source_uid"], self.config["school"]),
        )

    def do_delete(self, user):
        """
        Delete or deactivate a user.

        In the case of SingleSourcePartialImport:

        * if member of multiple schools, only remove from school being imported
        * if member of only one school (the one being imported), deactivate
          immediately and move to limbo school

        :param ImportUser user: user to be deleted
        :return: whether the deletion worked
        :rtype: bool
        """
        deletion_grace = max(0, int(self.config.get("deletion_grace_period", {}).get("deletion", 0)))
        modified = False

        self.logger.info("Removing %r from school %r...", user, self.config["school"])
        user.schools.remove(self.config["school"])

        if user.schools:
            self.logger.info("User is still member of school(s) %r.", user.schools)
            if user.school == self.config["school"]:
                imported_user = copy.deepcopy(user)
                imported_user.school = sorted(user.schools)[0]
                self.logger.info("User will be moved to school %r.", imported_user.school)
                user = self.school_move(imported_user, user)
                user.update(imported_user)  # user is freshly fetched from LDAP, readd import data
                # no modify() required, because the move takes care of it
            else:
                # perform user.modify() to remove user from school
                modified = True
                # must not have school classes of removed school anymore, when user.validate() runs
                user.school_classes.pop(self.config["school"], None)
        else:
            self.logger.info("Moving %r to limbo school %r.", user, self.limbo_ou)
            imported_user = copy.deepcopy(user)
            imported_user.school = self.limbo_ou
            imported_user.schools = [self.limbo_ou]
            imported_user.school_classes = {}
            user = self.school_move(imported_user, user)
            user.update(imported_user)  # user is freshly fetched from LDAP, readd import data
            modified |= self.set_deletion_grace(user, deletion_grace)
            modified |= self.deactivate_user_now(user)

        if self.dry_run:
            user.call_hooks("pre", "remove", self.connection)
            self.logger.info(
                "Dry-run: not expiring, deactivating or setting the purge timestamp for %s.", user
            )
            user.validate(self.connection, validate_unlikely_changes=True, check_username=False)
            if self.errors:
                raise UserValidationError(
                    "ValidationError when deleting {}.".format(user),
                    validation_error=ValidationError(user.errors.copy()),
                )
            success = True
            user.call_hooks("post", "remove", self.connection)
        elif modified:
            success = user.modify(lo=self.connection)
        else:
            # not a dry_run, but user was not modified, because user was not deactivated
            success = True

        user.invalidate_all_caches()
        return success
