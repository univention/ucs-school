#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2012-2024 Univention GmbH
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

import datetime
import re
import shutil

from six import string_types
from six.moves.configparser import ConfigParser

from univention.lib import locking
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE

LESSONS_FILE = "/var/lib/ucs-school-lib/lessons.ini"
LESSONS_BACKUP = "/var/lib/ucs-school-lib/lessons.bak"

_ = Translation("python-ucs-school").translate


class Lesson(object):

    TIME_REGEX = re.compile(r"^([01][0-9]|2[0-3]|[0-9]):([0-5][0-9])")

    def __init__(self, name, begin, end):
        self._name = self._check_name(name)
        self._begin = self._parse_time(begin)
        self._end = self._parse_time(end)
        if self._end <= self._begin:
            raise AttributeError(_("Overlapping lessons are not allowed"))

    def _check_name(self, string):
        if not isinstance(string, string_types):
            raise TypeError("string expected")
        for char in (
            "\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14"
            "\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f[]\x7f"
        ):
            string = string.replace(char, "")
        return string

    def _parse_time(self, string):
        if not isinstance(string, string_types):
            raise TypeError("string expected")
        m = Lesson.TIME_REGEX.match(string)
        if not m:
            raise AttributeError("invalid time format: %s" % string)
        return datetime.time(*map(int, m.groups()))

    @property
    def name(self):
        return self._name

    @property
    def begin(self):
        return self._begin

    @property
    def end(self):
        return self._end

    def __cmp__(self, other):
        if other.end < self.begin:
            return 1
        if other.begin > self.end:
            return -1
        return 0

    def __gt__(self, other):
        return self.begin > other.end

    def __ge__(self, other):
        return self.begin >= other.end

    def __lt__(self, other):
        return self.end < other.begin

    def __le__(self, other):
        return self.end <= other.begin

    def __eq__(self, other):
        return self.begin == other.begin and self.end == other.end

    def __ne__(self, other):
        return not self == other

    def intersect(self, lesson):
        return not (self.begin > lesson.end or self.end < lesson.begin)

    def __str__(self):
        return "%s: %s - %s" % (self._name, self._begin, self._end)


class SchoolLessons(ConfigParser):
    def __init__(self, filename=LESSONS_FILE):
        ConfigParser.__init__(self)
        self._lessons = []
        self.read(filename)
        self.init()

    def init(self):
        for sec in self.sections():
            try:
                lesson = Lesson(sec, self.get(sec, "begin"), self.get(sec, "end"))
                self.add(lesson)
            except (AttributeError, TypeError) as exc:
                MODULE.warn("Lesson %s could not be added: %s" % (sec, str(exc)))

    def remove(self, lesson):
        if isinstance(lesson, Lesson):
            lesson = lesson.name

        self._lessons[:] = [les for les in self._lessons if les.name != lesson]

    def add(self, lesson, begin=None, end=None):
        if isinstance(lesson, string_types):
            lesson = Lesson(lesson, begin, end)

        # ensure there is no intersection between the lessons
        for item in self._lessons:
            if lesson.intersect(item) or lesson.name == item.name:
                raise AttributeError(_("Overlapping lessons are not allowed"))

        self._lessons.append(lesson)

    def save(self):
        # remove all sections
        for sec in self.sections():
            self.remove_section(sec)

        for lesson in self.lessons:
            self.add_section(lesson.name)
            self.set(lesson.name, "begin", str(lesson.begin))
            self.set(lesson.name, "end", str(lesson.end))

        lock = locking.get_lock("ucs-school-lib-schoollessons")
        with open(LESSONS_FILE, "w") as fd:
            shutil.copyfile(LESSONS_FILE, LESSONS_BACKUP)
            self.write(fd)
        locking.release_lock(lock)

    @property
    def lessons(self):
        self._lessons.sort()
        return list(self._lessons)

    @property
    def current(self):
        now = datetime.datetime.now().time()

        # currently active lesson
        for lesson in self.lessons:
            if now >= lesson.begin and now <= lesson.end:
                return lesson

        return None

    @property
    def next(self):
        now = datetime.datetime.now().time()

        # currently active lesson
        for lesson in self.lessons:
            if now < lesson.begin:
                return lesson

        return None

    @property
    def previous(self):
        now = datetime.datetime.now().time()

        self._lessons.sort(reverse=True)
        # currently active lesson
        for lesson in self._lessons:
            if now > lesson.end:
                return lesson

        return None
