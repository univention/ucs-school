#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2018-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Django manage.py command to check if a specified superuser account already exists.

python3 -m ucsschool.http_api.manage superuserexists
"""

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("username", help="Username to check if is superuser.")

    def handle(self, *args, **options):
        UserModel = get_user_model()
        username = options["username"]
        if not UserModel._default_manager.filter(username=username, is_superuser=True).exists():
            raise CommandError("User {!r} does not exist or is not a superuser.".format(username))
