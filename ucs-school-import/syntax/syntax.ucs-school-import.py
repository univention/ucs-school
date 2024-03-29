#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2024 Univention GmbH
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

import re

import univention.admin.localization
from univention.admin.syntax import UDM_Objects, select

translation = univention.admin.localization.translation("univention-admin-syntax-ucsschool_import")
# The underscore function is already in use at this point -> use a different name
_local = translation.translate


class UCSSchool_Server_DN(UDM_Objects):
    udm_modules = (
        "computers/domaincontroller_master",
        "computers/domaincontroller_backup",
        "computers/domaincontroller_slave",
        "computers/memberserver",
    )
    label = "%(fqdn)s"
    empty_value = False
    simple = True


class ucsschoolSchools(UDM_Objects):
    udm_modules = ("container/ou",)
    udm_filter = "objectClass=ucsschoolOrganizationalUnit"
    regex = re.compile(r"^.+$")
    key = "%(name)s"
    label = "%(displayName)s"
    use_objects = False


class ucsschoolTypes(select):
    choices = [
        ("student", _local("Student")),
        ("teacher", _local("Teacher")),
        ("staff", _local("Staff")),
        ("teacher_and_staff", _local("Teacher and Staff")),
    ]
