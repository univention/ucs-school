# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2018-2021 Univention GmbH
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
Class to create an OU.
Used by create_ou script and customer single user HTTP API.
"""

import logging

from ldap.filter import filter_format

from ucsschool.lib.models.school import School
from ucsschool.lib.models.utils import ucr
from udm_rest_client import UDM

MAX_HOSTNAME_LENGTH = 13


async def create_ou(
    ou_name: str,
    display_name: str,
    edu_name: str,
    admin_name: str,
    share_name: str,
    lo: UDM,
    baseDN: str,
    hostname: str,
    is_single_master: bool,
    alter_dhcpd_base: bool,
):
    """
    Create a ucsschool OU.

    :param str ou_name: name for the OU
    :param str display_name: display name for the OU
    :param str edu_name: host name of educational school server
    :param str admin_name: host name of administrative school server
    :param str share_name: host name
    :param univention.uldap.access lo: LDAP connection object
    :param str baseDN: base DN
    :param str hostname: hostname of master in case of singlemaster
    :param bool is_single_master: whether it is a singlemaster
    :param bool alter_dhcpd_base: if the DHCP base should be modified
    :return bool: whether the OU was successfully created (or already existed)
    :raises ValueError: on validation errors
    :raises uidAlreadyUsed:
    """
    is_edu_name_generated = False
    if not edu_name:
        is_edu_name_generated = True
        if is_single_master:
            edu_name = hostname
        else:
            edu_name = "dc{}".format(ou_name)

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
    objects = [
        obj.dn
        async for obj in lo.get("computers/computer").search(
            filter_s=filter_format("(&(objectClass=univentionHost)(cn=%s))", (share_name,)), base=baseDN
        )
    ]
    if not objects:
        if share_name == "dc{}".format(ou_name) or (edu_name and share_name == edu_name):
            share_dn = filter_format(
                "cn=%s,cn=dc,cn=server,cn=computers,%s", (share_name, new_school.dn)
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

    await new_school.validate(lo)
    if len(new_school.warnings) > 0:
        logger.warning("The following fields reported warnings during validation:")
        for key, value in new_school.warnings.items():
            logger.warning("%s: %s", key, value)
    if len(new_school.errors) > 0:
        error_str = "The following fields reported errors during validation:\n"
        for key, value in new_school.errors.items():
            error_str += "{}: {}\n".format(key, value)
        raise ValueError(error_str)

    res = await new_school.create(lo)
    if res:
        logger.info("OU %r created successfully.", new_school.name)
    else:
        logger.error("Error creating OU %r.", new_school.name)
    return res
