#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school lib
#  module: UCS@school simple query interface
#
# SPDX-FileCopyrightText: 2018-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from collections import namedtuple
from typing import TYPE_CHECKING

from ldap.filter import filter_format

from univention.config_registry import ConfigRegistry

if TYPE_CHECKING:
    import univention.uldap  # noqa: F401

ucr = ConfigRegistry()
ucr.load()

MembershipFlags = namedtuple("MembershipFlags", ["is_edu_school_member", "is_admin_school_member"])


def get_school_membership_type(lo, dn):  # type: (univention.uldap.access, str) -> MembershipFlags
    """
    Returns a named tuple, that states if the given computer object specified by `dn` is an educational
    school Replica Directory Node/Managed Node or administrative Replica Directory Node/Managed Node.

    :param univention.uldap.access lo: the LDAP connection
    :param str dn: DN of the computer object
    :return: a named tuple that contains flags for educational and administrative membership
    :rtype: namedtuple(is_edu_school_member, is_admin_school_member)
    """
    filter_s = filter_format("(&(objectClass=univentionGroup)(uniqueMember=%s))", (dn,))
    grp_dn_list = lo.searchDn(filter=filter_s)
    is_edu_school_member = False
    is_admin_school_member = False
    for grp_dn in grp_dn_list:
        # is grp_dn in list of global school groups?
        if grp_dn in (
            "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
            "cn=Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
        ):
            is_edu_school_member = True
        if grp_dn in (
            "cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
            "cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
        ):
            is_admin_school_member = True
        # is dn in list of OU specific school groups?
        if not grp_dn.startswith("cn=OU"):
            continue
        for suffix in (
            "-DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
            "-Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
        ):
            if grp_dn.lower().endswith(suffix.lower()):
                is_edu_school_member = True
        for suffix in (
            "-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
            "-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
        ):
            if grp_dn.lower().endswith(suffix.lower()):
                is_admin_school_member = True
    return MembershipFlags(is_edu_school_member, is_admin_school_member)


def is_central_computer(lo, dn):  # type: (univention.uldap.access, str) -> bool
    """
    Checks if the given computer object specified by `dn` is a central system or located at a specific
    school.

    :param univention.uldap.access lo: the LDAP connection
    :param str dn: DN of the computer object
    :return: is the computer a central system?
    :rtype: bool
    """
    attrs = lo.get(dn, ["univentionObjectType"])
    object_type = attrs.get("univentionObjectType")[0]
    if object_type in (b"computers/domaincontroller_master", b"computers/domaincontroller_backup"):
        return True
    if object_type in (b"computers/domaincontroller_slave", b"computers/memberserver"):
        membership = get_school_membership_type(lo, dn)
        return not (membership.is_edu_school_member or membership.is_admin_school_member)
    return True


def is_school_slave(lo, dn):  # type: (univention.uldap.access, str) -> bool
    """
    Checks if the given domaincontroller_slave object (specified by `dn`) is a school Replica Node.

    :param univention.uldap.access lo: the LDAP connection
    :param str dn: DN of the computer object
    :return: is the computer a school Replica Directory Node?
    :rtype: bool
    :raises ValueError: computer DN does not refer to a computers/domaincontroller_slave object
    """
    attrs = lo.get(dn, ["univentionObjectType"])
    object_type = attrs.get("univentionObjectType")[0]
    if object_type != b"computers/domaincontroller_slave":
        raise ValueError(
            "Given computer DN does not refer to a computers/domaincontroller_slave object!"
        )

    membership = get_school_membership_type(lo, dn)
    return membership.is_edu_school_member or membership.is_admin_school_member
