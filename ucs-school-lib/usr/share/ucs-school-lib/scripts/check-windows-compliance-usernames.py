#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2023 Univention GmbH
#
# https://www.univention.de/
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
See Bug #56152 / https://forge.univention.org/bugzilla/show_bug.cgi?id=56152
and GitLab Issue https://git.knut.univention.de/univention/ucsschool/-/issues/1050
"""
import sys
from argparse import ArgumentParser
from typing import Dict, List, Tuple

from ucsschool.lib.models.attributes import is_valid_win_directory_name
from ucsschool.lib.models.school import School
from univention.admin.uldap import getAdminConnection
from univention.udm import UDM


def get_number_of_invalid_usernames(silent=False, show_dn=False) -> int:
    """Get the number of invalid usernames which do not comply with Windows naming conventions"""
    lo, _ = getAdminConnection()
    UDM.admin().version(2).get("users/user")
    all_schools = School.get_all(lo)
    number_of_invalid_usernames = 0
    for school in all_schools:

        # Use ldap directly to fetch usernames for a school
        # for large systems, this might take multiple minutes otherwise
        all_users: List[Tuple[str, Dict]] = lo.search(
            filter="(&(objectClass=ucsschoolType)(objectClass=organizationalPerson))",
            attr=["uid"],
            base=f"cn=users,{school.dn}",
        )

        for user_data in all_users:
            dn, attrs = user_data
            username = attrs["uid"][0].decode("utf-8")
            if not is_valid_win_directory_name(username):
                if not silent:
                    if show_dn:
                        print(f"{dn}")
                    else:
                        print(
                            f"Username {username} in school {school.name}"
                            f" is not a valid Windows directory name."
                        )
                number_of_invalid_usernames += 1

    return number_of_invalid_usernames


def main():

    parser = ArgumentParser(
        description=f"{__file__} checks all present UCS@School user names for compliance with the "
        f"Windows naming conventions. Without any options,"
        f" it lists invalid usernames together with the associated school."
    )
    parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        required=False,
        default=False,
        help="Only writes the number of invalid usernames to"
        " the standard output upon script completion.",
    )
    parser.add_argument(
        "--dn",
        action="store_true",
        required=False,
        default=False,
        help="Alternative output: List distinguished names of all users with invalid usernames.",
    )
    args = parser.parse_args()

    number_of_invalid_usernames = get_number_of_invalid_usernames(silent=args.silent, show_dn=args.dn)
    if args.silent:
        sys.stdout.write(f"{number_of_invalid_usernames}")
        sys.stdout.flush()
    else:
        print(f"Total number of invalid usernames: {number_of_invalid_usernames}")


if __name__ == "__main__":
    main()
