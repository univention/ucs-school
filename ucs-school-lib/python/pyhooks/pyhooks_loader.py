# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Loader for Python based hooks.
"""
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

import imp
import inspect
from os import listdir
import os.path
from collections import defaultdict

try:
	from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar
	import logging.Logger
	from ucsschool.lib.pyhooks import PyHook
	PyHookTV = TypeVar('PyHookTV', bound=PyHook)
except ImportError:
	pass


class PyHooksLoader(object):
	"""
	Loader for PyHooks.

	Use get_hook_objects() to get initialized and sorted objects.
	Use get_hook_classes() if you want to initialize them yourself.
	"""

	# Dict[base_class_name, List[Class]]
	_hook_classes = {}  # type: Dict[str, List[PyHookTV]]

	def __init__(self, base_dir, base_class, logger, filter_func=None):
		# type: (str, Type[PyHookTV], logging.Logger, Optional[Callable[[Type[PyHookTV]], bool]]) -> None
		"""

		Hint: if you wish to pass a logging instance to a hook, add it to the
		arguments list of :py:meth:`get_hook_objects()` and receive it in the
		hooks :py:meth:`__init__()` method.

		If `filter_func` is a callable, it will be passed each class that is
		considered for loading and it can decide if it should be loaded or not.
		Thus its signature is `(type) -> bool`.

		:param str base_dir: path to a directory containing Python files
		:param type base_class: only subclasses of this class will be imported
		:param logging.Logger logger: Python logging instance to use for loader logging
		:param Callable filter_func: function that takes a class and returns a bool
		"""
		self.base_dir = base_dir
		self.base_class = base_class
		self.base_class_name = base_class.__name__
		self.logger = logger
		if filter_func:
			assert callable(filter_func), "'filter_func' must be a callable, got {!r}.".format(filter_func)
		self._filter_func = filter_func
		self._pyhook_obj_cache = None

	def drop_cache(self):  # type: () -> None
		"""
		Drop the cache of loaded hook classes and force a rerun of the
		filesystem search, next time get_hook_classes() or get_pyhook_objects()
		is called.

		:return: None
		"""
		self._pyhook_obj_cache = None
		if self.base_class_name in self._hook_classes:
			del self._hook_classes[self.base_class_name]

	def get_hook_classes(self):  # type: () -> List[PyHookTV]
		"""
		Search hook files in filesystem and load classes.
		No objects are initialized, no sorting is done.

		:return: list of PyHook subclasses
		:rtype: list[type]
		"""
		if self._hook_classes.get(self.base_class_name) is None:
			self.logger.info("Searching for hooks of type %r in: %s...", self.base_class_name, self.base_dir)
			self._hook_classes[self.base_class_name] = list()
			if self._filter_func:
				filter_func = self._filter_func
			else:
				filter_func = lambda x: True
			for filename in listdir(self.base_dir):
				if filename.endswith(".py") and os.path.isfile(os.path.join(self.base_dir, filename)):
					info = imp.find_module(filename[:-3], [self.base_dir])
					a_class = self._load_hook_class(filename[:-3], info, self.base_class)
					if a_class:
						if filter_func(a_class):
							self._hook_classes[self.base_class_name].append(a_class)
						else:
							self.logger.info("Hook class %r filtered out by %s().", a_class.__name__, filter_func.func_name)
			self.logger.info("Found hook classes: %s", ", ".join(c.__name__ for c in self._hook_classes[self.base_class_name]))
		return self._hook_classes[self.base_class_name]

	def get_hook_objects(self, *args, **kwargs):  # type: (*Any, **Any) -> List[PyHookTV]
		"""
		Get hook classes, initialize objects and sort by method and priority.

		:param tuple args: arguments to pass to __init__ of hooks
		:param  dict kwargs: arguments to pass to __init__ of hooks
		:return: initialized hook objects, sorted by method and method-priority
		:rtype: Dict[List[ucsschool.lib.pyhooks.PyHook]]
		"""
		if self._pyhook_obj_cache is None:
			pyhook_objs = [pyhook_cls(*args, **kwargs) for pyhook_cls in self.get_hook_classes()]

			# fill cache: find all enabled hook methods
			methods = defaultdict(list)
			for pyhook_obj in pyhook_objs:
				if not hasattr(pyhook_obj, "priority") or not isinstance(pyhook_obj.priority, dict):
					self.logger.warn('Ignoring hook %r without/invalid "priority" attribute.', pyhook_obj)
					continue
				for meth_name, prio in pyhook_obj.priority.items():
					if hasattr(pyhook_obj, meth_name) and isinstance(pyhook_obj.priority.get(meth_name), int):
						methods[meth_name].append((getattr(pyhook_obj, meth_name), pyhook_obj.priority[meth_name]))
					elif hasattr(pyhook_obj, meth_name) and pyhook_obj.priority.get(meth_name) is None:
						pass
					else:
						self.logger.warn('Ignoring invalid priority item (%r : %r).', meth_name, prio)
			# sort by priority
			self._pyhook_obj_cache = dict()
			for meth_name, meth_list in methods.items():
				self._pyhook_obj_cache[meth_name] = [x[0] for x in sorted(meth_list, key=lambda x: x[1], reverse=True)]

			self.logger.info("Loaded hooks: %r.", dict([(meth_name, ["{}.{}".format(m.im_class.__name__, m.im_func.func_name) for m in meths]) for meth_name, meths in self._pyhook_obj_cache.items()]))
		return self._pyhook_obj_cache

	@staticmethod
	def _load_hook_class(cls_name, info, super_class):
		# type: (str, Tuple[file, str, Tuple[str, str, int]], Type[PyHookTV]) -> Optional[Type[PyHookTV]]
		res = imp.load_module(cls_name, *info)
		for thing in dir(res):
			candidate = getattr(res, thing)
			if inspect.isclass(candidate) and issubclass(candidate, super_class) and candidate is not super_class:
				return candidate
		return None
