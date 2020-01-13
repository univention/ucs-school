#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
#  Check App version
#
# Copyright 2016-2020 Univention GmbH
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

import sys
from distutils.version import LooseVersion
from univention.appcenter.actions import get_action
from univention.appcenter.app_cache import Apps
from univention.appcenter.ucr import ucr_get, ucr_is_true


if len(sys.argv) < 2 or sys.argv[-1] == '-v':
	print('Usage: {} [-v] <app name>'.format(sys.argv[0]))
	sys.exit(2)
app_name = sys.argv[-1]

hostname_master = ucr_get('ldap/master').split('.')[0]
app = Apps().find(app_name)
if app is None:
	print('Unknown app "{}".'.format(app_name))
	sys.exit(2)
domain = get_action('domain')
info = domain.to_dict([app])[0]

if not app.is_installed():
	print('App "{}" is not installed on this host.'.format(app_name))
	sys.exit(2)

try:
	master_version = info['installations'][hostname_master]['version']
	if master_version is None:
		raise KeyError
except KeyError:
	print('App "{}" is not installed on DC master.'.format(app_name))
	sys.exit(2)

ret = LooseVersion(app.version) > LooseVersion(master_version)

if '-v' in sys.argv:
	print('Version of app "{}" on this host: "{}"'.format(app_name, app.version))
	print('Version of app "{}" on DC master: "{}"'.format(app_name, master_version))
	if ret:
		print('Error: local version of app "{}" higher than DC masters versions!'.format(app_name))
	else:
		print('OK: local version of app "{}" is lower or equal to that of the DC master.'.format(app_name))

ucrv = 'ucsschool/join/ignore-version-mismatch/{}/{}'.format(master_version, app.version)
if ucr_is_true(ucrv):
	if '-v' in sys.argv:
		print('Ignoring version mismatch, because "{}" is set.'.format(ucrv))
	sys.exit(0)

sys.exit(int(ret))
