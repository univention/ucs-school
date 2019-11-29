# -*- coding: iso-8859-15 -*-
#
# Copyright 2014-2019 Univention GmbH
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
Role specific shares
"""

import os

from ucsschool.lib.i18n import ucs_school_name_i18n
from ucsschool.lib.roles import role_pupil, role_staff, role_teacher

try:
	from typing import Optional
	from univention.config_registry import ConfigRegistry
except ImportError:
	pass


def roleshare_name(role, school_ou, ucr):  # type: (str, str, ConfigRegistry) -> str
	custom_roleshare_name = ucr.get('ucsschool/import/roleshare/%s' % (role,))
	if custom_roleshare_name:
		return custom_roleshare_name
	else:
		return '-'.join((ucs_school_name_i18n(role), school_ou))


def roleshare_path(role, school_ou, ucr):  # type: (str, str, ConfigRegistry) -> str
	custom_roleshare_path = ucr.get('ucsschool/import/roleshare/%s/path' % (role,))
	if custom_roleshare_path:
		return custom_roleshare_path
	else:
		return os.path.join(school_ou, ucs_school_name_i18n(role))


def roleshare_home_subdir(school_ou, roles, ucr=None):  # type: (str, str, Optional[ConfigRegistry]) -> str
	if not ucr:
		from .models.utils import ucr

	if ucr.is_true('ucsschool/import/roleshare', True):
		for role in (role_pupil, role_teacher, role_staff):
			if role in roles:
				return roleshare_path(role, school_ou, ucr)
	return ''
