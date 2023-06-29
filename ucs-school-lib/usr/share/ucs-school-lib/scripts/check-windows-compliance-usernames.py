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

from ucsschool.lib.models.attributes import is_valid_win_directory_name
from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import User
from univention.admin.uldap import getAdminConnection

parser = ArgumentParser(
    description=f"{__file__} checks all present UCS@School user names for compliance with the "
    f"Windows naming conventions. The script is silent by default and only writes the "
    f"number of invalid user names to stdout upon completion."
)
parser.add_argument(
    "-v", "--verbose", action="store_true", required=False, help="Prints invalid usernames."
)
args = parser.parse_args()


def get_number_of_invalid_usernames() -> int:
    """Get the number of invalid usernames which do not comply with Windows naming conventions"""
    lo, _ = getAdminConnection()
    all_schools = School.get_all(lo)
    number_of_invalid_usernames = 0
    for school in all_schools:
        all_users = User.get_all(lo, school.name)
        for user in all_users:
            if not is_valid_win_directory_name(user.name):
                if args.verbose:
                    print(f"Username {user.name} is not a valid Windows directory name.")
                number_of_invalid_usernames += 1

    return number_of_invalid_usernames


sys.stdout.write(f"{get_number_of_invalid_usernames()}")
sys.stdout.flush()
