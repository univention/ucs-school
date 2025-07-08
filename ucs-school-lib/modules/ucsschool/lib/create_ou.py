#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2018-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Class to create an OU.
Used by create_ou script and customer single user HTTP API.
"""

import logging
from typing import TYPE_CHECKING, Optional  # noqa: F401

from ldap.dn import escape_dn_chars
from ldap.filter import filter_format

from ucsschool.lib.models.school import School
from ucsschool.lib.models.utils import ucr

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType  # noqa: F401


MAX_HOSTNAME_LENGTH = 15


def create_ou(
    ou_name,  # type: str
    display_name,  # type: str
    edu_name,  # type: str
    admin_name,  # type: str
    share_name,  # type: str
    lo,  # type: LoType
    baseDN,  # type: str
    hostname,  # type: str
    is_single_master,  # type: bool
    alter_dhcpd_base=None,  # type: Optional[bool]
):
    """
    Create a ucsschool OU.

    :param str ou_name: name for the OU, see models.attributes::SchoolName for allowed values, may
        contain dashes and underscores, but the latter only if DC name(s) are passed explicitly (without
        underscore), max length is 11 chars if DC names are not passed explicitly.
    :param str display_name: display name for the OU
    :param str edu_name: host name of educational school server, see models.attributes::DCName for
        allowed values, may contain dashes but no underscores, max 13 chars
    :param str admin_name: host name of administrative school server, see models.attributes::DCName for
        allowed values, may contain dashes but no underscores, max 13 chars
    :param str share_name: host name
    :param univention.uldap.access lo: LDAP connection object
    :param str baseDN: base DN
    :param str hostname: hostname of Primary Directory Node in case of singleserver
    :param bool is_single_master: whether it is a singleserver
    :param bool alter_dhcpd_base: if the DHCP base should be modified
    :return bool: whether the OU was sucessfully created (or already existed)
    :raises ValueError: on validation errors
    :raises uidAlreadyUsed:
    """
    if edu_name:
        is_edu_name_generated = False
    else:
        is_edu_name_generated = True
        edu_name = hostname if is_single_master else "dc{}".format(ou_name)

    if admin_name and len(admin_name) > MAX_HOSTNAME_LENGTH:
        raise ValueError(
            "The specified hostname for the administrative DC is too long (>{} characters).".format(
                MAX_HOSTNAME_LENGTH
            )
        )

    if len(edu_name) > MAX_HOSTNAME_LENGTH:
        if is_edu_name_generated:
            raise ValueError(
                "Automatically generated hostname for the educational DC is too long (>{} characters). "
                "Please pass the desired hostname(s) as parameters.".format(MAX_HOSTNAME_LENGTH)
            )
        else:
            raise ValueError(
                "The specified hostname for the educational DC is too long (>{} characters). ".format(
                    MAX_HOSTNAME_LENGTH
                )
            )

    if display_name is None:
        display_name = ou_name

    logger = logging.getLogger(__name__)

    new_school = School(
        name=ou_name,
        dc_name=edu_name,
        dc_name_administrative=admin_name,
        display_name=display_name,
        alter_dhcpd_base=alter_dhcpd_base,
    )

    # TODO: Reevaluate this validation after CNAME changes are implemented
    share_dn = ""
    if share_name is None:
        share_name = edu_name
    objects = lo.searchDn(
        filter=filter_format("(&(objectClass=univentionHost)(cn=%s))", (share_name,)), base=baseDN
    )
    if not objects:
        if share_name == "dc{}".format(ou_name) or (edu_name and share_name == edu_name):
            share_dn = "cn=%s,cn=dc,cn=server,cn=computers,%s" % (
                escape_dn_chars(share_name),
                new_school.dn,
            )
        else:
            logger.warning(
                "WARNING: share file server name %r not found! Using %r as share file server.",
                share_name,
                ucr.get("hostname"),
            )
            share_dn = ucr.get("ldap/hostdn")
    else:
        share_dn = objects[0]

    new_school.class_share_file_server = share_dn
    new_school.home_share_file_server = share_dn

    new_school.validate(lo)
    if len(new_school.warnings) > 0:
        logger.warning("The following fields reported warnings during validation:")
        for key, value in new_school.warnings.items():
            logger.warning("%s: %s", key, value)
    if len(new_school.errors) > 0:
        error_str = "The following fields reported errors during validation:\n"
        for key, value in new_school.errors.items():
            error_str += "{}: {}\n".format(key, value)
        raise ValueError(error_str)

    res = new_school.create(lo)
    if res:
        logger.info("OU %r created successfully.", new_school.name)
    else:
        logger.error("Error creating OU %r.", new_school.name)
    return res
