#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2018-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

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
