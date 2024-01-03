# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2024 Univention GmbH
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
from functools import partial

import lazy_object_proxy
from six import iteritems

import univention.admin.modules as udm_modules

from .attributes import Attribute

try:
    from typing import Any, Dict
except ImportError:
    pass


# load UDM modules see Bug #51717
udm_modules.update()


class UCSSchoolHelperOptions(object):
    def __init__(self, klass, meta=None):
        self.set_from_meta_object(meta, "udm_module", None)
        self.set_from_meta_object(meta, "udm_filter", "")
        self.set_from_meta_object(meta, "name_is_unique", False)
        self.set_from_meta_object(meta, "allow_school_change", False)
        self.set_from_meta_object(meta, "ignore_meta", False)
        udm_module_short = None
        if self.udm_module:
            udm_module_short = self.udm_module.split("/")[1]
        self.set_from_meta_object(meta, "udm_module_short", udm_module_short)
        self.set_from_meta_object(
            meta, "hook_path", udm_module_short
        )  # default same as udm_module_short
        if self.udm_module:
            module = udm_modules.get(self.udm_module)
            if not module:
                # happens when the udm_module is not in the standard package
                #   i.e. computers/ucc
                return
            for key, attr in iteritems(klass._attributes):
                # sanity checks whether we specified everything correctly
                if attr.udm_name and not attr.extended:
                    # extended? only available after module_init(lo)
                    #   we have to trust ourselved here
                    if attr.udm_name not in module.property_descriptions:
                        raise RuntimeError(
                            "%s's attribute \"%s\" has no counterpart in the %s's property_descriptions "
                            '("%s")!' % (klass.__name__, key, self.udm_module, attr.udm_name)
                        )
            udm_name = klass._attributes["name"].udm_name
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
            self.ldap_name_part = "cn"
            self.ldap_map_function = lambda name: name
            self.ldap_unmap_function = lambda name: name

    def set_from_meta_object(self, meta, name, default):
        setattr(self, name, getattr(meta, name, default))


class UCSSchoolHelperMetaClass(type):
    def __new__(mcs, cls_name, bases, attrs):
        attributes = {}
        meta = None

        def scan_class_attributes(class_attrs):  # type: (Dict[str, Any]) -> None
            # side effect: changes "attributes" dict from function scope
            for name, value in iteritems(class_attrs):
                if name in attributes:
                    # allows to remove an attribute from a subclass
                    # hierarchie should better have been architectured differently (e.g. using mixins)
                    del attributes[name]
                if type(value) is lazy_object_proxy.Proxy:
                    # The isinstance() below will access the value and create an InitialisationError in
                    # ImportUser.config and ImportUser.factory, as they are not initialized at import
                    # time. Interestingly type() does not do that.
                    continue
                if isinstance(value, Attribute):
                    attributes[name] = value

        # collect attributes and "Meta" (_meta) from all base classes in the
        # order from most basic to most special
        for base in reversed(bases):
            if hasattr(base, "_meta") and not getattr(base._meta, "ignore_meta", False):
                meta = base._meta
            # works for classes inheriting from UCSSchoolHelperAbstractClass:
            if hasattr(base, "_attributes"):
                attributes.update(base._attributes)
            # works also for mixins:
            scan_class_attributes(vars(base))

        # attributes and "Meta" of top class (the one currently being created)
        # is read last, as it's the "most special"
        meta = attrs.get("Meta") or meta
        scan_class_attributes(attrs)

        cls = super(UCSSchoolHelperMetaClass, mcs).__new__(mcs, cls_name, bases, dict(attrs))
        cls._attributes = attributes
        cls._meta = UCSSchoolHelperOptions(cls, meta)
        cls.logger = lazy_object_proxy.Proxy(
            lambda: logging.getLogger(inspect.getmodule(cls).__name__)
        )  # type: logging.Logger
        return cls
