#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Get csv class lists
#
# SPDX-FileCopyrightText: 2018-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import csv
import os
import uuid
from datetime import datetime
from io import StringIO

from ldap.dn import explode_rdn
from six.moves.urllib_parse import quote

from ucsschool.lib.models.user import User
from ucsschool.lib.school_umc_base import SchoolBaseModule
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import allow_get_request, sanitize
from univention.management.console.modules.sanitizers import (
    StringSanitizer,
)

_ = Translation("ucs-school-umc-lists").translate


def write_classlist_csv(fieldnames, students, separator):
    with StringIO() as csvfile:
        writer = csv.writer(csvfile, delimiter=str(separator))
        writer.writerow(fieldnames)
        for row in students:
            writer.writerow(row)
        return csvfile.getvalue()


class Instance(SchoolBaseModule):
    @allow_get_request
    @sanitize(classlist=StringSanitizer(required=True))
    def csv_get(self, request):
        classlist = request.options["classlist"]
        path = "/usr/share/ucs-school-umc-lists/classlists/"
        filename = os.path.join(path, os.path.basename(classlist))
        # Bug #57018 - retrieve charset from filename
        charset = "utf-16" if "UTF-16" in filename else "utf-8"
        try:
            with open(filename, "rb") as fd:
                self.finished(request.id, fd.read(), mimetype=('text/csv; charset="%s"' % charset))
        except EnvironmentError:
            raise UMC_Error(
                _("The class list does not exists. Please create a new one."),
                status=404,
            )

    @LDAP_Connection()
    def csv_list(self, request, ldap_user_read=None, ldap_position=None):
        school = request.options["school"]
        group = request.options["group"]
        separator = request.options["separator"]
        exclude_deactivated = request.options["exclude_deactivated"]
        default = "firstname Firstname,lastname Lastname,Class Class,username Username"
        ucr_value = ucr.get("ucsschool/umc/lists/class/attributes", "") or default
        attributes, fieldnames = zip(*[field.split() for field in ucr_value.split(",")])
        rows = []
        for student in self.students(ldap_user_read, school, group):
            if exclude_deactivated and not student.is_active():
                continue
            row = []
            student_udm_obj = student.get_udm_object(ldap_user_read)
            if school not in student.school_classes:
                MODULE.error(
                    "Student missing class in school {!r}: {!r}".format(school, student_udm_obj.dn)
                )
                continue
            for attr in attributes:
                if attr == "Class":
                    row.append(student.school_classes[school][0].split("-", 1)[1])
                else:
                    try:
                        value = student_udm_obj[attr]
                    except KeyError:
                        raise UMC_Error(
                            _(
                                "{!r} is not a valid UDM-property. Please change the value of the UCR "
                                "variable ucsschool/umc/lists/class/attributes."
                            ).format(attr)
                        )
                    if isinstance(value, list):
                        value = " ".join(value)
                    row.append(value)
            rows.append(row)

        classlistname = explode_rdn(group, True)[0]
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        # Bug #57018 - workaround to pass used encoding in filename
        enc = "UTF-16" if separator == "\t" else "UTF-8"
        filename = "%s_%s_%s-%s.csv" % (classlistname.replace("/", "_"), enc, timestamp, uuid.uuid4())
        path = os.path.join("/usr/share/ucs-school-umc-lists/classlists/", filename)
        with open(path, "w", encoding=enc) as fd:
            os.chmod(path, 0o600)
            fd.write(write_classlist_csv(fieldnames, rows, separator))

        url = "/univention/command/schoollists/csvlistget?classlist=%s" % (quote(filename),)
        self.finished(
            request.id,
            {
                "url": url,
                "filename": "{}_{}.csv".format(classlistname.replace("/", "_"), timestamp),
            },
        )

    def students(self, lo, school, group):
        for user in self._users(lo, school, group=group, user_type="student"):
            yield User.from_udm_obj(user, school, lo)
