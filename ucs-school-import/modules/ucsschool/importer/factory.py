# -*- coding: utf-8 -*-
#
# Univention UCS@school
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

"""
Singleton to the factory currently in use.
"""


import importlib

from .exceptions import InitialisationError
try:
	from typing import Optional, Type
	from .default_user_import_factory import DefaultUserImportFactory
except ImportError:
	pass


def setup_factory(factory_cls_name):  # type: (str) -> DefaultUserImportFactory
	"""
	Create import factory.

	:param str factory_cls_name: full dotted name of class
	:return: Factory object
	:rtype: Factory
	"""
	fac_class = load_class(factory_cls_name)
	factory = Factory(fac_class())  # type: DefaultUserImportFactory
	return factory


def load_class(dotted_class_name):  # type: (str) -> type
	"""
	Load class from its full dotted name.

	:param dotted_class_name: str: full dotted name of class
	:return: class
	:rtype: type
	"""
	module_path, _, class_name = dotted_class_name.rpartition(".")
	module = importlib.import_module(module_path)
	return getattr(module, class_name)


class Factory(object):
	"""
	Singleton to the global abstract factory object.
	"""
	class __SingleFac:

		def __init__(self, factory):  # type: (Optional[DefaultUserImportFactory]) -> None
			if not factory:
				raise InitialisationError("Concrete factory not yet configured.")
			self.factory = factory

	_instance = None  # type: __SingleFac

	def __new__(cls, factory=None):
		# type: (Type[Factory], Optional[DefaultUserImportFactory]) -> DefaultUserImportFactory
		if not cls._instance:
			cls._instance = cls.__SingleFac(factory)
		return cls._instance.factory
