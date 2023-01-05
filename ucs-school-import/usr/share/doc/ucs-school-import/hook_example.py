#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2023 Univention GmbH
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

from ucsschool.importer.utils.user_pyhook import UserPyHook


class MyHook(UserPyHook):
    supports_dry_run = True  # when False (default) whole class will be skipped during dry-run

    priority = {
        "pre_create": 1,  # functions with value None will be skipped
        "post_create": 1,
        "pre_modify": 1,
        "post_modify": 1,
        "pre_move": 1,
        "post_move": 1,
        "pre_remove": 1,
        "post_remove": 1,
    }

    def pre_create(self, user):
        if self.dry_run:
            self.logger.info("Dry-run, skipping pre_create job for %s.", user)
        else:
            self.logger.debug("Running a pre_create hook for %s.", user)

    def post_create(self, user):
        if self.dry_run:
            self.logger.info("Dry-run, skipping post_create job for %s.", user)
        else:
            self.logger.debug("Running a post_create hook for %s.", user)

    def pre_modify(self, user):
        if self.dry_run:
            self.logger.info("Dry-run, skipping pre_modify job for %s.", user)
        else:
            self.logger.debug("Running a pre_modify hook for %s.", user)

    def post_modify(self, user):
        if self.dry_run:
            self.logger.info("Dry-run, skipping post_modify job for %s.", user)
        else:
            self.logger.debug("Running a post_modify hook for %s.", user)

    def pre_move(self, user):
        if self.dry_run:
            self.logger.info("Dry-run, skipping pre_move job for %s.", user)
        else:
            self.logger.debug("Running a pre_move hook for %s.", user)

    def post_move(self, user):
        if self.dry_run:
            self.logger.info("Dry-run, skipping post_move job for %s.", user)
        else:
            self.logger.debug("Running a post_move hook for %s.", user)

    def pre_remove(self, user):
        if self.dry_run:
            self.logger.info("Dry-run, skipping pre_remove job for %s.", user)
        else:
            self.logger.debug("Running a pre_remove hook for %s.", user)

    def post_remove(self, user):
        if self.dry_run:
            self.logger.info("Dry-run, skipping post_remove job for %s.", user)
        else:
            self.logger.debug("Running a post_remove hook for %s.", user)
