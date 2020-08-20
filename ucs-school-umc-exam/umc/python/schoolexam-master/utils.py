#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  Starts a new exam for a specified computer room
#
# Copyright 2013-2020 Univention GmbH
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
import inspect
import re
from typing import Any, Callable, Dict, List, Set, Tuple, Union

from univention.config_registry.backend import ConfigRegistry


def get_blacklist_set(ucr_var, ucr):  # type: (str, ConfigRegistry) -> Set[str]
    """
    >>> set([ x.replace('||','|') for x in re.split('(?<![|])[|](?![|])', '|My|new|Value|with|Pipe||symbol') if x ])
    set(['with', 'new', 'My', 'Value', 'Pipe|symbol'])
    """
    return set([x.replace("||", "|") for x in re.split("(?<![|])[|](?![|])", ucr.get(ucr_var, "")) if x])


def replace_user_values(
    old_values, overrides, key_blacklist, ucr, return_old_values=False
):  # type: (List[Tuple[str, Any]], Dict[str, Union[str, Callable]], Set[str], ConfigRegistry, bool) -> List[Any]
    """
    Takes a list of key value pairs and returns a list of new key value pairs.
    Overrides for specific keys can be specified.

    :param old_values: Tuple of key value pairs to replace
    :param overrides: Dictionary containing overrides for specific keys. If the provided override is a Callable
                    it will be invoked with the key and old value as parameters.
    :param key_blacklist: A set of key values that shall be removed from the result.
    :param ucr: ConfigRegistry instance to fetch value blacklists from
    :param return_old_values: If True the old values are included into the result as well,
                            which will then be (key, old_value, new_value).
    :return: A Tuple containing new key, value pairs. Can be modified to contain the old values as well!
    """
    result = list()
    for key, old_value in old_values:
        if key in key_blacklist:
            continue
        new_value = [
            elem
            for elem in old_value
            if elem not in get_blacklist_set("ucsschool/exam/user/ldap/blacklist/%s" % key, ucr)
        ]
        if not new_value:
            continue
        if key in overrides.keys():
            override = overrides.get(key)
            new_value = override(key, old_value) if inspect.isfunction(override) else override
        if return_old_values:
            result.append((key, old_value, new_value))
        else:
            result.append((key, new_value))
    return result
