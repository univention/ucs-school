# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Diverse helper functions.
"""
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

import os
import os.path
import pwd
import grp
import univention.admin.modules


__udm_prop_to_ldap_attr_cache = {}


def mkdir_p(dir_name, user, group, mode):
	"""
	Recursively create directories (like "mkdir -p").

	:param str dir_name: path to create
	:param str user: username of owner of new directories
	:param str group: group name for ownership of new directories
	:param octal mode: permission bits to set for new directories
	:returns: None
	:rtype: None
	"""
	if not dir_name:
		return

	uid = pwd.getpwnam(user).pw_uid
	gid = grp.getgrnam(group).gr_gid
	parent = os.path.dirname(dir_name)

	if not os.path.exists(parent):
		mkdir_p(parent, user, group, mode)

	if not os.path.exists(dir_name):
		os.mkdir(dir_name, mode)
		os.chown(dir_name, uid, gid)


def get_ldap_mapping_for_udm_property(udm_prop, udm_type):
	"""
	Get the name of the LDAP attribute, a UDM property is mapped to.

	:param str udm_prop: name of UDM property
	:param str udm_type: name of UDM module (e.g. 'users/user')
	:returns: name of LDAP attribute or empty str if no mapping was found
	:rtype str
	"""
	return univention.admin.modules.get(udm_type).mapping.mapName(udm_prop)
