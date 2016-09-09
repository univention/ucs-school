# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Default mass import class.
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

import sys
from collections import defaultdict
import datetime

from ldap.filter import filter_format
from univention.admin.uexceptions import noObject
from ucsschool.lib.models.attributes import ValidationError
from ucsschool.importer.exceptions import UcsSchoolImportError, CreationError, DeletionError, ModificationError, MoveError, ToManyErrors, UnkownAction, UnknownDeleteSetting, UserValidationError
from ucsschool.importer.factory import Factory
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.utils.logging import get_logger
from ucsschool.importer.utils.ldap_connection import get_admin_connection


class UserImport(object):
	def __init__(self, dry_run=True):
		"""
		:param dry_run: bool: set to False to actually commit changes to LDAP
		"""
		self.dry_run = dry_run
		self.errors = list()
		self.imported_users = list()
		self.added_users = defaultdict(list)
		self.modified_users = defaultdict(list)
		self.deleted_users = defaultdict(list)
		self.config = Configuration()
		self.logger = get_logger()
		self.connection, self.position = get_admin_connection()
		self.factory = Factory()
		self.reader = self.factory.make_reader()

	def read_input(self):
		"""
		Read users from input data.
		* UcsSchoolImportErrors are stored in in self.errors (with input entry
		number in error.entry).

		:return: list: ImportUsers found in input
		"""
		num = 1
		self.logger.info("------ Starting to read users from input data... ------")
		while True:
			try:
				import_user = self.reader.next()
				self.logger.info("Done reading %d. user: %s", num, import_user)
				self.imported_users.append(import_user)
			except StopIteration:
				break
			except UcsSchoolImportError as exc:
				self.logger.exception("Error reading %d. user: %s",  num, exc)
				self._add_error(exc)
			num += 1
		self.logger.info("------ Read %d users from input data. ------", len(self.imported_users))
		return self.imported_users

	def create_and_modify_users(self, imported_users=None):
		"""
		Create and modify users.
		* self.added_users and self.modified_users will hold objects of created/
		modified ImportUsers.
		* UcsSchoolImportErrors are stored in self.errors (with failed ImportUser
		object in error.import_user).

		:param imported_users: list: ImportUser objects
		:return tuple: (self.errors, self.added_users, self.modified_users)
		"""
		self.logger.info("------ Creating / modifying users... ------")
		for imported_user in imported_users:
			if imported_user.action == "D":
				continue
			try:
				self.logger.debug("Creating / modifying user %s...", imported_user)
				user = self.determine_add_modify_action(imported_user)
				cls_name = user.__class__.__name__

				try:
					action_str = {
						"A": "Adding",
						"D": "Deleting",
						"M": "Modifying"
					}[user.action]
				except KeyError:
					raise UnkownAction("{}  (source_uid:{} record_uid: {}) has unknown action '{}'.".format(
						user, user.source_uid, user.record_uid, user.action), entry=user.entry_count, import_user=user)

				if user.action in ["A", "M"]:
					self.logger.info("%s %s (source_uid:%s record_uid:%s) attributes=%r udm_properties=%r...",
						action_str, user, user.source_uid, user.record_uid, user.to_dict(), user.udm_properties)

				try:
					if user.action == "A":
						err = CreationError
						store = self.added_users[cls_name]
						if self.dry_run:
							self.logger.info("Dry run: would create %s now.", user)
							success = True
						else:
							success = user.create(lo=self.connection)
					elif user.action == "M":
						err = ModificationError
						store = self.modified_users[cls_name]
						if self.dry_run:
							self.logger.info("Dry run: would modify %s now.", user)
							success = True
						else:
							success = user.modify(lo=self.connection)
					else:
						# delete
						continue
				except ValidationError as exc:
					raise UserValidationError, UserValidationError("ValidationError when {} {} "
						"(source_uid:{} record_uid: {}): {}".format(action_str.lower(), user, user.source_uid,
						user.record_uid, exc), validation_error=exc, import_user=user), sys.exc_info()[2]

				if success:
					self.logger.info("Success %s %s (source_uid:%s record_uid: %s).", action_str.lower(), user,
						user.source_uid, user.record_uid)
					store.append(user)
				else:
					raise err("Error {} {} (source_uid:{} record_uid: {}), does probably {}exist.".format(
						action_str.lower(), user, user.source_uid, user.record_uid,
						"not " if user.action == "M" else "already "), entry=user.entry_count, import_user=user)

			except (CreationError, ModificationError) as exc:
				self.logger.error("Entry #%d: %s",  exc.entry, exc)  # traceback useless
				self._add_error(exc)
			except UcsSchoolImportError as exc:
				self.logger.exception("Entry #%d: %s",  exc.entry, exc)
				self._add_error(exc)
		num_added_users = sum(map(len, self.added_users.values()))
		num_modified_users = sum(map(len, self.modified_users.values()))
		self.logger.info("------ Created %d users, modified %d users. ------", num_added_users, num_modified_users)
		return self.errors, self.added_users, self.modified_users

	def determine_add_modify_action(self, imported_user):
		"""
		Determine what to do with the ImportUser. Should set attribute "action"
		to either "A" or "M". If set to "M" the returned user must be a opened
		ImportUser from LDAP.
		Run modify preparations here, like school-move etc.

		:param imported_user: ImportUser from input
		:return: ImportUser: ImportUser with action set and possibly fetched
		from LDAP
		"""
		try:
			user = imported_user.get_by_import_id(self.connection, imported_user.source_uid,
				imported_user.record_uid)
			imported_user.old_user = user
			imported_user.prepare_all(new_user=False)
			if user.school != imported_user.school:
				user = self.school_move(imported_user, user)
			user.update(imported_user)
			if user.disabled != "none" or user.has_expiry(self.connection):
				self.logger.info("Found deactivated user %r, reactivating.", user)
				if self.dry_run:
					self.logger.info("Dry run - not reactivating.")
				else:
					user.reactivate(self.connection)
			user.action = "M"
		except noObject:
			imported_user.prepare_all(new_user=True)
			user = imported_user
			user.action = "A"
		return user

	def detect_users_to_delete(self):
		"""
		Find difference between source database and UCS user database.

		:return list: ImportUsers to delete (objects loaded from LDAP)
		"""
		self.logger.info("------ Detecting which users to delete... ------")
		users_to_delete = list()
		a_user = self.factory.make_import_user([])

		if self.config["no_delete"]:
			self.logger.info("------ Looking only for users with action='D' (no_delete=%r) ------",
				self.config["no_delete"])
			for user in self.imported_users:
				if user.action == "D":
					try:
						ldap_user = a_user.get_by_import_id(self.connection, user.source_uid, user.record_uid)
						ldap_user.update(user)  # need user.input_data for hooks
						users_to_delete.append(ldap_user)
					except noObject:
						msg = "User to delete not found in LDAP: {}.".format(user)
						self.logger.error(msg)
						self._add_error(DeletionError(msg, entry=user.entry_count, import_user=user))
			return users_to_delete

		source_uid = self.config["sourceUID"]
		attr = ["ucsschoolSourceUID", "ucsschoolRecordUID"]
		filter_s = filter_format("(&(ucsschoolSourceUID=%s)(ucsschoolRecordUID=*))", (source_uid, ))

		id2imported_user = dict()  # for fast access later
		for iu in self.imported_users:
			id2imported_user[(iu.source_uid, iu.record_uid)] = iu
		imported_user_ids = set(id2imported_user.keys())

		# Find all users that exist in UCS but not in input.
		ucs_ldap_users = self.connection.search(filter_s, attr=attr)
		ucs_user_ids = set([(lu[1]["ucsschoolSourceUID"][0], lu[1]["ucsschoolRecordUID"][0]) for lu in ucs_ldap_users])

		# collect ucschool objects for those users to delete in imported_users
		for ucs_id_not_in_import in (ucs_user_ids - imported_user_ids):
			try:
				ldap_user = a_user.get_by_import_id(self.connection, ucs_id_not_in_import[0], ucs_id_not_in_import[1])
				ldap_user.action = "D"  # mark for logging/csv-output purposes
				users_to_delete.append(ldap_user)
			except noObject as exc:
				self.logger.error("Cannot delete non existing user with source_uid=%r, record_uid=%r: %s",
					ucs_id_not_in_import[0], ucs_id_not_in_import[1], exc)

		self.logger.debug("users_to_delete=%r", users_to_delete)
		return users_to_delete

	def delete_users(self, users=None):
		"""
		Delete users.
		* detect_users_to_delete() should have run before this.
		* self.deleted_users will hold objects of deleted ImportUsers.
		* UcsSchoolImportErrors are stored in self.errors (with failed ImportUser
		object in error.import_user).
		* To add or change a deletion strategy overwrite do_delete().

		:param users: list: ImportUsers with record_uid and source_uid set.
		:return: tuple: (self.errors, self.deleted_users)
		"""
		self.logger.info("------ Deleting %d users... ------", len(users))
		for user in users:
			try:
				success = self.do_delete(user)
				if success:
					self.logger.info("Success deleting user %r (source_uid:%s record_uid: %s).", user.name,
						user.source_uid, user.record_uid)
				else:
					raise DeletionError("Error deleting user '{}' (source_uid:{} record_uid: {}), has probably already "
						"been deleted.".format(user.name, user.source_uid, user.record_uid), entry=user.entry_count,
						import_user=user)
				self.deleted_users[user.__class__.__name__].append(user)
			except UcsSchoolImportError as exc:
				self.logger.exception("Error in entry #%d: %s",  exc.entry, exc)
				self._add_error(exc)
		self.logger.info("------ Deleted %d users. ------", len(self.deleted_users))
		return self.errors, self.deleted_users

	def school_move(self, imported_user, user):
		"""
		Change users primary school.

		:param imported_user: User from input with target school
		:param user: existing User with old school
		:return: ImportUser: user in new position, freshly fetched from LDAP
		"""
		self.logger.info("Moving %s from school %r to %r...", user, user.school, imported_user.school)
		user = self.do_school_move(imported_user, user)
		return user

	def do_school_move(self, imported_user, user):
		"""
		Change users primary school - school_move() without calling Python
		hooks (ucsschool lib calls executables anyway).
		"""
		if self.dry_run:
			self.logger.info("Dry run - not doing the school move.")
			res = True
		else:
			res = user.change_school(imported_user.school, self.connection)
		if not res:
			raise MoveError("Error moving {} from school '{}' to '{}'.".format(user, user.school, imported_user.school),
				entry=imported_user.entry_count, import_user=imported_user)
		# refetch user from LDAP
		user = imported_user.get_by_import_id(self.connection, imported_user.source_uid,
			imported_user.record_uid)
		return user

	def do_delete(self, user):
		"""
		Delete or deactivate a user.
		IMPLEMENTME to add or change a deletion variant.

		:param user: ImportUser
		:return bool: whether the deletion worked
		"""
		if self.config["user_deletion"]["delete"] and not self.config["user_deletion"]["expiration"]:
			# delete user right now
			self.logger.info("Deleting user %s...", user)
			if self.dry_run:
				self.logger.info("Dry run - not removing the user.")
				success = True
			else:
				success = user.remove(self.connection)
		elif self.config["user_deletion"]["delete"] and self.config["user_deletion"]["expiration"]:
			# set expiration date, don't delete, don't deactivate
			expiry = datetime.datetime.now() + datetime.timedelta(days=self.config["user_deletion"]["expiration"])
			expiry_str = expiry.strftime("%Y-%m-%d")
			self.logger.info("Setting account expiration date of %s to %s...", user, expiry_str)
			if self.dry_run:
				self.logger.info("Dry run - not expiring the user.")
			else:
				user.expire(expiry_str)
				user.modify(lo=self.connection)
			success = True
		elif not self.config["user_deletion"]["delete"] and self.config["user_deletion"]["expiration"]:
			# don't delete but deactivate with an expiration data
			expiry = datetime.datetime.now() + datetime.timedelta(days=self.config["user_deletion"]["expiration"])
			expiry_str = expiry.strftime("%Y-%m-%d")
			self.logger.info("Setting account expiration date of %s to %s...", user, expiry_str)
			self.logger.info("Deactivating user %s...", user)
			if self.dry_run:
				self.logger.info("Dry run - not expiring the user.")
				self.logger.info("Dry run - not deactivating the user.")
			else:
				user.expire(expiry_str)
				user.deactivate()
				user.modify(lo=self.connection)
			success = True
		else:
			raise UnknownDeleteSetting("Don't know what to do with user_deletion=%r and expiration=%r.".format(
				self.config["user_deletion"]["delete"], self.config["user_deletion"]["expiration"]),
				entry=user.entry_count, import_user=user)
		return success

	def log_stats(self):
		"""
		Log statistics about read, created, modified and deleted users.
		"""
		self.logger.info("------ User import statistics ------")
		self.logger.info("Read users from input data: %d", len(self.imported_users))
		cls_names = self.added_users.keys()
		cls_names.extend(self.modified_users.keys())
		cls_names.extend(self.deleted_users.keys())
		cls_names = set(cls_names)
		columns = 4
		for cls_name in sorted(cls_names):
			self.logger.info("Created %s: %d", cls_name, len(self.added_users.get(cls_name, [])))
			for i in range(0, len(self.added_users[cls_name]), columns):
				self.logger.info("  %s", [iu.name for iu in self.added_users[cls_name][i:i+columns]])
			self.logger.info("Modified %s: %d", cls_name, len(self.modified_users.get(cls_name, [])))
			for i in range(0, len(self.modified_users[cls_name]), columns):
				self.logger.info("  %s", [iu.name for iu in self.modified_users[cls_name][i:i+columns]])
			self.logger.info("Deleted %s: %d", cls_name, len(self.deleted_users.get(cls_name, [])))
			for i in range(0, len(self.deleted_users[cls_name]), columns):
				self.logger.info("  %s", [iu.name for iu in self.deleted_users[cls_name][i:i+columns]])
		self.logger.info("Errors: %d", len(self.errors))
		if self.errors:
			self.logger.info("Entry #: Error description")
		for error in self.errors:
			self.logger.info("  %d: %s: %s", error.entry, error.import_user.name if error.import_user else "NoName",
				error)
		self.logger.info("------ End of user import statistics ------")

	def _add_error(self, err):
		self.errors.append(err)
		if -1 < self.config["tolerate_errors"] < len(self.errors):
			raise ToManyErrors("More than {} errors.".format(self.config["tolerate_errors"]), self.errors)
