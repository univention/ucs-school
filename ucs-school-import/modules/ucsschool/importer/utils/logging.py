# -*- coding: utf-8 -*-
#
# Copyright 2016-2019 Univention GmbH
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
Central place to get logger for import.
"""

from __future__ import absolute_import
import logging
from ucsschool.lib.models.utils import get_file_handler, UniFileHandler, UniStreamHandler

try:
	from typing import Optional
except ImportError:
	pass


def get_logger():  # type: () -> logging.Logger
	"""
	Get a logging instance with name `ucsschool`.

	.. deprecated:: 4.4 v2
		Use `logging.getLogger(__name__)` and :py:func:`get_stream_handler()`,
		:py:func:`get_file_handler()`.

	:return: Logger
	:rtype: logging.Logger
	"""
	logger = logging.getLogger('ucsschool.import')
	logger.warn('get_logger() is deprecated, use "logging.getLogger(__name__)" instead.')
	return logger


def make_stdout_verbose():  # type: () -> logging.Logger
	logger = logging.getLogger('ucsschool.import')
	for handler in logger.handlers:
		if isinstance(handler, UniStreamHandler):
			handler.setLevel(logging.DEBUG)
	return logger


def add_file_handler(filename, uid=None, gid=None, mode=None):
	# type: (str, Optional[int], Optional[int], Optional[int]) -> logging.Logger
	if filename.endswith(".log"):
		info_filename = "{}.info".format(filename[:-4])
	else:
		info_filename = "{}.info".format(filename)
	logger = logging.getLogger('ucsschool.import')
	if not any(isinstance(handler, UniFileHandler) for handler in logger.handlers):
		logger.addHandler(get_file_handler('DEBUG', filename, uid, gid, mode))
		# TODO: bug to remove INFO file, or only create >=WARN/ERROR
		logger.addHandler(get_file_handler('INFO', info_filename, uid, gid, mode))
	return logger


def move_our_handlers_to_lib_logger():  # type: () -> None
	"""
	Move logging handlers from `ucsschool.import` to `ucsschool` logger.

	.. deprecated:: 4.4 v2
		Use `logging.getLogger(__name__)` and :py:func:`get_stream_handler()`,
		:py:func:`get_file_handler()` for the logger hierarchie required.
	"""
	import_logger = logging.getLogger('ucsschool.import')
	import_logger.warn('move_our_handlers_to_lib_logger() is deprecated.')
	school_logger = logging.getLogger('ucsschool')
	for handler in import_logger.handlers:
		school_logger.addHandler(handler)
		import_logger.removeHandler(handler)
