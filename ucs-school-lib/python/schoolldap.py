#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2007-2020 Univention GmbH
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

import re

from ldap.dn import explode_dn
from univention.config_registry import ConfigRegistry
try:
	from typing import Any, Dict, List, Optional, Tuple
	from univention.admin.uldap import access as LoType
	from univention.admin.handlers import simpleLdap as UdmObject
except ImportError:
	pass


class SchoolSearchBase(object):
	"""Deprecated utility class that generates DNs of common school containers for a OU"""

	ucr = None  # type: ConfigRegistry

	def __init__(self, availableSchools, school=None, dn=None, ldapBase=None):
		if not self.ucr:
			self._load_ucr()

		self._ldapBase = ldapBase or self.ucr.get('ldap/base')

		from ucsschool.lib.models import School
		self._school = school or availableSchools[0]
		self._schoolDN = dn or School.cache(self.school).dn

		# prefixes
		self._containerAdmins = self.ucr.get('ucsschool/ldap/default/container/admins', 'admins')
		self._containerStudents = self.ucr.get('ucsschool/ldap/default/container/pupils', 'schueler')
		self._containerStaff = self.ucr.get('ucsschool/ldap/default/container/staff', 'mitarbeiter')
		self._containerTeachersAndStaff = self.ucr.get('ucsschool/ldap/default/container/teachers-and-staff', 'lehrer und mitarbeiter')
		self._containerTeachers = self.ucr.get('ucsschool/ldap/default/container/teachers', 'lehrer')
		self._containerClass = self.ucr.get('ucsschool/ldap/default/container/class', 'klassen')
		self._containerRooms = self.ucr.get('ucsschool/ldap/default/container/rooms', 'raeume')
		self._examUserContainerName = self.ucr.get('ucsschool/ldap/default/container/exam', 'examusers')
		self._examGroupNameTemplate = self.ucr.get('ucsschool/ldap/default/groupname/exam', 'OU%(ou)s-Klassenarbeit')

		self.group_prefix_students = self.ucr.get('ucsschool/ldap/default/groupprefix/pupils', 'schueler-')
		self.group_prefix_teachers = self.ucr.get('ucsschool/ldap/default/groupprefix/teachers', 'lehrer-')
		self.group_prefix_admins = self.ucr.get('ucsschool/ldap/default/groupprefix/admins', 'admins-')
		self.group_prefix_staff = self.ucr.get('ucsschool/ldap/default/groupprefix/staff', 'mitarbeiter-')

	@classmethod
	def _load_ucr(cls):  # type: () -> ConfigRegistry
		cls.ucr = ConfigRegistry()
		cls.ucr.load()
		return cls.ucr

	@classmethod
	def getOU(cls, dn):  # type: (str) -> str
		"""Return the school OU for a given DN.

			>>> SchoolSearchBase.getOU('uid=a,fou=bar,Ou=dc1,oU=dc,dc=foo,dc=bar')
			'dc1'
		"""
		school_dn = cls.getOUDN(dn)
		if school_dn:
			return explode_dn(school_dn, True)[0]

	@classmethod
	def getOUDN(cls, dn):  # type: (str) -> str
		"""Return the School OU-DN part for a given DN.

			>>> SchoolSearchBase.getOUDN('uid=a,fou=bar,Ou=dc1,oU=dc,dc=foo,dc=bar')
			'Ou=dc1,oU=dc,dc=foo,dc=bar'
			>>> SchoolSearchBase.getOUDN('ou=dc1,ou=dc,dc=foo,dc=bar')
			'ou=dc1,ou=dc,dc=foo,dc=bar'
		"""
		match = cls._RE_OUDN.search(dn)
		if match:
			return match.group(1)
	_RE_OUDN = re.compile('(?:^|,)(ou=.*)$', re.I)

	@property
	def dhcp(self):  # type: () -> str
		return "cn=dhcp,%s" % self.schoolDN

	@property
	def policies(self):  # type: () -> str
		return "cn=policies,%s" % self.schoolDN

	@property
	def networks(self):  # type: () -> str
		return "cn=networks,%s" % self.schoolDN

	@property
	def school(self):  # type: () -> str
		return self._school

	@property
	def schoolDN(self):  # type: () -> str
		return self._schoolDN

	@property
	def users(self):  # type: () -> str
		return "cn=users,%s" % self.schoolDN

	@property
	def groups(self):  # type: () -> str
		return "cn=groups,%s" % self.schoolDN

	@property
	def workgroups(self):  # type: () -> str
		return "cn=%s,cn=groups,%s" % (self._containerStudents, self.schoolDN)

	@property
	def classes(self):  # type: () -> str
		return "cn=%s,cn=%s,cn=groups,%s" % (self._containerClass, self._containerStudents, self.schoolDN)

	@property
	def rooms(self):  # type: () -> str
		return "cn=%s,cn=groups,%s" % (self._containerRooms, self.schoolDN)

	@property
	def students(self):  # type: () -> str
		return "cn=%s,cn=users,%s" % (self._containerStudents, self.schoolDN)

	@property
	def teachers(self):  # type: () -> str
		return "cn=%s,cn=users,%s" % (self._containerTeachers, self.schoolDN)

	@property
	def teachersAndStaff(self):  # type: () -> str
		return "cn=%s,cn=users,%s" % (self._containerTeachersAndStaff, self.schoolDN)

	@property
	def staff(self):  # type: () -> str
		return "cn=%s,cn=users,%s" % (self._containerStaff, self.schoolDN)

	@property
	def admins(self):  # type: () -> str
		return "cn=%s,cn=users,%s" % (self._containerAdmins, self.schoolDN)

	@property
	def classShares(self):  # type: () -> str
		return "cn=%s,cn=shares,%s" % (self._containerClass, self.schoolDN)

	@property
	def shares(self):  # type: () -> str
		return "cn=shares,%s" % self.schoolDN

	@property
	def printers(self):  # type: () -> str
		return "cn=printers,%s" % self.schoolDN

	@property
	def computers(self):  # type: () -> str
		return "cn=computers,%s" % self.schoolDN

	@property
	def examUsers(self):  # type: () -> str
		return "cn=%s,%s" % (self._examUserContainerName, self.schoolDN)

	@property
	def globalGroupContainer(self):  # type: () -> str
		return "cn=ouadmins,cn=groups,%s" % (self._ldapBase,)

	@property
	def educationalDCGroup(self):  # type: () -> str
		return "cn=OU%s-DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

	@property
	def educationalMemberGroup(self):  # type: () -> str
		return "cn=OU%s-Member-Edukativnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

	@property
	def administrativeDCGroup(self):  # type: () -> str
		return "cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

	@property
	def administrativeMemberGroup(self):  # type: () -> str
		return "cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

	@property
	def examGroupName(self):  # type: () -> str
		# replace '%(ou)s' strings in generic exam_group_name
		ucr_value_keywords = {'ou': self.school}
		return self._examGroupNameTemplate % ucr_value_keywords

	@property
	def examGroup(self):  # type: () -> str
		return "cn=%s,cn=ucsschool,cn=groups,%s" % (self.examGroupName, self._ldapBase)

	def isWorkgroup(self, groupDN):  # type: (str) -> bool
		# a workgroup cannot lie in a sub directory
		if not groupDN.endswith(self.workgroups):
			return False
		return len(explode_dn(groupDN)) - len(explode_dn(self.workgroups)) == 1

	def isGroup(self, groupDN):  # type: (str) -> bool
		return groupDN.endswith(self.groups)

	def isClass(self, groupDN):  # type: (str) -> bool
		return groupDN.endswith(self.classes)

	def isRoom(self, groupDN):  # type: (str) -> bool
		return groupDN.endswith(self.rooms)
