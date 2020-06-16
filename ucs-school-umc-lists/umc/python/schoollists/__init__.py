#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Get csv class lists
#
# Copyright 2018-2020 Univention GmbH
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

import csv
import StringIO
from ldap.dn import explode_dn

from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.sanitizers import (
    DNSanitizer,
    StringSanitizer,
)
from univention.management.console.modules.decorators import sanitize

from ucsschool.lib.school_umc_base import SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from ucsschool.lib.models.user import User

_ = Translation("ucs-school-umc-lists").translate


def write_classlist_csv(fieldnames, students, filename, separator):
    csvfile = StringIO.StringIO()
    writer = csv.writer(csvfile, delimiter=str(separator))
    writer.writerow(fieldnames)
    for row in students:
        writer.writerow(row)
    csvfile.seek(0)
    result = {"filename": filename, "csv": csvfile.read()}
    csvfile.close()
    return result


class Instance(SchoolBaseModule):
    @sanitize(
        school=SchoolSanitizer(required=True),
        group=DNSanitizer(required=True, minimum=1),
        separator=StringSanitizer(required=True),
    )
    @LDAP_Connection()
    def csv_list(self, request, ldap_user_read=None, ldap_position=None):
        school = request.options["school"]
        group = request.options["group"]
        separator = request.options["separator"]

        default = "firstname Firstname,lastname Lastname,Class Class,username Username"
        ucr_value = ucr.get("ucsschool/umc/lists/class/attributes", "") or default
        attributes, fieldnames = zip(*[field.split() for field in ucr_value.split(",")])
        rows = []
        for student in self.students(ldap_user_read, school, group):
            row = []
            student_udm_obj = student.get_udm_object(ldap_user_read)
            for attr in attributes:
                if attr == "Class":
                    row.append(student.school_classes[school][0].split("-", 1)[1])
                else:
                    try:
                        value = student_udm_obj[attr]
                    except KeyError:
                        raise UMC_Error(
                            _(
                                "{!r} is not a valid UDM-property. Please change the value of UCR "
                                "ucsschool/umc/lists/class/attributes."
                            ).format(attr)
                        )
                    if type(value) is list:
                        value = " ".join(value)
                    row.append(value)
            rows.append(row)

        filename = explode_dn(group)[0].split("=")[1] + ".csv"
        result = write_classlist_csv(fieldnames, rows, filename, separator)
        self.finished(request.id, result)

    def students(self, lo, school, group):
        for user in self._users(lo, school, group=group, user_type="student"):
            yield User.from_udm_obj(user, school, lo)
