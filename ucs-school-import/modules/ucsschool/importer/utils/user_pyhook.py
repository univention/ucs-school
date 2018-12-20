# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
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
Base class for all Python based User hooks.
"""

from ucsschool.importer.utils.import_pyhook import ImportPyHook


class UserPyHook(ImportPyHook):
	"""
	Base class for Python based user import hooks.

	An example is provided in /usr/share/doc/ucs-school-import/hook_example.py

	The base class' :py:meth:`__init__()` provides the following attributes:

	* self.dry_run     # whether hook is executed during a dry-run (1)
	* self.lo          # LDAP connection object (2)
	* self.logger      # Python logging instance

	If multiple hook classes are found, hook functions with higher
	priority numbers run before those with lower priorities. None disables
	a function (no need to remove it / comment it out).

	(1) Hooks are only executed during dry-runs, if the class attribute
	:py:attr:`supports_dry_run` is set to `True` (default is `False`). Hooks
	with `supports_dry_run == True` should not modify LDAP objects.
	Therefore the LDAP connection object self.lo will be a read-only connection
	during a dry-run.
	(2) Read-write cn=admin connection in a real run, read-only cn=admin
	connection during a dry-run.
	"""
	priority = {
		"pre_create": None,
		"post_create": None,
		"pre_modify": None,
		"post_modify": None,
		"pre_move": None,
		"post_move": None,
		"pre_remove": None,
		"post_remove": None,
	}

	def pre_create(self, user):
		"""
		Run code before creating a user.

		* The user does not exist in LDAP, yet.
		* `user.dn` is the future DN of the user, if username and school does not change.
		* `user.input_data` contains the (csv) input data, if the user was create during an import job
		* set `priority["pre_create"]` to an `int`, to enable this method

		:param ImportUser user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""

	def post_create(self, user):
		"""
		Run code after creating a user.

		* The hook is only executed if adding the user succeeded.
		* `user` will be an :py:class:`ImportUser`, loaded from LDAP.
		* Do not run :py:meth:`user.modify()`, it will create a recursion. Please use :py:meth:`user.modify_without_hooks()`.
		* set `priority["post_create"]` to an int, to enable this method

		:param ImportUser user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""

	def pre_modify(self, user):
		"""
		Run code before modifying a user.

		* `user` will be a :py:class:`ImportUser`, loaded from LDAP.
		* set `priority["pre_modify"]` to an int, to enable this method

		:param ImportUser user: User (or a subclass of it, eg. :py:class:`ImportUser`)
		:return: None
		"""

	def post_modify(self, user):
		"""
		Run code after modifying a user.

		* The hook is only executed if modifying the user succeeded.
		* `user` will be an :py:class:`ImportUser`, loaded from LDAP.
		* Do not run :py:meth:`user.modify()`, it will create a recursion. Please use :py:meth:`user.modify_without_hooks()`.
		* If running in an import job, the user may not have been removed, but merely deactivated. If `user.udm_properties["ucsschoolPurgeTimestamp"]` is set, the user is marked for removal.
		* set `priority["post_modify"]` to an `int`, to enable this method

		:param ImportUser user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""

	def pre_move(self, user):
		"""
		Run code before changing a users primary school (position).

		* `user` will be an :py:class:`ImportUser`, loaded from LDAP.
		* set `priority["pre_move"]` to an `int`, to enable this method

		:param ImportUser user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""

	def post_move(self, user):
		"""
		Run code after changing a users primary school (position).

		* The hook is only executed if moving the user succeeded.
		* `user` will be an :py:class:`ImportUser`, loaded from LDAP.
		* Do not run :py:meth:`user.modify()`, it will create a recursion. Please use :py:meth:`user.modify_without_hooks()`.
		* set `priority["post_move"]` to an `int`, to enable this method

		:param ImportUser user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""

	def pre_remove(self, user):
		"""
		Run code before deleting a user.

		* `user` will be an :py:class:`ImportUser`, loaded from LDAP.
		* set `priority["pre_remove"]` to an `int`, to enable this method

		:param ImportUser user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""

	def post_remove(self, user):
		"""
		Run code after deleting a user.

		* The hook is only executed if the deleting the user succeeded.
		* `user` will be an :py:class:`ImportUser`, loaded from LDAP.
		* The user was removed, do not try to :py:meth:`modify()` it.
		* set `priority["post_remove"]` to an `int`, to enable this method

		:param ImportUser user: User (or a subclass of it, eg. ImportUser)
		:return: None
		"""
