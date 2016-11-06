#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2016 Univention GmbH
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

from functools import partial

import univention.admin.modules as udm_modules

from ucsschool.lib.models.attributes import Attribute

class UCSSchoolHelperOptions(object):
	def __init__(self, klass, meta=None):
		self.set_from_meta_object(meta, 'udm_module', None)
		self.set_from_meta_object(meta, 'udm_filter', '')
		self.set_from_meta_object(meta, 'name_is_unique', False)
		self.set_from_meta_object(meta, 'allow_school_change', False)
		udm_module_short = None
		if self.udm_module:
			udm_module_short = self.udm_module.split('/')[1]
		self.set_from_meta_object(meta, 'udm_module_short', udm_module_short)
		self.set_from_meta_object(meta, 'hook_path', udm_module_short)  # default same as udm_module_short
		if self.udm_module:
			module = udm_modules.get(self.udm_module)
			if not module:
				# happens when the udm_module is not in the standard package
				#   i.e. computers/ucc
				return
			for key, attr in klass._attributes.iteritems():
				# sanity checks whether we specified everything correctly
				if attr.udm_name and not attr.extended:
					# extended? only available after module_init(lo)
					#   we have to trust ourselved here
					if attr.udm_name not in module.property_descriptions:
						raise RuntimeError('%s\'s attribute "%s" has no counterpart in the %s\'s property_descriptions ("%s")!' % (klass.__name__, key, self.udm_module, attr.udm_name))
			udm_name = klass._attributes['name'].udm_name
			ldap_name = module.mapping.mapName(udm_name)
			self.ldap_name_part = ldap_name
			ldap_map_function = partial(module.mapping.mapValue, udm_name)
			self.ldap_map_function = ldap_map_function
			ldap_unmap_function = partial(module.mapping.unmapValue, module.mapping.mapName(udm_name))
			self.ldap_unmap_function = ldap_unmap_function
		else:
			# this is to not let models fail when accessing obj.dn
			#   note that without an udm_module it is not possible
			#   to save an object
			self.ldap_name_part = 'cn'
			self.ldap_map_function = lambda name: name
			self.ldap_unmap_function = lambda name: name

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
		for name, value in attrs.iteritems():
			if name in attributes:
				del attributes[name]
			if isinstance(value, Attribute):
				attributes[name] = value
		cls = super(UCSSchoolHelperMetaClass, mcs).__new__(mcs, cls_name, bases, dict(attrs))
		cls._attributes = attributes
		cls._meta = UCSSchoolHelperOptions(cls, meta)
		return cls

