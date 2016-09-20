#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Class to create lots of test users.
"""
# Copyright 2016 Univention GmbH
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

import gzip
import json
import random
import string

from ucsschool.importer.utils.logging import get_logger

TEST_DATA_FILE = "/usr/share/doc/ucs-school-import/test_data.json.gz"
logger = get_logger()


class TestUserCreator(object):
	def __init__(self, ous, staff=0, students=0, teachers=0, staffteachers=0, classes=0, inclasses=2, schools=2):
		self.ous = sorted(ous)
		self.num_staff = staff
		self.num_students = students
		self.num_teachers = teachers
		self.num_staffteachers = staffteachers
		self.num_classes = classes
		self.num_inclasses = inclasses
		self.num_schools = schools
		self.staff = list()
		self.students = list()
		self.teachers = list()
		self.staffteachers = list()
		self.class_names = list()
		self.class_name_generators = dict()
		self.test_data = self.get_test_data(TEST_DATA_FILE)

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
					logger.info("Created %d class names for %d schools.", len(self.class_names), len(self.ous))
					return self.class_names

	def _get_new_given_name(self):
		give_modifier = ""
		given_len = len(self.test_data["given"])
		given_cursor = random.randint(0, given_len)
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
		family_cursor = random.randint(0, family_len)
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

	def make_users(self):
		given_name = self._get_new_given_name()
		family_name = self._get_new_family_name()
		jobs = ((self.num_staff, "staff"), (self.num_students, "student"), (self.num_teachers, "teacher"),
			(self.num_staffteachers, "staffteacher"))
		total_users_num = sum([job[0] for job in jobs])
		total_users_count = 0

		for num, kind in jobs:
			if num == 0:
				continue
			for user_num in xrange(num):
				user = dict(
					Schulen=None,
					Benutzertyp=kind,
					Vorname=next(given_name),
					Nachname=next(family_name),
					Klassen=None,
					Beschreibung="A {}.".format(kind),
					Telefon="+{:>02}-{:>03}-{}".format(random.randint(1, 99), random.randint(1, 999),
						random.randint(1000, 999999))
				)
				if kind != "student" and random.choice((True, False)):
					# 50% chance for non-students to be in multiple schools
					user["Schulen"] = sorted(random.sample(self.ous, self.num_schools))
				else:
					user["Schulen"] = [random.choice(self.ous)]

				if kind == "staff":
					user["Klassen"] = {}
				elif kind == "student":
					# students are in 1 class
					user["Klassen"] = dict([(school, self._get_class_name(school)) for school in user["Schulen"]])
				else:
					# [staff]teachers can be in multiple classes
					user["Klassen"] = dict([(school, [self._get_class_name(school) for _x in range(self.num_inclasses)])
						for school in user["Schulen"]])
				total_users_count += 1
				logger.debug("(%d/%d) Created: %r", total_users_count, total_users_num, user)
				yield user
			logger.info("Created %d %ss.", num, kind)
		logger.info("Created a total of %d users.", total_users_count)
