#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright 2021-2024 Univention GmbH
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
CLI for OU cloning:

$ python3 -m univention.testing.ucsschool DEMOSCHOOL testou1234
"""

import sys

import click

from ucsschool.lib.models.utils import ucr
from univention.admin.uldap import getAdminConnection
from univention.testing.ucsschool.ucs_test_school import OUCloner


@click.command()
@click.argument("source_ou", type=click.STRING)
@click.argument("target_ou", type=click.STRING)
def cli(source_ou, target_ou):
    lo, _ = getAdminConnection()
    oc = OUCloner(lo)
    oc.clone_ou(source_ou, target_ou)


if __name__ == "__main__":
    if ucr["server/role"] not in ("domaincontroller_master", "domaincontroller_backup"):
        click.echo("This script must be executed on a Primary Directory Node or Backup Directory Node.")
        sys.exit(1)
    cli()
