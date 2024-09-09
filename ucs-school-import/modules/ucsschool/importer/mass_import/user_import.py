#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
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

"""Default user import class."""

import copy
import datetime
import logging
import sys
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, Union  # noqa: F401

import six
from ldap.filter import filter_format

from ucsschool.lib.models.attributes import ValidationError
from ucsschool.lib.models.base import NoObject, WrongObjectType

from ..configuration import Configuration
from ..exceptions import (
    CreationError,
    DeletionError,
    ModificationError,
    MoveError,
    TooManyErrors,
    UcsSchoolImportError,
    UnknownAction,
    UserValidationError,
    WrongUserType,
)
from ..factory import Factory
from ..utils.import_pyhook import run_import_pyhooks
from ..utils.ldap_connection import get_admin_connection, get_readonly_connection
from ..utils.post_read_pyhook import PostReadPyHook

if TYPE_CHECKING:
    from ..configuration import ReadOnlyDict  # noqa: F401
    from ..models.import_user import ImportUser  # noqa: F401


class UserImport(object):
    """
    Currently used by MassImport like this:

    1. read_input()
    2. detect_users_to_delete()
    3. delete_users()
    4. create_and_modify_users()
    5. log_stats()
    6. get_result_data()
    """

    def __init__(self, dry_run=True):
        """:param bool dry_run: set to False to actually commit changes to LDAP"""
        self.dry_run = dry_run
        self.errors = []  # type: List[UcsSchoolImportError]
        self.imported_users = []  # type: List[ImportUser]
        self.added_users = defaultdict(list)  # type: Dict[str, List[Dict[str, Any]]]
        self.modified_users = defaultdict(list)  # type: Dict[str, List[Dict[str, Any]]]
        self.deleted_users = defaultdict(list)  # type: Dict[str, List[Dict[str, Any]]]
        self.config = Configuration()  # type: ReadOnlyDict
        self.logger = logging.getLogger(__name__)
        self.connection, self.position = get_readonly_connection() if dry_run else get_admin_connection()
        self.factory = Factory()
        self.reader = self.factory.make_reader(filename=self.config["input"]["filename"])
        self.ucr = self.factory.make_ucr()
        self.imported_users_len = 0

    def read_input(self):  # type: () -> List[ImportUser]
        """
        Read users from input data.

        * :py:class:`UcsSchoolImportErrors` are stored in in `self.errors` (with input entry number in
            `error.entry_count`).

        :return: ImportUsers found in input
        :rtype: list(ImportUser)
        """
        num = 1
        self.logger.info("------ Starting to read users from input data... ------")
        while True:
            try:
                import_user = next(self.reader)
                self.logger.info("Done reading %d. user: %s", num, import_user)
                self.imported_users.append(import_user)
            except StopIteration:
                run_import_pyhooks(PostReadPyHook, "all_entries_read", self.imported_users, self.errors)
                break
            except UcsSchoolImportError as exc:
                self.logger.exception("Error reading %d. user: %s", num, exc)
                self._add_error(exc)
            num += 1
        self.logger.info("------ Read %d users from input data. ------", len(self.imported_users))
        return self.imported_users

    def create_and_modify_users(self, imported_users):
        # type: (List[ImportUser]) -> Tuple[List[UcsSchoolImportError], Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]  # noqa: E501
        """
        Create and modify users.

        * `self.added_users` and `self.modified_users` will hold created / modified
            :py:class:`ImportUser` objects.
        * :py:class:`UcsSchoolImportErrors` are stored in `self.errors` (with failed
            :py:class:`ImportUser` objects in `error.import_user`).

        :param imported_users: ImportUser objects
        :type imported_users: :func:`list`
        :return: (self.errors, self.added_users, self.modified_users)
        :rtype: tuple(list[UcsSchoolImportError], list[dict], list[dict])
        """
        self.logger.info("------ Creating / modifying users... ------")
        usernum = 0
        self.imported_users_len = len(imported_users)
        while imported_users:
            imported_user = imported_users.pop(0)
            usernum += 1
            percentage = 10 + 90 * usernum // self.imported_users_len  # 10% - 100%
            self.progress_report(
                description="Creating and modifying users: {}%.".format(percentage),
                percentage=int(percentage),
                done=usernum,
                total=self.imported_users_len,
                errors=len(self.errors),
            )
            if imported_user.action == "D":
                continue
            try:
                self.logger.debug(
                    "Creating / modifying user %d/%d %s...",
                    usernum,
                    self.imported_users_len,
                    imported_user,
                )
                user = self.determine_add_modify_action(imported_user)
                cls_name = user.__class__.__name__

                try:
                    action_str = {"A": "Adding", "D": "Deleting", "M": "Modifying"}[user.action]
                except KeyError:
                    raise UnknownAction(
                        "{}  (source_uid:{} record_uid: {}) has unknown action '{}'.".format(
                            user, user.source_uid, user.record_uid, user.action
                        ),
                        entry_count=user.entry_count,
                        import_user=user,
                    )

                if user.action in ["A", "M"]:
                    _user = user.to_dict()  # sorted output
                    self.logger.info(
                        "%s %s (source_uid:%s record_uid:%s) attributes: {%s}...",
                        action_str,
                        user,
                        user.source_uid,
                        user.record_uid,
                        ", ".join("{!r}: {!r}".format(k, _user[k]) for k in sorted(_user.keys())),
                    )
                # save password of new user for later export (NewUserPasswordCsvExporter):
                password = user.password
                try:
                    if user.action == "A":
                        err = CreationError  # type: Union[Type[CreationError], Type[ModificationError]]
                        store = self.added_users[cls_name]  # type: List[Dict[str, Any]]
                        if self.dry_run:
                            user.validate(
                                self.connection,
                                validate_unlikely_changes=True,
                                check_username=True,
                            )
                            if user.errors:
                                raise ValidationError(user.errors.copy())
                            user.call_hooks("pre", "create", self.connection)
                            self.logger.info("Dry-run: skipping user.create() for %s.", user)
                            success = True
                            user.call_hooks("post", "create", self.connection)
                        else:
                            success = user.create(lo=self.connection)
                    elif user.action == "M":
                        err = ModificationError
                        store = self.modified_users[cls_name]
                        if self.dry_run:
                            user.validate(
                                self.connection,
                                validate_unlikely_changes=True,
                                check_username=False,
                                check_name=False,
                            )
                            if user.errors:
                                raise ValidationError(user.errors.copy())
                            user.call_hooks("pre", "modify", self.connection)
                            self.logger.info("Dry-run: skipping user.modify() for %s.", user)
                            success = True
                            user.call_hooks("post", "modify", self.connection)
                        else:
                            success = user.modify(lo=self.connection)
                    else:
                        # delete
                        continue
                except ValidationError as exc:
                    six.reraise(
                        UserValidationError,
                        UserValidationError(
                            "ValidationError when {} {} "
                            "(source_uid:{} record_uid: {}): {}".format(
                                action_str.lower(),
                                user,
                                user.source_uid,
                                user.record_uid,
                                exc,
                            ),
                            validation_error=exc,
                            import_user=user,
                        ),
                        sys.exc_info()[2],
                    )

                if success:
                    self.logger.info(
                        "Success %s %d/%d %s (source_uid:%s record_uid: %s).",
                        action_str.lower(),
                        usernum,
                        self.imported_users_len,
                        user,
                        user.source_uid,
                        user.record_uid,
                    )
                    user.password = password
                    store.append(user.to_dict())
                else:
                    raise err(
                        "Error {} {}/{} {} (source_uid:{} record_uid: {}), does probably "
                        "{}exist.".format(
                            action_str.lower(),
                            usernum,
                            len(imported_users),
                            user,
                            user.source_uid,
                            user.record_uid,
                            "not " if user.action == "M" else "already ",
                        ),
                        entry_count=user.entry_count,
                        import_user=user,
                    )

            except (CreationError, ModificationError) as exc:
                self.logger.error("Entry #%d: %s", exc.entry_count, exc)  # traceback useless
                self._add_error(exc)
            except UcsSchoolImportError as exc:
                self.logger.exception("Entry #%d: %s", exc.entry_count, exc)
                self._add_error(exc)
        num_added_users = sum(map(len, self.added_users.values()))
        num_modified_users = sum(map(len, self.modified_users.values()))
        self.logger.info(
            "------ Created %d users, modified %d users. ------",
            num_added_users,
            num_modified_users,
        )
        return self.errors, self.added_users, self.modified_users

    def find_importuser_in_ldap(self, import_user):  # type: (ImportUser) -> ImportUser
        """
        Fetch fresh :py:class:`ImportUser` object from LDAP.

        :param ImportUser import_user: ImportUser object to use as reference for search
        :return: fresh ImportUser object
        :rtype: ImportUser
        :raises NoObject: if ImportUser cannot be found
        :raises WrongUserType: if the user in LDAP is not of the same type as the `import_user` object
        """
        try:
            return import_user.get_by_import_id(
                self.connection, import_user.source_uid, import_user.record_uid
            )
        except WrongObjectType as exc:
            six.reraise(
                WrongUserType,
                WrongUserType(
                    str(exc),
                    entry_count=import_user.entry_count,
                    import_user=import_user,
                ),
                sys.exc_info()[2],
            )

    def prepare_imported_user(self, imported_user, old_user):
        # type: (ImportUser, Optional[ImportUser]) -> ImportUser
        """
        Prepare attributes of ``imported_user`` object. Optionally save existing
        user (``old_user``) object reference in ``imported_user.old_user``.
        Sets ``imported_user.action`` according to ``is_new_user``.

        :param ImportUser imported_user: object to prepare attributes of
        :param old_user: imported_user equivalent already existing in LDAP or None
        :type old_user: ImportUser or None
        :return: ImportUser object with attributes prepared
        :rtype: ImportUser
        """
        if old_user:
            imported_user.old_user = copy.deepcopy(old_user)
        imported_user.prepare_all(new_user=not old_user)
        imported_user.action = "M" if old_user else "A"
        return imported_user

    def determine_add_modify_action(self, imported_user):  # type: (ImportUser) -> ImportUser
        """
        Determine what to do with the ImportUser. Should set attribute `action`
        to either `A` or `M`. If set to `M` the returned user must be a opened
        :py:class:`ImportUser` from LDAP.

        Run modify preparations here, like school-move etc.

        :param ImportUser imported_user: ImportUser from input
        :return: ImportUser with action set and possibly fetched from LDAP
        :rtype: ImportUser
        :raises WrongUserType: if the user in LDAP is not of the same type as the `import_user` object
        """
        try:
            user = self.find_importuser_in_ldap(imported_user)
        except NoObject:
            # no user found -> create
            return self.prepare_imported_user(imported_user, None)

        # user found -> modify
        imported_user = self.prepare_imported_user(imported_user, user)
        if user.school != imported_user.school:
            if user.school in imported_user.schools:
                self.logger.info(
                    "Preventing school move of %r by changing value of 'school' attribute from %r to "
                    "previous value %r.",
                    imported_user.name,
                    imported_user.school,
                    user.school,
                )
                imported_user.school = user.school
            else:
                self.logger.info(
                    "User will change school. Previous school: %r, new school: %r.",
                    user.school,
                    imported_user.school,
                )
                user = self.school_move(imported_user, user)
        user.update(imported_user)
        if (
            user.disabled != "0"
            or user.has_expiry(self.connection)
            or user.has_purge_timestamp(self.connection)
        ):
            self.logger.info(
                "Found user %r that was previously deactivated or is scheduled for deletion (purge "
                "timestamp is non-empty), reactivating user.",
                user,
            )
            user.reactivate()
        return user

    def get_existing_users_search_filter(self):  # type: () -> str
        """
        Create LDAP filter with which to find existing users.

        In the case of the default UserImport, we look at:
        `user.source_uid == config[source_uid]`

        :return: LDAP filter
        :rtype: str
        """
        oc_filter = self.factory.make_import_user([]).get_ldap_filter_for_user_role()
        return filter_format(
            "(&{}(ucsschoolSourceUID=%s)(ucsschoolRecordUID=*))".format(oc_filter),
            (self.config["source_uid"],),
        )

    def get_ids_of_existing_users(self):  # type: () -> List[Tuple[str, str]]
        """
        Get IDs of existing users.

        :return: list of tuples: [(source_uid, record_uid), ..]
        :rtype: list(tuple(str, str))
        """
        attr = ["ucsschoolSourceUID", "ucsschoolRecordUID"]
        filter_s = self.get_existing_users_search_filter()
        self.logger.debug("Searching with filter=%r", filter_s)
        ucs_ldap_users = self.connection.search(filter_s, attr=attr)
        return [
            (
                lu[1]["ucsschoolSourceUID"][0].decode("utf-8"),
                lu[1]["ucsschoolRecordUID"][0].decode("utf-8"),
            )
            for lu in ucs_ldap_users
        ]

    def detect_users_to_delete(self):  # type: () -> List[Tuple[str, str, List[str]]]
        """
        Find difference between source database and UCS user database.

        :return: list of tuples: [(source_uid, record_uid, input_data), ..]
        :rtype: list(tuple(str, str, list(str)))
        """
        self.logger.info("------ Detecting which users to delete... ------")

        if self.config["no_delete"]:
            self.logger.info(
                "------ Looking only for users with action='D' (no_delete=%r) ------",
                self.config["no_delete"],
            )
            return [
                (user.source_uid, user.record_uid, user.input_data)
                for user in self.imported_users
                if user.action == "D"
            ]

        ucs_user_ids = set(self.get_ids_of_existing_users())
        imported_user_ids = {(iu.source_uid, iu.record_uid) for iu in self.imported_users}
        users_to_delete = ucs_user_ids - imported_user_ids
        users_to_delete = [(u[0], u[1], []) for u in users_to_delete]
        self.logger.debug("users_to_delete=%r", users_to_delete)
        return users_to_delete

    def delete_users(self, users=None):
        # type: (Optional[List[Tuple[str, str, List[str]]]]) -> Tuple[List[UcsSchoolImportError], Dict[str, List[Dict[str, Any]]]]  # noqa: E501
        """
        Delete users.

        * :py:meth:`detect_users_to_delete()` should have run before this.
        * `self.deleted_users` will hold objects of deleted :py:class:`ImportUser`.
        * :py:class:`UcsSchoolImportErrors` are stored in `self.errors` (with failed
            :py:class:`ImportUser` object in `error.import_user`).
        * To add or change a deletion strategy overwrite :py:meth:`do_delete()`.

        :param users: :func:`list` of tuples: [(source_uid, record_uid, input_data), ..]
        :type users: :func:`list`
        :return: (self.errors, self.deleted_users)
        :rtype: tuple
        """
        self.logger.info("------ Deleting %d users... ------", len(users))
        a_user = self.factory.make_import_user([])
        for num, (source_uid, record_uid, input_data) in enumerate(users, start=1):
            percentage = 10 * num // len(users)  # 0% - 10%
            self.progress_report(
                description="Deleting users: {}.".format(percentage),
                percentage=int(percentage),
                done=num,
                total=len(users),
                errors=len(self.errors),
            )
            try:
                # additional_udm_properties are loaded from ldap, so that remove hooks can
                # work with them the same way as other hooks. For "A" and "M" operations,
                # udm_properties are set by the reader class.
                additional_udm_properties = self.reader.get_imported_udm_property_names(a_user)
                user = a_user.get_by_import_id(
                    self.connection,
                    source_uid,
                    record_uid,
                    udm_properties=additional_udm_properties,
                )
                user.action = "D"  # mark for logging/csv-output purposes
                user.input_data = input_data  # most likely empty list
            except NoObject as exc:
                self.logger.error(
                    "Cannot delete non existing user with source_uid=%r, record_uid=%r input_data=%r: "
                    "%s",
                    source_uid,
                    record_uid,
                    input_data,
                    exc,
                )
                continue
            try:
                success = self.do_delete(user)
                if success:
                    self.logger.info(
                        "Success deleting %d/%d %r (source_uid:%s record_uid: %s).",
                        num,
                        len(users),
                        user.name,
                        user.source_uid,
                        user.record_uid,
                    )
                else:
                    raise DeletionError(
                        "Error deleting user '{}' (source_uid:{} record_uid: {}), has probably already "
                        "been deleted.".format(user.name, user.source_uid, user.record_uid),
                        entry_count=user.entry_count,
                        import_user=user,
                    )
                self.deleted_users[user.__class__.__name__].append(user.to_dict())
            except UcsSchoolImportError as exc:
                self.logger.exception("Error in entry #%d: %s", exc.entry_count, exc)
                self._add_error(exc)
        self.logger.info(
            "------ Deleted %d users. ------",
            sum(map(len, self.deleted_users.values())),
        )
        return self.errors, self.deleted_users

    def school_move(self, imported_user, user):  # type: (ImportUser, ImportUser) -> ImportUser
        """
        Change users primary school.

        :param ImportUser imported_user: User from input with target school
        :param ImportUser user: existing User with old school
        :return: user in new position, freshly fetched from LDAP
        :rtype: ImportUser
        """
        self.logger.info("Moving %s from school %r to %r...", user, user.school, imported_user.school)
        user = self.do_school_move(imported_user, user)
        return user

    def do_school_move(self, imported_user, user):  # type: (ImportUser, ImportUser) -> ImportUser
        """
        Change users primary school - :py:meth:`school_move()` without calling Python
        hooks (ucsschool lib calls executables anyway).

        :param ImportUser imported_user: User from input with target school
        :param ImportUser user: existing User with old school
        :return: user in new position, freshly fetched from LDAP
        :rtype: ImportUser
        """
        if self.dry_run:
            user.check_schools(lo=self.connection, additional_schools=[imported_user.school])
            user.validate(self.connection, validate_unlikely_changes=True, check_username=False)
            if self.errors:
                raise UserValidationError(
                    "ValidationError when moving {} from {!r} to {!r}.".format(
                        user, user.school, imported_user.school
                    ),
                    validation_error=ValidationError(user.errors.copy()),
                )
            user.call_hooks("pre", "move", self.connection)
            self.logger.info(
                "Dry-run: would move %s from %r to %r.",
                user,
                user.school,
                imported_user.school,
            )
            user._unique_ids_replace_dn(user.dn, imported_user.dn)
            res = True
            user.call_hooks("post", "move", self.connection)
        else:
            res = user.change_school(imported_user.school, self.connection)
        if not res:
            raise MoveError(
                "Error moving {} from school '{}' to '{}'.".format(
                    user, user.school, imported_user.school
                ),
                entry_count=imported_user.entry_count,
                import_user=imported_user,
            )
        # refetch user from LDAP
        user = imported_user.get_by_import_id(
            self.connection, imported_user.source_uid, imported_user.record_uid
        )
        return user

    def do_delete(self, user):  # type: (ImportUser) -> bool
        """
        Delete or deactivate a user.

        IMPLEMENTME to add or change a deletion variant.

        :param ImportUser user: user to be deleted
        :return: whether the deletion worked
        :rtype: bool
        """
        deactivation_grace = max(
            0, int(self.config.get("deletion_grace_period", {}).get("deactivation", 0))
        )
        deletion_grace = max(0, int(self.config.get("deletion_grace_period", {}).get("deletion", 0)))
        modified = False
        success = None

        if deletion_grace <= deactivation_grace:
            # just delete, ignore deactivation setting
            if deletion_grace == 0:
                # delete user right now
                success = self.delete_user_now(user)
            else:
                # delete user later
                modified |= self.set_deletion_grace(user, deletion_grace)
        else:
            # deactivate first, delete later
            if deactivation_grace == 0:
                # deactivate user right now
                modified |= self.deactivate_user_now(user)
            else:
                # deactivate user later
                modified |= self.set_deactivation_grace(user, deactivation_grace)

            # delete user later
            modified |= self.set_deletion_grace(user, deletion_grace)

        if success is not None:
            # immediate deletion already happened above
            pass
        elif self.dry_run:
            user.call_hooks("pre", "remove", self.connection)
            self.logger.info(
                "Dry-run: not expiring, deactivating or setting the purge timestamp for %s.",
                user,
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
            success = user.modify(lo=self.connection, validate=False)
        else:
            # not a dry_run, but user was not modified, because
            # disabled / expiration date / purge timestamp were already set
            success = True

        user.invalidate_all_caches()
        return success

    def deactivate_user_now(self, user):  # type: (ImportUser) -> bool
        """
        Deactivate the user. Does not run user.modify().

        :param ImportUser user: user to deactivate when :py:meth:`modidy()` is run
        :return: whether any changes were made to the object and :py:meth:`user.modify()` is required
        :rtype: bool
        """
        if user.disabled == "1":
            self.logger.info("User %s is already disabled.", user)
            return False
        else:
            self.logger.info("Deactivating user %s...", user)
            user.deactivate()
            return True

    def delete_user_now(self, user):  # type: (ImportUser) -> bool
        """
        Truly delete the user.

        :param ImportUser user: object to delete
        :return: return value from the ucsschool.lib.model remove() call
        :rtype: bool
        """
        self.logger.info("Deleting user %s...", user)
        if self.dry_run:
            user.call_hooks("pre", "remove", self.connection)
            self.logger.info("Dry-run: not removing user %s.", user)
            user.call_hooks("post", "remove", self.connection)
            return True
        else:
            return user.remove(self.connection)

    def set_deactivation_grace(self, user, grace):  # type: (ImportUser, int) -> bool
        """
        Sets the account expiration date (UDM attribute `userexpiry`) on the
        user object. Does not run :py:meth:`user.modify()`.

        :param ImportUser user: object to delete
        :param int grace: days until deactivation
        :return: whether any changes were made to the object and user.modify() is required
        :rtype: bool
        """
        if user.disabled == "1":
            self.logger.info("User %s is already disabled. No account expiration date is set.", user)
            return False
        elif user.has_expiry(self.connection):
            self.logger.info(
                "An account expiration date is already set for user %s. The entry remains unchanged.",
                user,
            )
            return False
        else:
            expiry = datetime.datetime.now() + datetime.timedelta(days=grace)
            expiry_str = expiry.strftime("%Y-%m-%d")
            self.logger.info("Setting account expiration date of %s to %s...", user, expiry_str)
            user.expiration_date = expiry_str
            return True

    def set_deletion_grace(self, user, grace):  # type: (ImportUser, int) -> bool
        """
        Sets the account deletion timestamp (UDM attribute `ucsschoolPurgeTimestamp`)
        on the user object. Does not run :py:meth:`user.modify()`.

        :param ImportUser user: user to schedule the deletion for
        :param int grace: days until deletion
        :return: whether any changes were made to the object and user.modify() is required
        :rtype: bool
        """
        if user.has_purge_timestamp(self.connection):
            self.logger.info(
                "User %s is already scheduled for deletion. The entry remains unchanged.",
                user,
            )
            return False
        else:
            purge_ts = datetime.datetime.now() + datetime.timedelta(days=grace)
            purge_ts_str = purge_ts.strftime("%Y-%m-%d")
            self.logger.info("Setting deletion grace date of %s to %r...", user, purge_ts_str)
            user.set_purge_timestamp(purge_ts_str)
            return True

    def log_stats(self):  # type: () -> str
        """Log statistics about read, created, modified and deleted users."""
        self.logger.info("------ User import statistics ------")
        lines = ["Read users from input data: {}".format(self.imported_users_len)]
        cls_names = list(self.added_users)
        cls_names.extend(self.modified_users)
        cls_names.extend(self.deleted_users)
        cls_names = set(cls_names)
        columns_default = 4
        columns = self.ucr.get_int("ucsschool/import/log_stats/columns", columns_default)
        if columns < 1:  # validate the `pint` type of `ucsschool/import/log_stats/columns`
            columns = columns_default
        lines_allowed_default = 2
        lines_allowed = self.ucr.get_int("ucsschool/import/log_stats/lines", lines_allowed_default)
        if lines_allowed < 0:  # validate the `uint` type of `ucsschool/import/log_stats/lines`
            lines_allowed = lines_allowed_default
        allowed_user_print_cnt = columns * lines_allowed
        for cls_name in sorted(cls_names):
            lines.append("Created {}: {}".format(cls_name, len(self.added_users.get(cls_name, []))))
            added_users_len = len(self.added_users[cls_name])
            if added_users_len <= allowed_user_print_cnt:
                for i in range(0, added_users_len, columns):
                    lines.append(
                        "  {}".format([iu["name"] for iu in self.added_users[cls_name][i : i + columns]])
                    )
            lines.append("Modified {}: {}".format(cls_name, len(self.modified_users.get(cls_name, []))))
            modified_users_len = len(self.modified_users[cls_name])
            if modified_users_len <= allowed_user_print_cnt:
                for i in range(0, modified_users_len, columns):
                    lines.append(
                        "  {}".format(
                            [iu["name"] for iu in self.modified_users[cls_name][i : i + columns]]
                        )
                    )
            lines.append("Deleted {}: {}".format(cls_name, len(self.deleted_users.get(cls_name, []))))
            deleted_users_len = len(self.deleted_users[cls_name])
            if deleted_users_len <= allowed_user_print_cnt:
                for i in range(0, deleted_users_len, columns):
                    lines.append(
                        "  {}".format(
                            [iu["name"] for iu in self.deleted_users[cls_name][i : i + columns]]
                        )
                    )
        lines.append("Errors: {}".format(len(self.errors)))
        if self.errors:
            username_width = max(
                len(
                    error.import_user.name
                    if error.import_user and error.import_user.name
                    else "<No name>"
                )
                for error in self.errors[:10]
            )
            error_header = ("Entry | {: ^%d} | Error description" % (username_width,)).format("User")
            lines.append(error_header)
            lines.append("-" * len(error_header))
            for error in self.errors:
                lines.append(
                    ("{: >5} | {: >%d} | {}" % (username_width,)).format(
                        error.entry_count,
                        error.import_user.name
                        if error.import_user and error.import_user.name
                        else "<No name>",
                        error,
                    )
                )
        for line in lines:
            self.logger.info(line)
        self.logger.info("------ End of user import statistics ------")
        return "\n".join(lines)

    def _add_error(self, exc):  # type: (UcsSchoolImportError) -> None
        """
        Append given exception to list of errors.
        :param UcsSchoolImportError exc: an Exception raised during import
        :raises TooManyErrors: if the number of countable exceptions exceeds the number of tolerable
            errors
        """
        self.errors.append(exc)
        if -1 < self.config["tolerate_errors"] < len([x for x in self.errors if x.is_countable]):
            raise TooManyErrors(
                "More than {} errors.".format(self.config["tolerate_errors"]),
                self.errors,
            )

    def progress_report(self, description, percentage=0, done=0, total=0, **kwargs):
        if "progress_notification_function" not in self.config:
            return
        self.config["progress_notification_function"](description, percentage, done, total, **kwargs)

    def get_result_data(self):  # type: () -> UserImportData
        return UserImportData(self)


class UserImportData(object):
    def __init__(self, user_import):  # type: (UserImport) -> None
        self.config = user_import.config  # type: ReadOnlyDict
        self.dry_run = user_import.dry_run  # type: bool
        self.errors = user_import.errors  # type: List[UcsSchoolImportError]
        self.added_users = user_import.added_users  # type: Dict[str, List[Dict[str, Any]]]
        self.modified_users = user_import.modified_users  # type: Dict[str, List[Dict[str, Any]]]
        self.deleted_users = user_import.deleted_users  # type: Dict[str, List[Dict[str, Any]]]
