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
import csv
import enum
import pathlib
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ucsschool.lib.models.attributes import is_valid_win_directory_name
from ucsschool.lib.models.school import School
from univention.admin.uldap import getAdminConnection


class InvalidUsernameReasons(enum.Enum):
    WIN_DIRECTORY = "Is not a valid Windows directory name."


@dataclass(frozen=True)
class InvalidUser:
    username: str
    school_name: str
    dn: str
    reason: InvalidUsernameReasons


def print_reason_details():
    reason_details = {
        InvalidUsernameReasons.WIN_NAMING_CONVENTIONS.value: "Certain usernames like like CON, PRN, AUX,"
        " ... lead to problems in Windows systems. In a Windows environment file and directory names "
        "are not allowed to start with those words. But Windows automatically creates files for each "
        "user that contain their username. One consequence can be,"
        " that users with an invalid username can't sign in to a Windows system. "
        "The use of usernames which aren't compliant with Windows naming conventions"
        " is deprecated, and support will be removed with UCS 5.2."
        "See the manual"
        " https://docs.software-univention.de/ucsschool-manual/5.0/de/management/users.html "
        "(Chapter 3) and the relevant Microsoft documentation about naming conventions"
        " https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file for more information."
    }

    for reason, details in reason_details.items():
        print(f'\n# Reason: "{reason}"\n')
        print(f"{details}")


def get_all_invalid_users() -> List[InvalidUser]:
    """Retrieve all invalid users"""
    lo, _ = getAdminConnection()
    all_schools = School.get_all(lo)

    all_invalid_users: List[InvalidUser] = []

    for school in all_schools:

        # Use ldap directly to fetch usernames for a school
        # for large systems, this might take multiple minutes otherwise
        all_users: List[Tuple[str, Dict]] = lo.search(
            filter="(&(objectClass=ucsschoolType)(objectClass=organizationalPerson))",
            attr=["uid"],
            base=f"cn=users,{school.dn}",
        )

        for dn, attrs in all_users:
            username = attrs["uid"][0].decode("utf-8")

            if not is_valid_win_directory_name(username):
                all_invalid_users.append(
                    InvalidUser(
                        username=username,
                        school_name=school.name,
                        dn=dn,
                        reason=InvalidUsernameReasons.WIN_DIRECTORY,
                    )
                )

        return all_invalid_users


def report_invalid_users(all_invalid_users: List[InvalidUser], silent=False) -> None:

    number_of_invalid_usernames = len(all_invalid_users)
    if silent:
        sys.stdout.write(f"{number_of_invalid_usernames}")
        sys.stdout.flush()
    else:
        if len(all_invalid_users) > 0:
            print('"Username" "School Name" "Distinguished Name" "Reason"')
        for invalid_user in all_invalid_users:
            print(
                f"{invalid_user.username} {invalid_user.school_name}"
                f' {invalid_user.dn} "{invalid_user.reason.value}"'
            )

        print(f"\nTotal number of invalid usernames: {number_of_invalid_usernames}")
        print(
            "To list more details for the 'Reason' column "
            "use the option '-l' or '--list-reason-details'"
        )


def write_output_file(all_invalid_users: List[InvalidUser], output_path: pathlib.Path) -> None:
    """Write a csv file with username, school name, dn and the reason why the username is invalid."""
    with open(output_path, "w") as output_file:
        csv_writer = csv.writer(output_file)
        csv_writer.writerow(["Username", "School Name", "Distinguished Name", "Reason"])
        for invalid_user in all_invalid_users:
            csv_writer.writerow(
                [
                    invalid_user.username,
                    invalid_user.school_name,
                    invalid_user.dn,
                    invalid_user.reason.value,
                ]
            )


def setup_parser() -> ArgumentParser:

    parser = ArgumentParser(
        description=f"{__file__} checks all present UCS@School user names for compliance with the "
        f"Windows naming conventions. Without any options,"
        f" it lists invalid usernames together with the associated school."
    )
    parser.add_argument(
        "-l",
        "--list-reason-details",
        action="store_true",
        required=False,
        default=False,
        help="Lists the reasons for invalid usernames and explains them in more detail.",
    )
    parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        required=False,
        default=False,
        help="Only writes the number of invalid usernames to"
        " the standard output upon script completion, otherwise silent if no errors occur.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        required=False,
        default=None,
        help="Path to an output file. The output will be a CSV file with username, school name,"
        " dn and the reason why the username is invalid.",
    )
    return parser


def main() -> None:

    parser = setup_parser()
    args = parser.parse_args()

    if args.list_reason_details:
        print_reason_details()
        sys.exit(0)

    if not args.silent:
        print(f"Running {__file__} ...")

    output_path: Optional[pathlib.Path] = args.output
    if args.output is not None:
        output_path = output_path.resolve()
        if output_path.exists():
            print(f"Path {output_path} already exists, aborting...")
            sys.exit(1)

    if not args.silent:
        print("Checking all UCS@school users for invalid usernames...")
    all_invalid_users = get_all_invalid_users()

    report_invalid_users(all_invalid_users, silent=args.silent)

    if output_path is not None:
        write_output_file(all_invalid_users, output_path)


if __name__ == "__main__":
    main()
