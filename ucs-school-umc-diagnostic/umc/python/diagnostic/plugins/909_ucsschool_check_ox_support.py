#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# SPDX-FileCopyrightText: 2020-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
This module checks if a UCS@school Primary Directory Node with OX installed also has
the package ucs-school-ox-support installed. If not a button pops up,
which tries to fix this issue by installing it.
"""

from __future__ import absolute_import

import subprocess

from univention.appcenter.actions import get_action
from univention.appcenter.app_cache import Apps
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules.diagnostic import Warning

_ = Translation("ucs-school-umc-diagnostic").translate

title = _("UCS@school OX Support")
description = "\n".join(
    _(
        "If the OX App Suite is installed somewhere on the domain "
        "check that the package ucs-school-ox-support is also installed"
    ),
)


def run(_umc_instance):
    if ucr.get("server/role") != "domaincontroller_master":
        return

    # check if OX is installed
    ox_app = Apps().find("oxseforucs")
    if ox_app is None:
        return  # app could not be found

    domain = get_action("domain")
    info = domain.to_dict([ox_app])
    if info[0] is None:
        return
    is_ox_installed = info[0]["is_installed_anywhere"]
    if not is_ox_installed:
        return  # app is not installed anywhere

    # check if ucs-school-ox-support package is installed
    out, err = exec_cmd("/usr/bin/dpkg-query", "-W", "-f", "${Status}", "ucs-school-ox-support")
    if "ok installed" not in out.decode("UTF-8", "replace"):
        raise Warning(
            "The OX App Suite is installed but the required package 'ucs-school-ox-support' is missing.",
            buttons=[{"action": "install_missing", "label": _("Install missing components")}],
        )


def exec_cmd(*args):
    cmd = []
    for arg in args:
        cmd.append(arg)  # noqa: PERF402
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # nosec
    return p.communicate()


def install_missing_components(_umc_instance):
    stdout, stderr = exec_cmd("apt-get", "install", "ucs-school-ox-support")
    if stderr:  # on fail, try again with univention-install
        stdout, stderr = exec_cmd("univention-install", "ucs-school-ox-support")
        stdout, stderr = stdout.decode("UTF-8", "replace"), stderr.decode("UTF-8", "replace")
        error_text = "E: Unable to locate package"
        if error_text in stdout or stderr:
            raise Warning("Could not install package 'ucs-school-ox-support'.\n{}".format(stderr))
    return run(_umc_instance)


actions = {
    "install_missing": install_missing_components,
}


if __name__ == "__main__":
    run(None)
