#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2016-2024 Univention GmbH
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

"""Class to create lots of test users."""
from __future__ import absolute_import

import gzip
import json
import logging
import random
import string

from ucsschool.lib.models.utils import ucr

from ..models.import_user import ImportUser

TEST_DATA_FILE = "/usr/share/doc/ucs-school-import/test_data.json.gz"


class TestUserCreator(object):
    def __init__(
        self,
        ous,
        staff=0,
        students=0,
        teachers=0,
        staffteachers=0,
        classes=0,
        inclasses=2,
        schools=2,
        email=False,
    ):
        self.ous = sorted(ous)
        self.num_staff = staff
        self.num_students = students
        self.num_teachers = teachers
        self.num_staffteachers = staffteachers
        self.num_classes = classes
        self.num_inclasses = inclasses
        self.num_schools = schools
        self.email = email
        self.staff = []
        self.students = []
        self.teachers = []
        self.staffteachers = []
        self.class_names = []
        self.class_name_generators = {}
        self.logger = logging.getLogger(__name__)
        self.test_data = self.get_test_data(TEST_DATA_FILE)
        self.mail_domain = self._get_maildomain()

    @staticmethod
    def get_test_data(filename):
        with gzip.open(filename, "rb") as fp:
            return json.load(fp)

    def make_classes(self):
        grade = 0
        while len(self.class_names) * len(self.ous) < self.num_classes:
            grade += 1
            for letter in string.ascii_lowercase:
                self.class_names.append("{}{}".format(grade, letter))
                if len(self.class_names) * len(self.ous) >= self.num_classes:
                    self.logger.info(
                        "Created %d class names for %d schools.", len(self.class_names), len(self.ous)
                    )
                    return self.class_names

    def _get_new_given_name(self):
        give_modifier = ""
        given_len = len(self.test_data["given"])
        given_cursor = random.randint(0, given_len - 1)  # nosec
        while True:
            yield u"{}{}".format(self.test_data["given"][given_cursor], give_modifier)
            given_cursor += 1
            if given_cursor == given_len:
                # used all names, append number
                try:
                    give_modifier = str(int(give_modifier) + 1)
                except ValueError:
                    give_modifier = "2"
            given_cursor %= given_len

    def _get_new_family_name(self):
        family_modifier = ""
        family_len = len(self.test_data["family"])
        family_cursor = random.randint(0, family_len - 1)  # nosec
        while True:
            yield u"{}{}".format(self.test_data["family"][family_cursor], family_modifier)
            family_cursor += 1
            if family_cursor == family_len:
                # used all names, append number
                try:
                    family_modifier = str(int(family_modifier) + 1)
                except ValueError:
                    family_modifier = "2"
            family_cursor %= family_len

    def _class_name_gen(self, school):
        cursor = 0
        class_names_len = len(self.class_names)
        while True:
            yield self.class_names[cursor % class_names_len]
            cursor += 1

    def _get_class_name(self, school):
        try:
            gen = self.class_name_generators[school]
        except KeyError:
            gen = self.class_name_generators[school] = self._class_name_gen(school)
        return next(gen)

    @staticmethod
    def _get_maildomain():
        try:
            return ucr["mail/hosteddomains"].split()[0]
        except (AttributeError, IndexError):
            return ucr["domainname"]

    def make_users(self):
        jobs = (
            (self.num_staff, "staff"),
            (self.num_students, "student"),
            (self.num_teachers, "teacher"),
            (self.num_staffteachers, "staffteacher"),
        )
        total_users_num = sum(job[0] for job in jobs)
        total_users_count = 0
        given_name_gen = self._get_new_given_name()
        family_name_gen = self._get_new_family_name()

        for num, kind in jobs:
            if num == 0:
                continue
            for _user_num in range(num):
                given_name = next(given_name_gen)
                family_name = next(family_name_gen)
                user = {
                    "Schulen": None,
                    "Benutzertyp": kind,
                    "Vorname": given_name,
                    "Nachname": family_name,
                    "Klassen": None,
                    "Beschreibung": "A {}.".format(kind),
                    "Telefon": "+{:>02}-{:>03}-{}".format(  # nosec
                        random.randint(1, 99), random.randint(1, 999), random.randint(1000, 999999)
                    ),
                }
                if self.email:
                    user["EMail"] = ImportUser.normalize(
                        "{}m.{}m@{}".format(given_name, family_name, self.mail_domain)
                    ).lower()
                if kind != "student" and random.choice((True, False)):  # nosec
                    # 50% chance for non-students to be in multiple schools
                    user["Schulen"] = sorted(random.sample(self.ous, self.num_schools))
                else:
                    user["Schulen"] = [random.choice(self.ous)]  # nosec

                if kind == "staff":
                    user["Klassen"] = {}
                elif kind == "student":
                    # students are in 1 class
                    user["Klassen"] = {
                        school: [self._get_class_name(school)] for school in user["Schulen"]
                    }
                else:
                    # [staff]teachers can be in multiple classes
                    user["Klassen"] = {
                        school: [self._get_class_name(school) for _x in range(self.num_inclasses)]
                        for school in user["Schulen"]
                    }
                total_users_count += 1
                self.logger.debug("(%d/%d) Created: %r", total_users_count, total_users_num, user)
                yield user
            self.logger.info("Created %d %ss.", num, kind)
        self.logger.info("Created a total of %d users.", total_users_count)
