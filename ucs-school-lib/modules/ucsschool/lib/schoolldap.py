#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# SPDX-FileCopyrightText: 2007-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import re
from typing import Dict, Optional, Pattern, Sequence  # noqa: F401

from ldap.dn import dn2str, escape_dn_chars, explode_dn, str2dn

from univention.config_registry import ConfigRegistry


class SchoolSearchBase(object):
    """Deprecated: don't use position to identify user objects"""

    ucr = None  # type: ConfigRegistry
    _regex_cache = {}  # type: Dict[str, Pattern]

    # templates
    user_container_regex_template = r"cn={},cn=users,ou=[^,]+,{}"
    group_container_regex_template = r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}"
    groups_dn_template = "cn={}{},cn=groups,{}"
    users_container_dn_template = "cn={},cn=users,{}"

    # prefixes
    _containerAdmins = ""
    _containerStudents = ""
    _containerStaff = ""
    _containerTeachersAndStaff = ""
    _containerTeachers = ""
    _containerLegalGuardians = ""
    _containerClass = ""
    _containerRooms = ""
    _examUserContainerName = ""
    _examGroupNameTemplate = ""
    group_prefix_students = ""
    group_prefix_teachers = ""
    group_prefix_legal_guardians = ""
    group_prefix_admins = ""
    group_prefix_staff = ""

    def __init__(self, availableSchools, school=None, dn=None, ldapBase=None):
        #  type: (Sequence[str], Optional[str], Optional[str], Optional[str]) -> None
        if not self.ucr:
            self._load_ucr()

        self._ldapBase = ldapBase or self.ucr.get("ldap/base")

        from ucsschool.lib.models.school import School

        self._school = school or availableSchools[0]
        self._schoolDN = dn or School.cache(self.school).dn
        if not self._containerAdmins:
            self._load_containers_and_prefixes()

    @classmethod
    def _load_containers_and_prefixes(cls):  # type: () -> None
        if not cls.ucr:
            cls._load_ucr()
        cls._containerAdmins = cls.ucr.get("ucsschool/ldap/default/container/admins", "admins")
        cls._containerStudents = cls.ucr.get("ucsschool/ldap/default/container/pupils", "schueler")
        cls._containerStaff = cls.ucr.get("ucsschool/ldap/default/container/staff", "mitarbeiter")
        cls._containerTeachersAndStaff = cls.ucr.get(
            "ucsschool/ldap/default/container/teachers-and-staff", "lehrer und mitarbeiter"
        )
        cls._containerTeachers = cls.ucr.get("ucsschool/ldap/default/container/teachers", "lehrer")
        cls._containerLegalGuardians = cls.ucr.get(
            "ucsschool/ldap/default/container/legal_guardians", "sorgeberechtigte"
        )
        cls._containerClass = cls.ucr.get("ucsschool/ldap/default/container/class", "klassen")
        cls._containerRooms = cls.ucr.get("ucsschool/ldap/default/container/rooms", "raeume")
        cls._examUserContainerName = cls.ucr.get("ucsschool/ldap/default/container/exam", "examusers")
        cls._examGroupNameTemplate = cls.ucr.get(
            "ucsschool/ldap/default/groupname/exam", "OU%(ou)s-Klassenarbeit"
        )
        cls.group_prefix_students = cls.ucr.get("ucsschool/ldap/default/groupprefix/pupils", "schueler-")
        cls.group_prefix_teachers = cls.ucr.get("ucsschool/ldap/default/groupprefix/teachers", "lehrer-")
        cls.group_prefix_legal_guardians = cls.ucr.get(
            "ucsschool/ldap/default/groupprefix/legal_guardians", "sorgeberechtigte-"
        )  # default value required on non-PDN-systems
        cls.group_prefix_admins = cls.ucr.get("ucsschool/ldap/default/groupprefix/admins", "admins-")
        cls.group_prefix_staff = cls.ucr.get("ucsschool/ldap/default/groupprefix/staff", "mitarbeiter-")

    @classmethod
    def _load_ucr(cls):  # type: () -> ConfigRegistry
        cls.ucr = ConfigRegistry()
        cls.ucr.load()
        return cls.ucr

    @classmethod
    def getOU(cls, dn):  # type: (str) -> str
        """
        Return the school OU for a given DN.

        >>> SchoolSearchBase.getOU('uid=a,fou=bar,Ou=dc1,oU=dc,dc=foo,dc=bar')
        'dc1'
        """
        try:
            return next(val for x in str2dn(dn) for attr, val, z in x if attr.lower() == "ou")
        except StopIteration:
            pass

    @classmethod
    def getOUDN(cls, dn):  # type: (str) -> str
        """
        Return the School OU-DN part for a given DN.

        >>> SchoolSearchBase.getOUDN('uid=a,fou=bar,Ou=dc1,oU=dc,dc=foo,dc=bar')
        'Ou=dc1,oU=dc,dc=foo,dc=bar'
        >>> SchoolSearchBase.getOUDN('ou=dc1,ou=dc,dc=foo,dc=bar')
        'ou=dc1,ou=dc,dc=foo,dc=bar'
        >>> SchoolSearchBase.getOUDN('dc=foo,dc=bar')
        'dc=foo,dc=bar'
        """
        sdn = str2dn(dn)
        index = 0
        for part in sdn:
            if any(x[0].lower() == "ou" for x in part):
                break
            index += 1
        else:
            return dn
        return dn2str(sdn[index:])

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
    def students_group(self):  # type: () -> str
        return self.groups_dn_template.format(
            escape_dn_chars(self.group_prefix_students),
            escape_dn_chars(self.school.lower()),
            self.schoolDN,
        )

    @property
    def teachers_group(self):  # type: () -> str
        return self.groups_dn_template.format(
            escape_dn_chars(self.group_prefix_teachers),
            escape_dn_chars(self.school.lower()),
            self.schoolDN,
        )

    @property
    def legal_guardians_group(self):  # type: () -> str
        return self.groups_dn_template.format(
            escape_dn_chars(self.group_prefix_legal_guardians),
            escape_dn_chars(self.school.lower()),
            self.schoolDN,
        )

    @property
    def staff_group(self):  # type: () -> str
        return self.groups_dn_template.format(
            escape_dn_chars(self.group_prefix_staff),
            escape_dn_chars(self.school.lower()),
            self.schoolDN,
        )

    @property
    def admins_group(self):  # type: () -> str
        return "cn=%s%s,cn=ouadmins,cn=groups,%s" % (
            escape_dn_chars(self.group_prefix_admins),
            escape_dn_chars(self.school.lower()),
            self._ldapBase,
        )

    @property
    def workgroups(self):  # type: () -> str
        return "cn=%s,cn=groups,%s" % (escape_dn_chars(self._containerStudents), self.schoolDN)

    @property
    def classes(self):  # type: () -> str
        return "cn=%s,cn=%s,cn=groups,%s" % (
            escape_dn_chars(self._containerClass),
            escape_dn_chars(self._containerStudents),
            self.schoolDN,
        )

    @property
    def rooms(self):  # type: () -> str
        return "cn=%s,cn=groups,%s" % (escape_dn_chars(self._containerRooms), self.schoolDN)

    @property
    def students(self):  # type: () -> str
        return self.users_container_dn_template.format(
            escape_dn_chars(self._containerStudents), self.schoolDN
        )

    @property
    def teachers(self):  # type: () -> str
        return self.users_container_dn_template.format(
            escape_dn_chars(self._containerTeachers), self.schoolDN
        )

    @property
    def legal_guardians(self):  # type: () -> str
        return self.users_container_dn_template.format(
            escape_dn_chars(self._containerLegalGuardians), self.schoolDN
        )

    @property
    def teachersAndStaff(self):  # type: () -> str
        return self.users_container_dn_template.format(
            escape_dn_chars(self._containerTeachersAndStaff), self.schoolDN
        )

    @property
    def staff(self):  # type: () -> str
        return self.users_container_dn_template.format(
            escape_dn_chars(self._containerStaff), self.schoolDN
        )

    @property
    def admins(self):  # type: () -> str
        return self.users_container_dn_template.format(
            escape_dn_chars(self._containerAdmins), self.schoolDN
        )

    @property
    def classShares(self):  # type: () -> str
        return "cn=%s,cn=shares,%s" % (escape_dn_chars(self._containerClass), self.schoolDN)

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
        return "cn=%s,%s" % (escape_dn_chars(self._examUserContainerName), self.schoolDN)

    @property
    def globalGroupContainer(self):  # type: () -> str
        return "cn=ouadmins,cn=groups,%s" % (self._ldapBase,)

    @property
    def educationalDCGroup(self):  # type: () -> str
        return "cn=OU%s-DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (
            escape_dn_chars(self.school),
            self._ldapBase,
        )

    @property
    def educationalMemberGroup(self):  # type: () -> str
        return "cn=OU%s-Member-Edukativnetz,cn=ucsschool,cn=groups,%s" % (
            escape_dn_chars(self.school),
            self._ldapBase,
        )

    @property
    def administrativeDCGroup(self):  # type: () -> str
        return "cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (
            escape_dn_chars(self.school),
            self._ldapBase,
        )

    @property
    def administrativeMemberGroup(self):  # type: () -> str
        return "cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (
            escape_dn_chars(self.school),
            self._ldapBase,
        )

    @property
    def examGroupName(self):  # type: () -> str
        # replace '%(ou)s' strings in generic exam_group_name
        ucr_value_keywords = {"ou": self.school}
        return self._examGroupNameTemplate % ucr_value_keywords

    @property
    def examGroup(self):  # type: () -> str
        return "cn=%s,cn=ucsschool,cn=groups,%s" % (escape_dn_chars(self.examGroupName), self._ldapBase)

    def isWorkgroup(self, groupDN):  # type: (str) -> bool
        # a workgroup cannot lie in a sub directory
        if not groupDN.lower().endswith(self.workgroups.lower()):
            return False
        return len(explode_dn(groupDN)) - len(explode_dn(self.workgroups)) == 1

    def isGroup(self, groupDN):  # type: (str) -> bool
        return groupDN.lower().endswith(self.groups.lower())

    def isClass(self, groupDN):  # type: (str) -> bool
        return groupDN.lower().endswith(self.classes.lower())

    def isRoom(self, groupDN):  # type: (str) -> bool
        return groupDN.lower().endswith(self.rooms.lower())

    @classmethod
    def get_is_teachers_group_regex(cls):  # type: () -> Pattern
        if "is_teachers_group" not in cls._regex_cache:
            if not cls._containerTeachers:
                cls._load_containers_and_prefixes()
            cls._regex_cache["is_teachers_group"] = re.compile(
                cls.group_container_regex_template.format(cls._containerTeachers, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["is_teachers_group"]

    @classmethod
    def get_is_legal_guardians_group_regex(cls):  # type: () -> Pattern
        if "is_legal_guardians_group" not in cls._regex_cache:
            if not cls._containerLegalGuardians:
                cls._load_containers_and_prefixes()
            cls._regex_cache["is_legal_guardians_group"] = re.compile(
                cls.group_container_regex_template.format(
                    cls._containerLegalGuardians, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["is_legal_guardians_group"]

    @classmethod
    def get_is_admins_group_regex(cls):  # type: () -> Pattern
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
    def get_is_staff_group_regex(cls):  # type: () -> Pattern
        if "is_staff_group" not in cls._regex_cache:
            if not cls._containerStaff:
                cls._load_containers_and_prefixes()
            cls._regex_cache["is_staff_group"] = re.compile(
                cls.group_container_regex_template.format(cls._containerStaff, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["is_staff_group"]

    @classmethod
    def get_is_student_group_regex(cls):  # type: () -> Pattern
        if "is_student_group" not in cls._regex_cache:
            if not cls._containerStudents:
                cls._load_containers_and_prefixes()
            cls._regex_cache["is_student_group"] = re.compile(
                cls.group_container_regex_template.format(cls._containerStudents, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["is_student_group"]

    @classmethod
    def get_staff_group_regex(cls):  # type: () -> Pattern
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
    def get_students_group_regex(cls):  # type: () -> Pattern
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
    def get_students_pos_regex(cls):  # type: () -> Pattern
        if "students_pos" not in cls._regex_cache:
            if not cls._containerStudents:
                cls._load_containers_and_prefixes()
            cls._regex_cache["students_pos"] = re.compile(
                cls.user_container_regex_template.format(cls._containerStudents, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["students_pos"]

    @classmethod
    def get_teachers_pos_regex(cls):  # type: () -> Pattern
        if "teachers_pos" not in cls._regex_cache:
            if not cls._containerTeachers:
                cls._load_containers_and_prefixes()
            cls._regex_cache["teachers_pos"] = re.compile(
                cls.user_container_regex_template.format(cls._containerTeachers, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["teachers_pos"]

    @classmethod
    def get_legal_guardians_pos_regex(cls):  # type: () -> Pattern
        if "legal_guardians_pos" not in cls._regex_cache:
            if not cls._containerLegalGuardians:
                cls._load_containers_and_prefixes()
            cls._regex_cache["legal_guardians_pos"] = re.compile(
                cls.user_container_regex_template.format(
                    cls._containerLegalGuardians, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["legal_guardians_pos"]

    @classmethod
    def get_staff_pos_regex(cls):  # type: () -> Pattern
        if "staff_pos" not in cls._regex_cache:
            if not cls._containerStaff:
                cls._load_containers_and_prefixes()
            cls._regex_cache["staff_pos"] = re.compile(
                cls.user_container_regex_template.format(cls._containerStaff, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["staff_pos"]

    @classmethod
    def get_teachers_and_staff_pos_regex(cls):  # type: () -> Pattern
        if "teachers_and_staff_pos" not in cls._regex_cache:
            if not cls._containerTeachersAndStaff:
                cls._load_containers_and_prefixes()
            cls._regex_cache["teachers_and_staff_pos"] = re.compile(
                cls.user_container_regex_template.format(
                    cls._containerTeachersAndStaff, cls.ucr["ldap/base"]
                ),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["teachers_and_staff_pos"]

    @classmethod
    def get_admins_pos_regex(cls):  # type: () -> Pattern
        if "admins_pos" not in cls._regex_cache:
            if not cls._containerAdmins:
                cls._load_containers_and_prefixes()
            cls._regex_cache["admins_pos"] = re.compile(
                cls.user_container_regex_template.format(cls._containerAdmins, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["admins_pos"]

    @classmethod
    def get_exam_users_pos_regex(cls):  # type: () -> Pattern
        if "exam_user_pos" not in cls._regex_cache:
            if not cls._examUserContainerName:
                cls._load_containers_and_prefixes()
            cls._regex_cache["exam_user_pos"] = re.compile(
                r"cn={},ou=[^,]+,{}".format(cls._examUserContainerName, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["exam_user_pos"]

    @classmethod
    def get_schoolclass_pos_regex(cls):  # type: () -> Pattern
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
    def get_workgroup_pos_regex(cls):  # type: () -> Pattern
        if "workgroup_pos" not in cls._regex_cache:
            if not cls._containerStudents:
                cls._load_containers_and_prefixes()
            cls._regex_cache["workgroup_pos"] = re.compile(
                r"cn={},cn=groups,ou=[^,]+?,{}".format(cls._containerStudents, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["workgroup_pos"]

    @classmethod
    def get_computerroom_pos_regex(cls):  # type: () -> Pattern
        if "computerroom_pos" not in cls._regex_cache:
            if not cls._containerRooms:
                cls._load_containers_and_prefixes()
            cls._regex_cache["computerroom_pos"] = re.compile(
                r"cn={},cn=groups,ou=[^,]+?,{}".format(cls._containerRooms, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["computerroom_pos"]

    @classmethod
    def get_workgroup_share_pos_regex(cls):  # type: () -> Pattern
        if "workgroup_share_pos" not in cls._regex_cache:
            cls._regex_cache["workgroup_share_pos"] = re.compile(
                r"cn=shares,ou=[^,]+?,{}".format(cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["workgroup_share_pos"]

    @classmethod
    def get_school_class_share_pos_regex(cls):  # type: () -> Pattern
        if "school_class_share_pos" not in cls._regex_cache:
            if not cls._containerClass:
                cls._load_containers_and_prefixes()
            cls._regex_cache["school_class_share_pos"] = re.compile(
                r"cn={},cn=shares,ou=[^,]+?,{}".format(cls._containerClass, cls.ucr["ldap/base"]),
                flags=re.IGNORECASE,
            )
        return cls._regex_cache["school_class_share_pos"]
