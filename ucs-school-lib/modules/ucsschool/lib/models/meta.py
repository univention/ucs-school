# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2021 Univention GmbH
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
from typing import Any, Dict

import lazy_object_proxy
from six import iteritems

from .attributes import Attribute


class UCSSchoolHelperOptions(object):
    def __init__(self, klass, meta=None):
        self.set_from_meta_object(meta, "udm_module", None)
        self.set_from_meta_object(meta, "udm_filter", "")
        self.set_from_meta_object(meta, "name_is_unique", False)
        self.set_from_meta_object(meta, "allow_school_change", False)
        # Manually set cls.meta.ldap_name_part, because we cannot ask UDM, 'cn' is the default,
        # overwrite it in classes that use something else, like User (uid) and School (ou). Used in
        # UCSSchoolHelperAbstractClass.dn() to calculate the DN of school objects:
        self.set_from_meta_object(meta, "ldap_name_part", "cn")
        self.set_from_meta_object(meta, "ignore_meta", False)
        udm_module_short = None
        if self.udm_module:
            udm_module_short = self.udm_module.split("/")[1]
        self.set_from_meta_object(meta, "udm_module_short", udm_module_short)

    def set_from_meta_object(self, meta, name, default):
        setattr(self, name, getattr(meta, name, default))


class UCSSchoolHelperMetaClass(type):
    def __new__(mcs, cls_name, bases, attrs):
        attributes = {}
        meta = None

        def scan_class_attributes(class_attrs: Dict[str, Any]) -> None:
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
        cls.logger: logging.Logger = lazy_object_proxy.Proxy(
            lambda: logging.getLogger(inspect.getmodule(cls).__name__)
        )
        return cls
