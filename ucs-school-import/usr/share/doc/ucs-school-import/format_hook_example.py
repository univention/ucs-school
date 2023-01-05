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

from ucsschool.importer.utils.format_pyhook import FormatPyHook

SPLIT_FIRSTNAME_SPACE = 0
SPLIT_FIRSTNAME_DASH = 0
SPLIT_LASTNAME_SPACE = -1
SPLIT_LASTNAME_DASH = 0


class FormatUsernamePyHook(FormatPyHook):
    priority = {
        "patch_fields_staff": 10,
        "patch_fields_student": 10,
        "patch_fields_teacher": 10,
        "patch_fields_teacher_and_staff": 10,
    }
    properties = ("username", "email")

    @staticmethod
    def patch_fields(fields):
        fields["firstname"] = (
            fields["firstname"].split()[SPLIT_FIRSTNAME_SPACE].split("-")[SPLIT_FIRSTNAME_DASH]
        )
        fields["lastname"] = (
            fields["lastname"].split()[SPLIT_LASTNAME_SPACE].split("-")[SPLIT_LASTNAME_DASH]
        )

    def patch_fields_staff(self, property_name, fields):
        if property_name == "username":
            self.patch_fields(fields)
        return fields

    def patch_fields_student(self, property_name, fields):
        if property_name == "email":
            self.patch_fields(fields)
        return fields

    def patch_fields_teacher(self, property_name, fields):
        if property_name == "username":
            self.patch_fields(fields)
        return fields

    def patch_fields_teacher_and_staff(self, property_name, fields):
        if property_name == "email":
            self.patch_fields(fields)
        return fields
