#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# SPDX-FileCopyrightText: 2014-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import ldap

from .attributes import EmptyAttributes
from .base import UCSSchoolHelperAbstractClass
from .utils import _


class Policy(UCSSchoolHelperAbstractClass):
    @classmethod
    def get_container(cls, school):
        return cls.get_search_base(school).policies

    def attach(self, obj, lo):
        # add univentionPolicyReference if neccessary
        oc = lo.get(obj.dn, ["objectClass"])
        if b"univentionPolicyReference" not in oc.get("objectClass", []):
            try:
                lo.modify(obj.dn, [("objectClass", [], b"univentionPolicyReference")])
            except ldap.LDAPError:
                self.logger.warning("Objectclass univentionPolicyReference cannot be added to %r", obj)
                return
        # add the missing policy
        pl = lo.get(obj.dn, ["univentionPolicyReference"])
        self.logger.info("Attaching %r to %r", self, obj)
        if not any(
            self.dn.lower() == x.decode("UTF-8").lower() for x in pl.get("univentionPolicyReference", [])
        ):
            modlist = [("univentionPolicyReference", [], self.dn.encode("utf-8"))]
            try:
                lo.modify(obj.dn, modlist)
            except ldap.LDAPError:
                self.logger.warning("Policy %s cannot be referenced to %r", self, obj)
        else:
            self.logger.info("Already attached!")


class UMCPolicy(Policy):
    class Meta:
        udm_module = "policies/umc"


class DHCPDNSPolicy(Policy):
    empty_attributes = EmptyAttributes(_("Empty attributes"))

    class Meta:
        udm_module = "policies/dhcp_dns"
