# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Base class for all Python based exam user hooks.
"""
# Copyright 2017-2019 Univention GmbH
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

from ucsschool.importer.utils.import_pyhook import ImportPyHook


class ExamUserPyHook(ImportPyHook):
	"""
	See docstring of :py:class:`ucsschool.importer.utils.import_pyhook.ImportPyHook`
	to learn about the attributes available to the hooks methods.
	"""

	# If multiple hook classes are found, hook functions with higher
	# priority numbers run before those with lower priorities. None disables
	# a function.
	priority = {
		"pre_create": None,
		# "post_create": None,
		# "pre_remove": None,
		# "post_remove": None,
	}

	def pre_create(self, user_dn, al):
		"""
		Run code before creating an exam user.

		* The user does not exist in LDAP, yet.
		* set priority["pre_create"] to an int, to enable this method

		:param user_dn: str: the future DN of the user
		:param al: list of 2-tuples: ldapadd list
		:return: list of 2-tuples: modified ldapadd list
		"""

	# def post_create(self, user):
	# 	"""
	# 	Run code after creating an exam user.
	#
	# 	* The hook is only executed if adding the user succeeded.
	# 	* set priority["post_create"] to an int, to enable this method
	#
	# 	:param user: ExamStudent, loaded from LDAP
	# 	:return: None
	# 	"""
	#
	# def pre_remove(self, user):
	# 	"""
	# 	Run code before deleting an exam user.
	#
	# 	* set priority["post_create"] to an int, to enable this method
	#
	# 	:param user: ExamStudent, loaded from LDAP
	# 	:return: None
	# 	"""
	#
	# def post_remove(self, user):
	# 	"""
	# 	Run code after deleting an exam user.
	#
	# 	* The hook is only executed if deleting the user succeeded.
	# 	* "user" will be an ExamStudent, loaded from LDAP - that does not
	# 	exist anymore - do not modify() it!
	# 	* set priority["post_remove"] to an int, to enable this method
	#
	# 	:param user: ExamStudent
	# 	:return: None
	# 	"""
