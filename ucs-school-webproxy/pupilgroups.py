# -*- coding: utf-8 -*-
#
# Univention Directory Listener Module Pupilgroups
#  listener module: pupilgroups
#
# SPDX-FileCopyrightText: 2008-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import absolute_import

import ldap
import listener

import univention.admin.uldap
import univention.config_registry
import univention.debug as ud
from ucsschool.lib.models.school import School
from univention.config_registry.frontend import ucr_update

name = "pupilgroups"
description = "Map pupil group lists to UCR"
filter = "(objectClass=univentionGroup)"
attributes = ["memberUid"]

all_local_schools = None
keyPattern = "proxy/filter/usergroup/%s"


def initialize():
    pass


def prerun():
    update_local_school_list()


def update_local_school_list():
    global all_local_schools
    listener.setuid(0)
    ud.debug(ud.LISTENER, ud.INFO, "pupilgroups: update_local_school_list()")
    try:
        lo, po = univention.admin.uldap.getMachineConnection(ldap_master=False)
        all_local_schools = [school.dn for school in School.get_all(lo)]
    except ldap.LDAPError:
        all_local_schools = None
        return
    finally:
        ud.debug(ud.LISTENER, ud.PROCESS, "pupilgroups: all_local_schools=%r" % (all_local_schools,))
        listener.unsetuid()


def is_special_ucsschool_group(dn):
    # (DC|Member)-Edukativnetz
    # OU${OU}-(DC|Member)-Edukativnetz
    return dn.endswith(
        "-Edukativnetz,cn=ucsschool,cn=groups,%s" % (listener.configRegistry.get("ldap/base"),)
    )


def handler(dn, new, old):
    if is_special_ucsschool_group(dn):
        update_local_school_list()

    ud.debug(ud.LISTENER, ud.PROCESS, "pupilgroups: dn: %s" % dn)
    configRegistry = univention.config_registry.ConfigRegistry()
    configRegistry.load()

    if all_local_schools is None:
        ud.debug(
            ud.LISTENER,
            ud.ERROR,
            "pupilgroups: Could not detect local schools",
        )
    elif not any(dn.lower().endswith(",cn=groups,%s" % school.lower()) for school in all_local_schools):
        ud.debug(
            ud.LISTENER,
            ud.INFO,
            "pupilgroups: dn: %s does not belong to local schools %r" % (dn, all_local_schools),
        )
        return  # the object doesn't belong to this school

    changes = {}
    if new and new.get("memberUid"):
        changes[keyPattern % new["cn"][0].decode("UTF-8")] = b",".join(new.get("memberUid", [])).decode(
            "UTF-8"
        )
    elif old:  # old lost its last memberUid OR old was removed
        changes[keyPattern % old["cn"][0].decode("UTF-8")] = None
    ud.debug(ud.LISTENER, ud.INFO, "pupilgroups: %r" % (changes,))

    listener.setuid(0)
    try:
        ucr_update(configRegistry, changes)
    finally:
        listener.unsetuid()
