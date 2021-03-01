#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Add or remove an item to/from a UCRV list
#
# Copyright (C) 2017-2021 Univention GmbH
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

import univention.config_registry


def add_or_remove_ucrv(ucrv, action, value, delimiter):
    """Adds or removes an uncrv. Delimiter splits the value of the existing ucr."""
    ucr = univention.config_registry.ConfigRegistry()
    ucr.load()

    if action == "remove" and ucrv not in ucr.keys():
        return 0
    cur_val = ucr.get(ucrv, "")
    cur_val_list = [v for v in cur_val.split(delimiter) if v]
    if action == "add":
        if value not in cur_val_list:
            cur_val_list.append(value)
    elif action == "remove":
        try:
            cur_val_list.remove(value)
        except ValueError:
            return 0
    univention.config_registry.handler_set(["{}={}".format(ucrv, delimiter.join(cur_val_list))])
    return 0
