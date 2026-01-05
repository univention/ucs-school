#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#  Check App version
#
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import sys
from distutils.version import LooseVersion

from univention.appcenter.actions import get_action
from univention.appcenter.app_cache import Apps
from univention.appcenter.ucr import ucr_get, ucr_is_true

if len(sys.argv) < 2 or sys.argv[-1] == "-v":
    print("Usage: {} [-v] <app name>".format(sys.argv[0]))
    sys.exit(2)
app_name = sys.argv[-1]

hostname_master = ucr_get("ldap/master").split(".")[0]
app = Apps().find(app_name)
if app is None:
    print('Unknown app "{}".'.format(app_name))
    sys.exit(2)
domain = get_action("domain")
info = domain.to_dict([app])[0]

if not app.is_installed():
    print('App "{}" is not installed on this host.'.format(app_name))
    sys.exit(2)

try:
    master_version = info["installations"][hostname_master]["version"]
    if master_version is None:
        raise KeyError()
except KeyError:
    print('App "{}" is not installed on Primary Directory Node.'.format(app_name))
    sys.exit(2)

ret = LooseVersion(app.version) > LooseVersion(master_version)

if "-v" in sys.argv:
    print('Version of app "{}" on this host: "{}"'.format(app_name, app.version))
    print('Version of app "{}" on Primary Directory Node: "{}"'.format(app_name, master_version))
    if ret:
        print(
            'Error: local version of app "{}" higher than version on Primary Directoy Node!'.format(
                app_name
            )
        )
    else:
        print(
            'OK: local version of app "{}" lower than or equal to version on Primary Directory '
            "Node.".format(app_name)
        )

ucrv = "ucsschool/join/ignore-version-mismatch/{}/{}".format(master_version, app.version)
if ucr_is_true(ucrv):
    if "-v" in sys.argv:
        print('Ignoring version mismatch, because "{}" is set.'.format(ucrv))
    sys.exit(0)

sys.exit(int(ret))
