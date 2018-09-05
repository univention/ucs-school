# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2018 Univention GmbH
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
Django settings file that gets its content from
/etc/ucsschool-import/settings.py
"""

import os
import imp


if os.environ.get('UCSSCHOOL-SPHINX-DOC-BUILD-PATH'):
	django_settings = {
		'SECRET_KEY': 'abc',
		'INSTALLED_APPS': (
			'django.contrib.admin',
			'django.contrib.auth',
			'django.contrib.contenttypes',
			'django.contrib.sessions',
			'django.contrib.messages',
			'django.contrib.staticfiles',
			'rest_framework',
			'djcelery',
			'django_filters',
			'ucsschool.http_api.import_api',
		),
		'UCSSCHOOL_IMPORT': {
			'logging': {
				'api_datefmt': '%Y-%m-%d %H:%M:%S',
				'api_format': '%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d  %(message)s',
				'api_level': 10,
				'api_logfile': 'http_api.log',
			}
		},
	}
else:
	info = imp.find_module('settings', ['/etc/ucsschool-import'])
	res = imp.load_module('settings', *info)
	django_settings = dict((k, v) for k, v in res.__dict__.items() if k == k.upper())
globals().update(django_settings)
