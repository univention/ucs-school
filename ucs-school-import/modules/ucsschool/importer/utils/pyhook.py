# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Base class for all Python based hooks.
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

from ucsschool.lib.models.utils import logger


class PyHook(object):
	def __init__(self, user, lo, when, action):
		self.user = user      # the ImportUser
		self.lo = lo          # LDAP object
		self.logger = logger  # Python logging instance
		self.when = when      # either 'pre' or 'post'
		self.action = action  # one of 'create', 'modify', 'move' or 'remove'

	def run(self):
		"""
		Overwrite this method with the code you wish to run.

		:return: None
		"""
		raise NotImplementedError()
