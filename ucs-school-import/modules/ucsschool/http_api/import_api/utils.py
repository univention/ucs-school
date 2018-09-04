# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2018 Univention GmbH
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
Diverse helper functions.
"""

import pwd
import grp


def get_wsgi_user_group():
	"""
	Get the username and group name of the WSGI process in which the HTTP-API
	runs.

	:return: tuple with username and group name
	:rtype: tuple(str, str)
	"""
	return 'uas-import', 'uas-import'


def get_wsgi_uid_gid():
	"""
	Get the UID and GID of the WSGI process in which the HTTP-API runs.

	:return: tuple with UID and GID
	:rtype: tuple(int, int)
	"""
	user_name, group_name = get_wsgi_user_group()
	return pwd.getpwnam(user_name).pw_uid, grp.getgrnam(group_name).gr_gid
