# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
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

"""
Logging configuration for the HTTP API
"""

from __future__ import absolute_import, unicode_literals
import logging
from django.conf import settings


FILE_HANDLER_NAME = 'http_api.log'

logger = logging.getLogger(__name__)

if FILE_HANDLER_NAME not in [h.name for h in logger.handlers]:
	_file_handler = logging.FileHandler(settings.UCSSCHOOL_IMPORT['logging']['api_logfile'])
	_file_handler.set_name(FILE_HANDLER_NAME)
	_file_handler.setFormatter(logging.Formatter(
		fmt=settings.UCSSCHOOL_IMPORT['logging']['api_format'],
		datefmt=settings.UCSSCHOOL_IMPORT['logging']['api_datefmt']
	))
	_file_handler.setLevel(level=settings.UCSSCHOOL_IMPORT['logging']['api_level'])
	logger.addHandler(_file_handler)
	logger.setLevel(max(logger.level, _file_handler.level))
