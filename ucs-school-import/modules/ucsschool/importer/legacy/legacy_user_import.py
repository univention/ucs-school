# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2019 Univention GmbH
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
Legacy mass import class.
"""

import copy
from univention.admin.uexceptions import noObject
from ..mass_import.user_import import UserImport
from ..exceptions import CreationError, DeletionError, UnknownAction


class LegacyUserImport(UserImport):

	def detect_users_to_delete(self):
		"""
		No need to compare input and LDAP. Action was written in the CSV file
		and is already stored in user.action.
		"""
		self.logger.info("------ Detecting which users to delete... ------")
		users_to_delete = list()
		for user in self.imported_users:
			if user.action == "D":
				try:
					users_to_delete.append((user.source_uid, user.record_uid, user.input_data))
				except noObject:
					msg = "User to delete not found in LDAP: {}.".format(user)
					self.logger.error(msg)
					self._add_error(DeletionError(msg, entry_count=user.entry_count, import_user=user))
		return users_to_delete

	async def determine_add_modify_action(self, imported_user):
		"""
		Determine what to do with the ImportUser. Should set attribute "action"
		to either "A" or "M". If set to "M" the returned user must be a opened
		ImportUser from LDAP.
		Run modify preparations here, like school-move etc.

		:param ImportUser imported_user: ImportUser from input
		:return: ImportUser with action set and possibly fetched from LDAP
		:rtype: ImportUser
		"""
		if imported_user.action == "A":
			try:
				user = await imported_user.get_by_import_id_or_username(self.connection, imported_user.source_uid, imported_user.record_uid, imported_user.name)
				if user.disabled != "0" or await user.has_expiry(self.connection) or await user.has_purge_timestamp(self.connection):
					self.logger.info("Found user %r that was previously deactivated or is scheduled for deletion (purge timestamp is non-empty), reactivating user.", user)
					imported_user.old_user = copy.deepcopy(user)
					imported_user.prepare_all(new_user=False)
					# make school move first, reactivate freshly fetched user
					if user.school != imported_user.school:
						user = self.school_move(imported_user, user)
					if self.dry_run:
						self.logger.info("Dry-run: not reactivating.")
					else:
						user.reactivate()
					user.update(imported_user)
					user.action = "M"
				else:
					raise CreationError("User {} (source_uid:{} record_uid: {}) exist, but input demands 'A'.".format(
						imported_user, imported_user.source_uid, imported_user.record_uid),
						entry_count=imported_user.entry_count, import_user=imported_user)
			except noObject:
				# this is expected
				imported_user.prepare_all(new_user=True)
				user = imported_user
		elif imported_user.action == "M":
			try:
				user = await imported_user.get_by_import_id_or_username(self.connection, imported_user.source_uid, imported_user.record_uid, imported_user.name)
				imported_user.old_user = copy.deepcopy(user)
				imported_user.prepare_all(new_user=False)
				if user.school != imported_user.school:
					user = await self.school_move(imported_user, user)
				if user.disabled != "0" or await user.has_expiry(self.connection) or await user.has_purge_timestamp(self.connection):
					self.logger.info("Found user %r that was previously deactivated or is scheduled for deletion (purge timestamp is non-empty), reactivating user.", user)
					if self.dry_run:
						self.logger.info("Dry-run: not reactivating.")
					else:
						user.reactivate()
				user.update(imported_user)
			except noObject:
				imported_user.prepare_all(new_user=True)
				user = imported_user
				user.action = "A"
		elif imported_user.action == "D":
			user = imported_user
		else:
			raise UnknownAction("{} (source_uid:{} record_uid: {}) has unknown action '{}'.".format(
				imported_user, imported_user.source_uid, imported_user.record_uid, imported_user.action),
				entry_count=imported_user.entry_count, import_user=imported_user)
		return user
