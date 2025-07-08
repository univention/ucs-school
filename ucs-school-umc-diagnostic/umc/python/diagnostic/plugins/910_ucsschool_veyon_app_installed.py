#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2020-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
This module checks if on a UCS@school singleserver system or a school server from
UCS@school version 4.4 v9 on, the UCS@school Veyon Proxy app is installed.
"""

from __future__ import absolute_import

import tempfile

from univention.appcenter.actions import get_action
from univention.appcenter.app_cache import Apps
from univention.appcenter.ucr import ucr_load as appcenter_ucr_load
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules.diagnostic import Warning

# from univention.uldap import getMachineConnection

APPCENTER_LOGFILE = "/var/log/univention/appcenter.log"
VEYON_APP_NAME = "UCS@school Veyon Proxy"
VEYON_APP_ID = "ucsschool-veyon-proxy"
_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school Veyon Proxy app")
description = _(
    "Verify that the {!r} app is installed on singleserver system and school server system "  # noqa: INT002
    "roles.".format(VEYON_APP_NAME)
)


def run(_umc_instance):
    server_role = ucr["server/role"]
    if server_role not in ("domaincontroller_master", "domaincontroller_slave"):
        # not a singleserver system or a school server
        return
    if server_role == "domaincontroller_master" and not ucr.is_true("ucsschool/singlemaster"):
        # not a singleserver
        return
    if server_role == "domaincontroller_slave":
        host_dn = ucr["ldap/hostdn"]
        # lo = getMachineConnection()
        lo = _umc_instance.get_user_ldap_connection()
        edu_dc_dns = lo.getAttr(
            "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr["ldap/base"]), "uniqueMember"
        )
        if host_dn.encode("UTF-8") not in edu_dc_dns:
            # not a school server
            return

    # check if UCS@school Veyon Proxy is installed
    appcenter_ucr_load()
    app = Apps().find(VEYON_APP_ID)
    if app is None:
        # app could not be found
        raise Warning(
            _("Cannot find the {!r} ({!r}) app in the Appcenter.").format(VEYON_APP_NAME, VEYON_APP_ID),
            buttons=[{"action": "update_appcenter_cache", "label": _("Update Appcenter cache")}],
        )
    if app.is_installed():
        return

    raise Warning(
        _(
            "The {0!r} app is not installed. Try installing it through the 'Install {0!r} app' button. "  # noqa: INT002
            "If that fails, install it manually using the Appcenter module: {{link_appcenter}}.".format(
                VEYON_APP_NAME
            )
        ),
        buttons=[
            {
                "action": "install_veyon_proxy_app",
                "label": _("Install {!r} app".format(VEYON_APP_NAME)),  # noqa: INT002
            }
        ],
    )


def install_veyon_proxy_app(_umc_instance):
    app = Apps().find(VEYON_APP_ID)
    MODULE.process(
        "Installing {!r} ({!r}). Output will be written to {!r}.".format(
            VEYON_APP_NAME, VEYON_APP_ID, APPCENTER_LOGFILE
        )
    )
    with tempfile.NamedTemporaryFile("w+") as pw_file:
        pw_file.write(_umc_instance.password)
        pw_file.flush()
        get_action("install").call(
            app=[app],
            noninteractive=True,
            username=_umc_instance.username,
            pwdfile=pw_file.name,
        )
    return run(_umc_instance)


def update_appcenter_cache(_umc_instance):
    MODULE.process(
        "Updating the appcenter cache. Output will be written to {!r}.".format(APPCENTER_LOGFILE)
    )
    get_action("update").call()
    return run(_umc_instance)


actions = {
    "install_veyon_proxy_app": install_veyon_proxy_app,
    "update_appcenter_cache": update_appcenter_cache,
}
links = [
    {
        "name": "link_appcenter",
        "href": "/univention/management/#module=appcenter:appcenter:0:id:ucsschool-veyon-proxy",
        "label": _("Appcenter page for {!r} app.".format(VEYON_APP_NAME)),  # noqa: INT002
    }
]


if __name__ == "__main__":
    from univention.management.console.modules.diagnostic import main

    main()
