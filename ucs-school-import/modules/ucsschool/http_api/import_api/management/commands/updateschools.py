#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2018-2024 Univention GmbH
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
Django manage.py command to update one/some/all School object(s).

python3 -m ucsschool.http_api.manage updateschools --all
"""

from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError

from ucsschool.http_api.import_api.models import School


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-a",
            "--all",
            help="Update all school OU objects and delete not existing ones [default off].",
            action="store_true",
        )
        parser.add_argument("--ou", nargs="+", help="OU to update.")

    def handle(self, *args, **options):
        if not options["all"] and not options["ou"]:
            raise CommandError("Either --all or --ou must be used.")
        if options["all"]:
            School.update_from_ldap()
        else:
            for ou in options["ou"]:
                try:
                    School.update_from_ldap(ou)
                except RuntimeError as exc:
                    raise CommandError(str(exc))
        self.stderr.write(
            "Known schools in UCS@school import API now: {}.".format(
                ", ".join(School.objects.all().values_list("name", flat=True))
            )
        )
