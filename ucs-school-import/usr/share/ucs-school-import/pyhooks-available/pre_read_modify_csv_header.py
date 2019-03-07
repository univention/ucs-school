# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2019 Univention GmbH
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
Base class for all Python based pre-read hooks.
"""

from ucsschool.importer.utils.import_pyhook import ImportPyHook
from ucsschool.importer.configuration import Configuration
try:
	import typing
	from ucsschool.importer.configuration import ReadOnlyDict
except ImportError:
	pass


class PreReadPyHook(ImportPyHook):
	"""
	Hook that is called before starting to read the input file.

	* self.lo          # LDAP object
	* self.logger      # Python logging instance
	* self.config      # read-only import configuration

	If multiple hook classes are found, hook functions with higher
	priority numbers run before those with lower priorities. None disables
	a function.
	"""
	priority = {
		'pre_read': None,
	}

	def __init__(self, lo=None, dry_run=False, *args, **kwargs):
		super(PreReadPyHook, self).__init__(lo, dry_run, *args, **kwargs)
		self.config = Configuration()  # type: ReadOnlyDict

	def pre_read(self):  # type: () -> None
		"""
		Run code before starting to read the input file.

		:return: None
		"""
		return None
