# -*- coding: utf-8 -*-
#
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
Example hook class that moves the directory of class shares to a backup space,
when they are deleted.

Copy to /usr/share/ucs-school-import/pyhooks to activate it.
"""

import os
import shutil
import datetime
from ucsschool.lib.models.hook import Hook
from ucsschool.lib.models import ClassShare


BACKUP_BASE_PATH = '/var/backups/class_shares'


class ClassShareExampleHook(Hook):
	model = ClassShare
	priority = {
		"pre_create": None,
		"post_create": None,
		"pre_modify": None,
		"post_modify": None,
		"pre_move": None,
		"post_move": None,
		"pre_remove": None,
		"post_remove": 100,
	}

	def post_remove(self, obj):
		"""
		Move directory of class share to backup space.

		:param ClassShare obj: the ClassShare instance, that was just deleted from LDAP
		:return: None
		"""
		share_path = obj.get_share_path()
		target = os.path.join(
			BACKUP_BASE_PATH,
			'{}_{}'.format(datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S'), os.path.basename(share_path))
		)
		if os.path.isdir(share_path):
			if not os.path.isdir(BACKUP_BASE_PATH):
				self.logger.info('Creating backup path %r...', BACKUP_BASE_PATH)
				os.mkdir(BACKUP_BASE_PATH, 0o700)
				os.chown(BACKUP_BASE_PATH, 0, 0)

			self.logger.info('Moving %r of class share %r to %r...', share_path, obj, target)
			shutil.move(share_path, target)
			os.chown(target, 0, 0)
		else:
			self.logger.info('Directory %r of class share %r does not exist.', share_path, obj)
