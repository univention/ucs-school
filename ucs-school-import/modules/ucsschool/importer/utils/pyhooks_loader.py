# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Loader for Python based hooks.
"""
# Copyright 2016 Univention GmbH
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

import imp
import inspect
from os import listdir
import os.path

from ucsschool.importer.utils.logging2udebug import get_logger


class PyHooksLoader(object):
	def __init__(self, base_dir, base_class):
		self.base_dir = base_dir
		self.base_class = base_class
		self.logger = get_logger()
		self._plugins = None

	def get_plugins(self):
		if self._plugins:
			return self._plugins
		self.logger.info("Searching for plugins in: %s...", self.base_dir)
		self._plugins = list()
		for filename in listdir(self.base_dir):
			if filename.endswith(".py") and os.path.isfile(os.path.join(self.base_dir, filename)):
				info = imp.find_module(filename[:-3], [self.base_dir])
				plugin = self._load_plugin(filename[:-3], info, self.base_class)
				if plugin:
					self._plugins.append(plugin)
		self.logger.info("Found plugins: %r", self._plugins)
		return self._plugins

	@classmethod
	def _load_plugin(cls, cls_name, info, super_class):
		res = imp.load_module(cls_name, *info)
		for thing in dir(res):
			candidate = getattr(res, thing)
			if inspect.isclass(candidate) and issubclass(candidate, super_class) and candidate is not super_class:
				return candidate
		return None
