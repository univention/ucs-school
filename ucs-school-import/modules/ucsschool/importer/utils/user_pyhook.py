# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Base class for all Python based User hooks.
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

from ucsschool.importer.utils.pyhook import PyHook

#
# An example is provided in /usr/share/doc/ucs-school-import/hook_example.py
#

class UserPyHook(PyHook):
	#
	# The base class' init() provides the following attributes:
	#
	# self.lo          # LDAP object
	# self.logger      # Python logging instance
	#

	# If multiple hook classes are found, hook functions with higher
	# priority numbers run before those with lower priorities. None disables
	# a function.
	priority = {
		"pre_create": None,
		"post_create": None,
		"pre_modify": None,
		"post_modify": None,
		"pre_move": None,
		"post_move": None,
		"pre_delete": None,
		"post_delete": None,
	}

	def pre_create(self, user):
		"""
		Run code before creating a user.

		* The user does not exist in LDAP, yet.
		* user.dn is the future DN of the user, if username and school does
		not change.
		* user.input_data contains the (csv) input data, if the user was
		create during an import job
		* set priority["pre_create"] to an int, to enable this method

		:param user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
		pass

	def post_create(self, user):
		"""
		Run code after creating a user.

		* The hook is only executed if adding the user succeeded.
		* "user" will be an ImportUser, loaded from LDAP.
		* Do not run user.modify(), it will create a recursion. Please use
		user.modify_without_hooks().
		* set priority["post_create"] to an int, to enable this method

		:param user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
		pass

	def pre_modify(self, user):
		"""
		Run code before modifying a user.

		* "user" will be a ImportUser, loaded from LDAP.
		* set priority["pre_modify"] to an int, to enable this method

		:param user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
		pass

	def post_modify(self, user):
		"""
		Run code after modifying a user.

		* The hook is only executed if modifying the user succeeded.
		* "user" will be an ImportUser, loaded from LDAP.
		* Do not run user.modify(), it will create a recursion. Please use
		user.modify_without_hooks().
		* set priority["post_modify"] to an int, to enable this method

		:param user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
		pass

	def pre_move(self, user):
		"""
		Run code before changing a users primary school (position).

		* "user" will be an ImportUser, loaded from LDAP.
		* set priority["pre_move"] to an int, to enable this method

		:param user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
		pass

	def post_move(self, user):
		"""
		Run code after changing a users primary school (position).

		* The hook is only executed if moving the user succeeded.
		* "user" will be an ImportUser, loaded from LDAP.
		* Do not run user.modify(), it will create a recursion. Please use
		user.modify_without_hooks().
		* set priority["post_move"] to an int, to enable this method

		:param user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
		pass

	def pre_delete(self, user):
		"""
		Run code before deleting a user.

		* "user" will be an ImportUser, loaded from LDAP.
		* set priority["pre_delete"] to an int, to enable this method

		:param user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
		pass

	def post_delete(self, user):
		"""
		Run code after deleting a user.

		* The hook is only executed if the deleting the user succeeded.
		* "user" will be an ImportUser, loaded from LDAP.
		* If running in an import job, the user may not have been deleted,
		but merely deactivated. Search using user.dn to find out.
		* If the user was deleted, do not modify() it.
		* set priority["post_delete"] to an int, to enable this method

		:param user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
		pass
