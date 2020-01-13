# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2018-2020 Univention GmbH
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

from contextlib import contextmanager
import univention.admin.modules


def get_ldap_mapping_for_udm_property(udm_prop, udm_type):
	"""
	Get the name of the LDAP attribute, a UDM property is mapped to.

	:param str udm_prop: name of UDM property
	:param str udm_type: name of UDM module (e.g. 'users/user')
	:returns: name of LDAP attribute or empty str if no mapping was found
	:rtype: str
	"""
	return univention.admin.modules.get(udm_type).mapping.mapName(udm_prop)


@contextmanager
def nullcontext():
	"""Context manager that does nothing."""
	yield None
