# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
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

import inspect
import logging

import lazy_object_proxy
import six

from .attributes import Attribute


class UCSSchoolHelperOptions(object):

	def __init__(self, klass, meta=None):
		self.set_from_meta_object(meta, 'udm_module', None)
		self.set_from_meta_object(meta, 'udm_filter', '')
		self.set_from_meta_object(meta, 'name_is_unique', False)
		self.set_from_meta_object(meta, 'allow_school_change', False)
		self.set_from_meta_object(meta, 'ldap_name_part', 'cn')
		udm_module_short = None
		if self.udm_module:
			udm_module_short = self.udm_module.split('/')[1]
		self.set_from_meta_object(meta, 'udm_module_short', udm_module_short)

	def set_from_meta_object(self, meta, name, default):
		setattr(self, name, getattr(meta, name, default))


class UCSSchoolHelperMetaClass(type):

	def __new__(mcs, cls_name, bases, attrs):
		attributes = {}
		meta = attrs.get('Meta')
		for base in bases:
			if hasattr(base, '_attributes'):
				attributes.update(base._attributes)
			if meta is None and hasattr(base, '_meta'):
				meta = base._meta
		for name, value in six.iteritems(attrs):
			if name in attributes:
				del attributes[name]
			if isinstance(value, Attribute):
				attributes[name] = value
		cls = super(UCSSchoolHelperMetaClass, mcs).__new__(mcs, cls_name, bases, dict(attrs))
		cls._attributes = attributes
		cls._meta = UCSSchoolHelperOptions(cls, meta)
		cls.logger: logging.Logger = lazy_object_proxy.Proxy(lambda: logging.getLogger(inspect.getmodule(cls).__name__))
		return cls
