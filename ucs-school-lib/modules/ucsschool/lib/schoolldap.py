# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2007-2021 Univention GmbH
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

try:
    from typing import Dict, Pattern, Sequence
except ImportError:
    pass

from ldap.dn import explode_dn

from univention.config_registry import ConfigRegistry


class SchoolSearchBase(object):
    """Deprecated: don't use position to identify user objects"""

    ucr: ConfigRegistry = None
    _regex_cache: Dict[str, Pattern] = {}

    # prefixes
    _containerAdmins = ""
    _containerStudents = ""
    _containerStaff = ""
    _containerTeachersAndStaff = ""
    _containerTeachers = ""
    _containerClass = ""
    _containerRooms = ""
    _examUserContainerName = ""
    _examGroupNameTemplate = ""
    group_prefix_students = ""
    group_prefix_teachers = ""
    group_prefix_admins = ""
    group_prefix_staff = ""

    def __init__(
        self,
        availableSchools: Sequence[str],
        school: str = None,
        dn: str = None,
        ldapBase: str = None,
    ) -> None:
        if not self.ucr:
            self._load_ucr()

        self._ldapBase = ldapBase or self.ucr.get("ldap/base")

        from ucsschool.lib.models.school import School

        self._school = school or availableSchools[0]
        self._schoolDN = dn or School.cache(self.school).dn
        if not self._containerAdmins:
            self._load_containers_and_prefixes()

    @classmethod
    def _load_containers_and_prefixes(cls) -> None:
        if not cls.ucr:
            cls._load_ucr()
        cls._containerAdmins = cls.ucr.get("ucsschool/ldap/default/container/admins") or "admins"
        cls._containerStudents = cls.ucr.get("ucsschool/ldap/default/container/pupils") or "schueler"
        cls._containerStaff = cls.ucr.get("ucsschool/ldap/default/container/staff") or "mitarbeiter"
        cls._containerTeachersAndStaff = (
            cls.ucr.get("ucsschool/ldap/default/container/teachers-and-staff")
            or "lehrer und mitarbeiter"
        )
        cls._containerTeachers = cls.ucr.get("ucsschool/ldap/default/container/teachers") or "lehrer"
        cls._containerClass = cls.ucr.get("ucsschool/ldap/default/container/class") or "klassen"
        cls._containerRooms = cls.ucr.get("ucsschool/ldap/default/container/rooms") or "raeume"
        cls._examUserContainerName = cls.ucr.get("ucsschool/ldap/default/container/exam") or "examusers"
        cls._examGroupNameTemplate = (
            cls.ucr.get("ucsschool/ldap/default/groupname/exam") or "OU%(ou)s-Klassenarbeit"
        )
        cls.group_prefix_students = (
            cls.ucr.get("ucsschool/ldap/default/groupprefix/pupils") or "schueler-"
        )
        cls.group_prefix_teachers = (
            cls.ucr.get("ucsschool/ldap/default/groupprefix/teachers") or "lehrer-"
        )
        cls.group_prefix_admins = cls.ucr.get("ucsschool/ldap/default/groupprefix/admins") or "admins-"
        cls.group_prefix_staff = (
            cls.ucr.get("ucsschool/ldap/default/groupprefix/staff") or "mitarbeiter-"
        )

    @classmethod
    def _load_ucr(cls) -> ConfigRegistry:
        cls.ucr = ConfigRegistry()
        cls.ucr.load()
        return cls.ucr

    @classmethod
    def getOU(cls, dn: str) -> str:
        """Return the school OU for a given DN.

        >>> SchoolSearchBase.getOU('uid=a,fou=bar,Ou=dc1,oU=dc,dc=foo,dc=bar')
        'dc1'
        """
        school_dn = cls.getOUDN(dn)
        if school_dn:
            return explode_dn(school_dn, True)[0]

    @classmethod
    def getOUDN(cls, dn: str) -> str:
        """Return the School OU-DN part for a given DN.

        >>> SchoolSearchBase.getOUDN('uid=a,fou=bar,Ou=dc1,oU=dc,dc=foo,dc=bar')
        'Ou=dc1,oU=dc,dc=foo,dc=bar'
        >>> SchoolSearchBase.getOUDN('ou=dc1,ou=dc,dc=foo,dc=bar')
        'ou=dc1,ou=dc,dc=foo,dc=bar'
        """
        match = cls._RE_OUDN.search(dn)
        if match:
            return match.group(1)

    _RE_OUDN = re.compile("(?:^|,)(ou=.*)$", re.I)

    @property
    def dhcp(self) -> str:
        return "cn=dhcp,%s" % self.schoolDN

    @property
    def policies(self) -> str:
        return "cn=policies,%s" % self.schoolDN

    @property
    def networks(self) -> str:
        return "cn=networks,%s" % self.schoolDN

    @property
    def school(self) -> str:
        return self._school

    @property
    def schoolDN(self) -> str:
        return self._schoolDN

    @property
    def users(self) -> str:
        return "cn=users,%s" % self.schoolDN

    @property
    def groups(self) -> str:
        return "cn=groups,%s" % self.schoolDN

    @property
    def students_group(self) -> str:
        return "cn=%s%s,cn=groups,%s" % (self.group_prefix_students, self.school.lower(), self.schoolDN)

    @property
    def teachers_group(self) -> str:
        return "cn=%s%s,cn=groups,%s" % (self.group_prefix_teachers, self.school.lower(), self.schoolDN)

    @property
    def staff_group(self) -> str:
        return "cn=%s%s,cn=groups,%s" % (self.group_prefix_staff, self.school.lower(), self.schoolDN)

    @property
    def admins_group(self):  # type: () -> str
        return "cn=%s%s,cn=ouadmins,cn=groups,%s" % (
            self.group_prefix_admins,
            self.school.lower(),
            self._ldapBase,
        )

    @property
    def workgroups(self) -> str:
        return "cn=%s,cn=groups,%s" % (self._containerStudents, self.schoolDN)

    @property
    def classes(self) -> str:
        return "cn=%s,cn=%s,cn=groups,%s" % (
            self._containerClass,
            self._containerStudents,
            self.schoolDN,
        )

    @property
    def rooms(self) -> str:
        return "cn=%s,cn=groups,%s" % (self._containerRooms, self.schoolDN)

    @property
    def students(self) -> str:
        return "cn=%s,cn=users,%s" % (self._containerStudents, self.schoolDN)

    @property
    def teachers(self) -> str:
        return "cn=%s,cn=users,%s" % (self._containerTeachers, self.schoolDN)

    @property
    def teachersAndStaff(self) -> str:
        return "cn=%s,cn=users,%s" % (self._containerTeachersAndStaff, self.schoolDN)

    @property
    def staff(self) -> str:
        return "cn=%s,cn=users,%s" % (self._containerStaff, self.schoolDN)

    @property
    def admins(self) -> str:
        return "cn=%s,cn=users,%s" % (self._containerAdmins, self.schoolDN)

    @property
    def classShares(self) -> str:
        return "cn=%s,cn=shares,%s" % (self._containerClass, self.schoolDN)

    @property
    def shares(self) -> str:
        return "cn=shares,%s" % self.schoolDN

    @property
    def printers(self) -> str:
        return "cn=printers,%s" % self.schoolDN

    @property
    def computers(self) -> str:
        return "cn=computers,%s" % self.schoolDN

    @property
    def examUsers(self) -> str:
        return "cn=%s,%s" % (self._examUserContainerName, self.schoolDN)

    @property
    def globalGroupContainer(self) -> str:
        return "cn=ouadmins,cn=groups,%s" % (self._ldapBase,)

    @property
    def educationalDCGroup(self) -> str:
        return "cn=OU%s-DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

    @property
    def educationalMemberGroup(self) -> str:
        return "cn=OU%s-Member-Edukativnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

    @property
    def administrativeDCGroup(self) -> str:
        return "cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

    @property
    def administrativeMemberGroup(self) -> str:
        return "cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (self.school, self._ldapBase)

    @property
    def examGroupName(self) -> str:
        # replace '%(ou)s' strings in generic exam_group_name
        ucr_value_keywords = {"ou": self.school}
        return self._examGroupNameTemplate % ucr_value_keywords

    @property
    def examGroup(self) -> str:
        return "cn=%s,cn=ucsschool,cn=groups,%s" % (self.examGroupName, self._ldapBase)

    def isWorkgroup(self, groupDN: str) -> bool:
        # a workgroup cannot lie in a sub directory
        if not groupDN.endswith(self.workgroups):
            return False
        return len(explode_dn(groupDN)) - len(explode_dn(self.workgroups)) == 1

    def isGroup(self, groupDN: str) -> bool:
        return groupDN.endswith(self.groups)

    def isClass(self, groupDN: str) -> bool:
        return groupDN.endswith(self.classes)

    def isRoom(self, groupDN: str) -> bool:
        return groupDN.endswith(self.rooms)

    @classmethod
    def get_is_teachers_group_regex(cls) -> Pattern:
        if "is_teachers_group" not in cls._regex_cache:
            if not cls._containerTeachers:
                cls._load_containers_and_prefixes()
            cls._regex_cache["is_teachers_group"] = re.compile(
                r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(
                    cls._containerTeachers, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["is_teachers_group"]

    @classmethod
    def get_is_staff_group_regex(cls) -> Pattern:
        if "is_staff_group" not in cls._regex_cache:
            if not cls._containerStaff:
                cls._load_containers_and_prefixes()
            cls._regex_cache["is_staff_group"] = re.compile(
                r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(
                    cls._containerStaff, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["is_staff_group"]

    @classmethod
    def get_is_student_group_regex(cls) -> Pattern:
        if "is_student_group" not in cls._regex_cache:
            if not cls._containerStudents:
                cls._load_containers_and_prefixes()
            cls._regex_cache["is_student_group"] = re.compile(
                r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(
                    cls._containerStudents, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["is_student_group"]

    @classmethod
    def get_staff_group_regex(cls) -> Pattern:
        if "staff" not in cls._regex_cache:
            if not cls._containerStaff:
                cls._load_containers_and_prefixes()

    @classmethod
    def get_is_admins_group_regex(cls) -> Pattern:
        if "is_admins_group" not in cls._regex_cache:
            if not cls._containerAdmins:
                cls._load_containers_and_prefixes()
            cls._regex_cache["is_admins_group"] = re.compile(
                r"cn={}-[^,]+?,cn=ouadmins,cn=groups,{}".format(
                    cls._containerAdmins, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["is_admins_group"]

    @classmethod
    def get_staff_group_regex(cls) -> Pattern:
        if "staff" not in cls._regex_cache:
            if not cls._containerStaff:
                cls._load_containers_and_prefixes()

            cls._regex_cache["staff"] = re.compile(
                r"cn={}-(?P<ou>[^,]?),cn=groups,ou=(?P=ou),{}".format(
                    cls._containerStaff, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )

        return cls._regex_cache["staff"]

    @classmethod
    def get_students_group_regex(cls) -> Pattern:
        if "students" not in cls._regex_cache:
            if not cls._containerStudents:
                cls._load_containers_and_prefixes()
            cls._regex_cache["students"] = re.compile(
                r"cn={}-(?P<ou>[^,]?),cn=groups,ou=(?P=ou),{}".format(
                    cls._containerStudents, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )

        return cls._regex_cache["students"]

    @classmethod
    def get_students_pos_regex(cls) -> Pattern:
        if "students_pos" not in cls._regex_cache:
            if not cls._containerStudents:
                cls._load_containers_and_prefixes()
            cls._regex_cache["students_pos"] = re.compile(
                r"cn={},cn=users,ou=[^,]+,{}".format(cls._containerStudents, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["students_pos"]

    @classmethod
    def get_teachers_pos_regex(cls) -> Pattern:
        if "teachers_pos" not in cls._regex_cache:
            if not cls._containerTeachers:
                cls._load_containers_and_prefixes()
            cls._regex_cache["teachers_pos"] = re.compile(
                r"cn={},cn=users,ou=[^,]+,{}".format(cls._containerTeachers, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["teachers_pos"]

    @classmethod
    def get_staff_pos_regex(cls) -> Pattern:
        if "staff_pos" not in cls._regex_cache:
            if not cls._containerStaff:
                cls._load_containers_and_prefixes()
            cls._regex_cache["staff_pos"] = re.compile(
                r"cn={},cn=users,ou=[^,]+,{}".format(cls._containerStaff, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["staff_pos"]

    @classmethod
    def get_teachers_and_staff_pos_regex(cls) -> Pattern:
        if "teachers_and_staff_pos" not in cls._regex_cache:
            if not cls._containerTeachersAndStaff:
                cls._load_containers_and_prefixes()
            cls._regex_cache["teachers_and_staff_pos"] = re.compile(
                r"cn={},cn=users,ou=[^,]+,{}".format(
                    cls._containerTeachersAndStaff, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["teachers_and_staff_pos"]

    @classmethod
    def get_admins_pos_regex(cls) -> Pattern:
        if "admins_pos" not in cls._regex_cache:
            if not cls._containerAdmins:
                cls._load_containers_and_prefixes()
            cls._regex_cache["admins_pos"] = re.compile(
                r"cn={},cn=users,ou=[^,]+,{}".format(cls._containerAdmins, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["admins_pos"]

    @classmethod
    def get_exam_users_pos_regex(cls) -> Pattern:
        if "exam_user_pos" not in cls._regex_cache:
            if not cls._examUserContainerName:
                cls._load_containers_and_prefixes()
            cls._regex_cache["exam_user_pos"] = re.compile(
                r"cn={},ou=[^,]+,{}".format(cls._examUserContainerName, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["exam_user_pos"]

    @classmethod
    def get_exam_users_pos_regex(cls) -> Pattern:
        if "exam_user_pos" not in cls._regex_cache:
            if not cls._examUserContainerName:
                cls._load_containers_and_prefixes()
            cls._regex_cache["exam_user_pos"] = re.compile(
                r"cn={},ou=[^,]+,{}".format(cls._examUserContainerName, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["exam_user_pos"]

    @classmethod
    def get_schoolclass_pos_regex(cls) -> Pattern:
        if "schoolclass_pos" not in cls._regex_cache:
            if not cls._containerStudents or not cls._containerClass:
                cls._load_containers_and_prefixes()
            cls._regex_cache["schoolclass_pos"] = re.compile(
                r"cn={},cn={},cn=groups,ou=[^,]+?,{}".format(
                    cls._containerClass, cls._containerStudents, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["schoolclass_pos"]

    @classmethod
    def get_workgroup_pos_regex(cls) -> Pattern:
        if "workgroup_pos" not in cls._regex_cache:
            if not cls._containerStudents:
                cls._load_containers_and_prefixes()
            cls._regex_cache["workgroup_pos"] = re.compile(
                r"cn={},cn=groups,ou=[^,]+?,{}".format(cls._containerStudents, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["workgroup_pos"]

    @classmethod
    def get_computerroom_pos_regex(cls) -> Pattern:
        if "computerroom_pos" not in cls._regex_cache:
            if not cls._containerRooms:
                cls._load_containers_and_prefixes()
            cls._regex_cache["computerroom_pos"] = re.compile(
                r"cn={},cn=groups,ou=[^,]+?,{}".format(cls._containerRooms, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["computerroom_pos"]

    @classmethod
    def get_workgroup_share_pos_regex(cls) -> Pattern:
        if "workgroup_share_pos" not in cls._regex_cache:
            cls._regex_cache["workgroup_share_pos"] = re.compile(
                r"cn=shares,ou=[^,]+?,{}".format(cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["workgroup_share_pos"]

    @classmethod
    def get_school_class_share_pos_regex(cls) -> Pattern:
        if "school_class_share_pos" not in cls._regex_cache:
            if not cls._containerClass:
                cls._load_containers_and_prefixes()
            cls._regex_cache["school_class_share_pos"] = re.compile(
                r"cn={},cn=shares,ou=[^,]+?,{}".format(cls._containerClass, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["school_class_share_pos"]
