#!/usr/bin/python3
# -*- coding: utf-8 -*-
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

"""Role specific shares"""
from __future__ import print_function

import os
import sys
from typing import List, Optional  # noqa: F401

import univention.admin.modules as udm_modules
import univention.admin.uexceptions
import univention.admin.uldap as udm_uldap
from ucsschool.lib.i18n import ucs_school_name_i18n
from ucsschool.lib.models.group import Group
from ucsschool.lib.models.school import School
from ucsschool.lib.roles import role_pupil, role_staff, role_teacher
from ucsschool.lib.school_umc_ldap_connection import MACHINE_READ, USER_READ, USER_WRITE, LDAP_Connection
from univention.config_registry import ConfigRegistry
from univention.lib.misc import custom_groupname

udm_modules.update()


def roleshare_name(role, school_ou, ucr):  # type: (str, str, ConfigRegistry) -> str
    custom_roleshare_name = ucr.get("ucsschool/import/roleshare/%s" % (role,))
    if custom_roleshare_name:
        return custom_roleshare_name
    else:
        return "-".join((ucs_school_name_i18n(role), school_ou))


def roleshare_path(role, school_ou, ucr):  # type: (str, str, ConfigRegistry) -> str
    custom_roleshare_path = ucr.get("ucsschool/import/roleshare/%s/path" % (role,))
    if custom_roleshare_path:
        return custom_roleshare_path
    else:
        return os.path.join(school_ou, ucs_school_name_i18n(role))


def roleshare_home_subdir(
    school_ou, roles, ucr=None
):  # type: (str, List[str], Optional[ConfigRegistry]) -> str
    if not ucr:
        ucr = ConfigRegistry()
        ucr.load()

    if ucr.is_true("ucsschool/import/roleshare", True):
        for role in (role_pupil, role_teacher, role_staff):
            if role in roles:
                return roleshare_path(role, school_ou, ucr)
    return ""


@LDAP_Connection(USER_READ, USER_WRITE)
def create_roleshare_on_server(
    role,
    school_ou,
    share_container_dn,
    serverfqdn,
    teacher_group=None,
    ucr=None,
    ldap_user_read=None,
    ldap_user_write=None,
    ldap_position=None,
):
    if not ucr:
        ucr = ConfigRegistry()
        ucr.load()

    if not teacher_group:
        teacher_groupname = "-".join((ucs_school_name_i18n(role_teacher), school_ou))
        teacher_group = Group(name=teacher_groupname, school=school_ou).get_udm_object(ldap_user_read)
        if not teacher_group:
            raise univention.admin.uexceptions.noObject("Group not found: %s." % teacher_groupname)
    else:
        teacher_groupname = teacher_group["name"]

    custom_groupname_domainadmins = custom_groupname("Domain Admins")
    try:
        udm_module_name = "shares/share"
        udm_modules.init(ldap_user_write, ldap_position, udm_modules.get(udm_module_name))
        share_container = udm_uldap.position(share_container_dn)
        udm_obj = udm_modules.get(udm_module_name).object(None, ldap_user_write, share_container)
        udm_obj.open()
        udm_obj.options = ["samba"]
        udm_obj["name"] = roleshare_name(role, school_ou, ucr)
        udm_obj["path"] = os.path.join("/home", roleshare_path(role, school_ou, ucr))
        udm_obj["host"] = serverfqdn
        udm_obj["group"] = teacher_group["gidNumber"]
        udm_obj["sambaBrowseable"] = "0"
        udm_obj["sambaWriteable"] = "0"
        udm_obj["sambaValidUsers"] = '@"%s" @"%s"' % (teacher_groupname, custom_groupname_domainadmins)
        udm_obj["sambaCustomSettings"] = [
            ("admin users", '@"%s" @"%s"' % (teacher_groupname, custom_groupname_domainadmins))
        ]
        udm_obj.create()
    except univention.admin.uexceptions.objectExists as exc:
        print("Object exists: %s" % (exc.args[0],))
    else:
        print("Object created: %s" % udm_obj.dn)


@LDAP_Connection(MACHINE_READ)
def fqdn_from_serverdn(server_dn, ldap_machine_read=None, ldap_position=None):
    fqdn = None
    try:
        dn, ldap_obj = ldap_machine_read.search(
            base=server_dn, scope="base", attr=["cn", "associatedDomain"]
        )[0]
        if "associatedDomain" in ldap_obj:
            fqdn = ".".join(
                (ldap_obj["cn"][0].decode("UTF-8"), ldap_obj["associatedDomain"][0].decode("UTF-8"))
            )
    except IndexError:
        print("Could not determine FQDN for %s" % (server_dn,))
    return fqdn


@LDAP_Connection(MACHINE_READ)
def fileservers_for_school(school_id, ldap_machine_read=None, ldap_position=None):
    school_obj = School(name=school_id).get_udm_object(ldap_machine_read)

    server_dn_list = []
    server_dn = school_obj.get("ucsschoolHomeShareFileServer")
    if server_dn:
        server_dn_list.append(server_dn)

    server_list = []
    for server_dn in server_dn_list:
        try:
            fqdn = fqdn_from_serverdn(server_dn)
        except univention.admin.uexceptions.noObject:
            print('Ignoring non-existant ucsschoolHomeShareFileServer "%s"' % (server_dn,))
            continue
        if fqdn:
            server_list.append(fqdn)
    return set(server_list)


@LDAP_Connection()
def create_roleshare_for_searchbase(role, school, ucr=None, ldap_user_read=None):
    if not ucr:
        ucr = ConfigRegistry()
        ucr.load()

    school_ou = school.name
    share_container_dn = school.get_search_base(school.name).shares

    teacher_groupname = "-".join((ucs_school_name_i18n(role_teacher), school_ou))
    teacher_group = Group(name=teacher_groupname, school=school_ou).get_udm_object(ldap_user_read)
    if not teacher_group:
        raise univention.admin.uexceptions.noObject("Group not found: %s." % teacher_groupname)

    for serverfqdn in fileservers_for_school(school_ou):
        create_roleshare_on_server(role, school_ou, share_container_dn, serverfqdn, teacher_group, ucr)


@LDAP_Connection(MACHINE_READ)
def create_roleshares(role_list, school_list=None, ucr=None, ldap_machine_read=None):
    if not ucr:
        ucr = ConfigRegistry()
        ucr.load()

    supported_roles = (role_pupil, role_teacher, role_staff)
    supported_role_aliases = {"student": "pupil"}

    roles = []
    for name in role_list:
        if name in supported_role_aliases:
            name = supported_role_aliases[name]
        if name not in supported_roles:
            print("Given role is not supported. Only supported roles are %s" % (supported_roles,))
            sys.exit(1)
        roles.append(name)

    schools = School.get_all(ldap_machine_read)

    if not school_list:
        school_list = []

    all_visible_schools = [x.name for x in schools]
    for school_ou in school_list:
        if school_ou not in all_visible_schools:
            print("School not found: %s" % (school_ou,))

    for school in schools:
        if school_list and school.name not in school_list:
            continue
        for role in roles:
            create_roleshare_for_searchbase(role, school, ucr)
