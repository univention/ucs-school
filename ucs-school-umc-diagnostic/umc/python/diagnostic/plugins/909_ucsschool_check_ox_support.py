#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
#
# UCS@school Diagnosis Module
#
# Copyright 2020-2021 Univention GmbH
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
This module checks if a UCS@school DC-Master with OX installed also has
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
    if "ok installed" not in out:
        raise Warning(
            "The OX App Suite is installed but the required package 'ucs-school-ox-support' is missing.",
            buttons=[{"action": "install_missing", "label": _("Install missing components")}],
        )


def exec_cmd(*args):
    cmd = []
    for arg in args:
        cmd.append(arg)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.communicate()


def install_missing_components(_umc_instance):
    stdout, stderr = exec_cmd("apt-get", "install", "ucs-school-ox-support")
    if stderr:  # on fail, try again with univention-install
        stdout, stderr = exec_cmd("univention-install", "ucs-school-ox-support")
        error_text = "E: Unable to locate package"
        if error_text in stdout or stderr:
            raise Warning("Could not install package 'ucs-school-ox-support'.\n{}".format(stderr))
    return run(_umc_instance)


actions = {
    "install_missing": install_missing_components,
}


if __name__ == "__main__":
    run(None)
