#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2021-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

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
