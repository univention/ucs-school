#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# SPDX-FileCopyrightText: 2014-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from typing import TYPE_CHECKING, Optional  # noqa: F401

import univention.admin.modules as udm_modules
import univention.admin.uldap as udm_uldap
from univention.admin.uexceptions import objectExists

from .attributes import ContainerPath
from .base import UCSSchoolHelperAbstractClass
from .utils import _, ucr

if TYPE_CHECKING:
    from .base import LoType  # noqa: F401


class MailDomain(UCSSchoolHelperAbstractClass):
    school = None

    @classmethod
    def get_container(cls, school=None):
        return "cn=domain,cn=mail,%s" % ucr.get("ldap/base")

    class Meta:
        udm_module = "mail/domain"


class OU(UCSSchoolHelperAbstractClass):
    def create_without_hooks(self, lo, validate=True):  # type: (LoType, Optional[bool]) -> bool
        self.logger.info("Creating %r", self)
        pos = udm_uldap.position(ucr.get("ldap/base"))
        pos.setDn(self.position)
        udm_obj = udm_modules.get(self._meta.udm_module).object(None, lo, pos)
        udm_obj.open()
        udm_obj["name"] = self.name
        try:
            self.do_create(udm_obj, lo)
        except objectExists as exc:
            return exc.args[0]  # should return bool???
        else:
            return udm_obj.dn  # should return bool???

    def modify(self, lo, validate=True, move_if_necessary=None):
        # type: (LoType, Optional[bool], Optional[bool]) -> bool
        raise NotImplementedError()

    def remove(self, lo):  # type: (LoType) -> bool
        raise NotImplementedError()

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).schoolDN

    class Meta:
        udm_module = "container/ou"


class Container(OU):
    user_path = ContainerPath(_("User path"), udm_name="userPath")
    computer_path = ContainerPath(_("Computer path"), udm_name="computerPath")
    network_path = ContainerPath(_("Network path"), udm_name="networkPath")
    group_path = ContainerPath(_("Group path"), udm_name="groupPath")
    dhcp_path = ContainerPath(_("DHCP path"), udm_name="dhcpPath")
    policy_path = ContainerPath(_("Policy path"), udm_name="policyPath")
    share_path = ContainerPath(_("Share path"), udm_name="sharePath")
    printer_path = ContainerPath(_("Printer path"), udm_name="printerPath")

    class Meta:
        udm_module = "container/cn"
