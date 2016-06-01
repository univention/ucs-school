# -*- coding: utf-8 -*-
#
# Univention UCS@School
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

from univention.admin.uexceptions import noObject
from ucsschool.lib.models.attributes import ValidationError
from ucsschool.lib.roles import role_pupil, role_teacher, role_staff
from ucsschool.importer.exceptions import UcsSchoolImportError, CreationError, DeletionError, ModificationError, ToManyErrors, UnkownAction, UnknownDeleteSetting, UserValidationError
from ucsschool.importer.factory import Factory
from ucsschool.importer.configuration import Configuration
from ucsschool.importer.utils.logging2udebug import get_logger
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
		if self.dry_run:
			self.logger.info("------ Dry run - not creating / modifying users. ------ ")
			return

		self.logger.info("------ Creating / modifying users... ------")
		for imported_user in imported_users:
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
					self.logger.info("%s %s (source_uid:%s record_uid:%s)...", action_str, user,
						user.source_uid, user.record_uid)

				try:
					if user.action == "A":
						self.pre_create_hook(user)
						err = CreationError
						store = self.added_users[cls_name]
						success = user.create(lo=self.connection)
					elif user.action == "M":
						self.pre_modify_hook(user)
						err = ModificationError
						store = self.modified_users[cls_name]
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

				if user.action == "A":
					# load user from LDAP for create_and_modify_hook(post)
					user = imported_user.get_by_import_id(self.connection, imported_user.source_uid,
						imported_user.record_uid)
					self.post_create_hook(user)
				elif user.action == "M":
					self.post_modify_hook(user)

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

		:param imported_user: ImportUser from input
		:return: ImportUser: ImportUser with action set and possibly fetched
		from LDAP
		"""
		try:
			user = imported_user.get_by_import_id(self.connection, imported_user.source_uid,
				imported_user.record_uid)
			imported_user.prepare_properties(new_user=False)
			user.update(imported_user)
			if user.disabled != "none" or user.has_expiry(self.connection):
				self.logger.info("Found deactivated user %r, reactivating.", user)
				user.reactivate(self.connection)
			user.action = "M"
		except noObject:
			imported_user.prepare_properties(new_user=True)
			user = imported_user
			user.action = "A"
		return user

	def detect_users_to_delete(self):
		"""
		Find difference between source database and UCS user database.

		:return list: ImportUsers to delete with record_uid and source_uid set
		"""
		self.logger.info("------ Detecting which users to delete... ------")
		attr = ["ucsschoolSourceUID", "ucsschoolRecordUID"]
		filter_s = "(&{}(ucsschoolSourceUID=*)(ucsschoolRecordUID=*))"
		student_filter_s = filter_s.format("(objectclass=ucsschoolStudent)")
		staff_filter_s = "(&(!(objectclass=ucsschoolTeacher)){})".format(
			filter_s.format("(objectclass=ucsschoolStaff)"))
		teacher_filter_s = "(&(!(objectclass=ucsschoolStaff)){})".format(
			filter_s.format("(objectclass=ucsschoolTeacher)"))
		teacher_staff_filter_s = filter_s.format("(objectclass=ucsschoolTeacher)(objectclass=ucsschoolStaff)")

		students_in_ucs = self.connection.search(student_filter_s, attr=attr)
		staff_in_ucs = self.connection.search(staff_filter_s, attr=attr)
		teachers_in_ucs = self.connection.search(teacher_filter_s, attr=attr)
		teachers_staff_in_ucs = self.connection.search(teacher_staff_filter_s, attr=attr)

		# Find all users that exist in UCS but not in input.
		imported_users = set([(iu.source_uid, iu.record_uid) for iu in self.imported_users])
		ucs_students = set([(iu[1]["ucsschoolSourceUID"][0], iu[1]["ucsschoolRecordUID"][0]) for iu in students_in_ucs])
		ucs_staff = set([(iu[1]["ucsschoolSourceUID"][0], iu[1]["ucsschoolRecordUID"][0]) for iu in staff_in_ucs])
		ucs_teachers = set([(iu[1]["ucsschoolSourceUID"][0], iu[1]["ucsschoolRecordUID"][0]) for iu in teachers_in_ucs])
		ucs_teachers_staff = set([(iu[1]["ucsschoolSourceUID"][0], iu[1]["ucsschoolRecordUID"][0])
			for iu in teachers_staff_in_ucs])

		# We need those to fetch the correct type from LDAP.
		a_student = self.factory.make_import_user([role_pupil])
		a_staff = self.factory.make_import_user([role_staff])
		a_teacher = self.factory.make_import_user([role_teacher])
		a_staff_teacher = self.factory.make_import_user([role_staff, role_teacher])

		# collect ucschool objects for those users to delete in imported_users
		users_to_delete = list()
		for user in (ucs_students - imported_users):
			users_to_delete.append(a_student.get_by_import_id(self.connection, user[0], user[1]))
		for user in (ucs_staff - imported_users):
			users_to_delete.append(a_staff.get_by_import_id(self.connection, user[0], user[1]))
		for user in (ucs_teachers - imported_users):
			users_to_delete.append(a_teacher.get_by_import_id(self.connection, user[0], user[1]))
		for user in (ucs_teachers_staff - imported_users):
			users_to_delete.append(a_staff_teacher.get_by_import_id(self.connection, user[0], user[1]))

		for user in users_to_delete:
			# mark for logging/csv-output purposes
			user.action = "D"

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
		if self.dry_run:
			self.logger.info("------ Dry run - not deleting users. ------")
			return
		self.logger.info("------ Deleting users... ------")

		if self.config["no_delete"]:
			# Only create/modify users from input, do not remove users
			# that exist in UCS but not in input.
			self.logger.info("Option 'no_delete' ist set, not deleting users missing in input.")
			return

		self.logger.info("Deleting %d users...", len(users))
		for user in users:
			try:
				self.pre_delete_hook(user)
				success = self.do_delete(user)
				if success:
					self.logger.info("Success deleting user %r (source_uid:%s record_uid: %s).", user.name,
						user.source_uid, user.record_uid)
				else:
					raise DeletionError("Error deleting user '{}' (source_uid:{} record_uid: {}), has probably already "
						"been deleted.".format(user.name, user.source_uid, user.record_uid), entry=user.entry_count,
						import_user=user)
				self.deleted_users[user.__class__.__name__].append(user)
				self.post_delete_hook(user)
			except UcsSchoolImportError as exc:
				self.logger.exception("Error in entry #%d: %s",  exc.entry, exc)
				self._add_error(exc)
		self.logger.info("------ Deleted %d users. ------", len(self.deleted_users))
		return self.errors, self.deleted_users

	def do_delete(self, user):
		"""
		Delete or deactivate a user.
		IMPLEMENTME to add or change a deletion variant.

		:param user: ImportUser
		:return bool: whether the deletion worked
		"""
		user_udm = user.get_udm_object(self.connection)
		if self.config["user_deletion"]["delete"] and not self.config["user_deletion"]["expiration"]:
			# delete user right now
			self.logger.info("Deleting user %s...", user)
			success = user.remove(self.connection)
		elif self.config["user_deletion"]["delete"] and self.config["user_deletion"]["expiration"]:
			# set expiration date, don't delete, don't deactivate
			expiry = datetime.datetime.now() + datetime.timedelta(days=self.config["user_deletion"]["expiration"])
			expiry_str = expiry.strftime("%Y-%m-%d")
			self.logger.info("Setting account expiration date of %s to %s...", user, expiry_str)
			user.expire(self.connection, expiry_str)
			success = True
		elif not self.config["user_deletion"]["delete"] and self.config["user_deletion"]["expiration"]:
			# don't delete but deactivate with an expiration data
			expiry = datetime.datetime.now() + datetime.timedelta(days=self.config["user_deletion"]["expiration"])
			expiry_str = expiry.strftime("%Y-%m-%d")
			self.logger.info("Setting account expiration date of %s to %s...", user, expiry_str)
			user.expire(self.connection, expiry_str)
			self.logger.info("Deactivating user %s...", user)
			user.deactivate()
			user.modify()
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

	def pre_create_hook(self, user):
		"""
		Run code before creating a user.

		IMPLEMENT ME if you want to do something before creating a user.
		You'll have full access to the data being saved to LDAP.
		It is much faster than running executables from
		/usr/share/ucs-school-import/hooks/*.

		* The ImportUser does not exist in LDAP, yet. user.dn will be the DN
		of the user, if username and school does not change.
		* Use self.connection if you need a LDAP connection.

		:param user: ImportUser
		:return: None
		"""
		pass

	def post_create_hook(self, user):
		"""
		Run code after creating a user.

		IMPLEMENT ME if you want to do something after creating a user.
		It is much faster than running executables from
		/usr/share/ucs-school-import/hooks/*.

		* The hook is only executed if adding the user succeeded.
		* The user will be a opened ImportUser, loaded from LDAP.
		* Use self.connection if you need a LDAP connection.

		:param user: ImportUser
		:return: None
		"""
		pass

	def pre_modify_hook(self, user):
		"""
		Run code before modifying a user.

		IMPLEMENT ME if you want to do something before modifying a user.
		It is much faster than running executables from
		/usr/share/ucs-school-import/hooks/*.

		* The user will be a opened ImportUser, loaded from LDAP.
		* Use self.connection if you need a LDAP connection.

		:param user: ImportUser
		:return: None
		"""
		pass

	def post_modify_hook(self, user):
		"""
		Run code after modifying a user.

		IMPLEMENT ME if you want to do something after modifying a user.
		It is much faster than running executables from
		/usr/share/ucs-school-import/hooks/*.

		* The hook is only executed if modifying the user succeeded.
		* The user will be a opened ImportUser, loaded from LDAP.
		* Use self.connection if you need a LDAP connection.

		:param user: ImportUser
		:return: None
		"""
		pass

	def pre_delete_hook(self, user):
		"""
		Run code before deleting a user.

		IMPLEMENT ME if you want to do something before deleting a user.
		You'll have full access to the data still saved in LDAP.
		It is much faster than running executables from
		/usr/share/ucs-school-import/hooks/*.

		* user is a opened ImportUser, loaded from LDAP.
		* Use self.connection if you need a LDAP connection.

		:param user: ImportUser
		:return: None
		"""
		pass

	def post_delete_hook(self, user):
		"""
		Run code after deleting a user.

		IMPLEMENT ME if you want to do something after deleting a user.
		You'll have full access to the data that does not exist in LDAP
		anymore.
		It is much faster than running executables from
		/usr/share/ucs-school-import/hooks/*.

		* The hook is only executed if the deleting the user succeeded.
		* user is a opened ImportUser, loaded from LDAP.
		* Depending on self.config["user_deletion"]["delete"] and
		self.config["user_deletion"]["expiration"] the user may not have been
		deleted, but merely deactivated.
		* Use self.connection if you need a LDAP connection.

		:param user: ImportUser
		:return: None
		"""
		pass

	def _add_error(self, err):
		self.errors.append(err)
		if len(self.errors) > self.config["tolerate_errors"]:
			raise ToManyErrors("More than {} errors.".format(self.config["tolerate_errors"]), self.errors)
