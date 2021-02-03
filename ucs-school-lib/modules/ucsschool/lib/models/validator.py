# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2021 Univention GmbH
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

import logging
import re
import traceback
import uuid

try:
    from functools import lru_cache
    from typing import Dict, List, Optional

    from .base import UdmObject
except ImportError:
    pass

from ucsschool.lib.models.utils import get_file_handler, get_stream_handler, ucr
from ucsschool.lib.roles import (
    create_ucsschool_role_string,
    role_computer_room,
    role_exam_user,
    role_marketplace_share,
    role_school_admin,
    role_school_class,
    role_school_class_share,
    role_staff,
    role_student,
    role_teacher,
    role_workgroup,
    role_workgroup_share,
)

LOG_FILE = "/var/log/univention/ucsschool-kelvin-rest-api/ucs-school-validation.log"
VALIDATION_LOGGER = "UCSSchool-Validation"
private_data_logger = logging.getLogger(VALIDATION_LOGGER)
private_data_logger.setLevel("DEBUG")
private_data_logger.addHandler(
    get_file_handler("DEBUG", LOG_FILE, uid=0, gid=0, backupCount=1000)
)


container_teachers = ucr.get("ucsschool/ldap/default/containers/teachers", "lehrer")
container_staff = ucr.get("ucsschool/ldap/default/containers/staff", "mitarbeiter")
container_teachers_and_staff = ucr.get(
    "ucsschool/ldap/default/containers/teachers-and-staff", "lehrer und mitarbeiter"
)
container_students = ucr.get("ucsschool/ldap/default/containers/pupils", "schueler")
container_exam_students = ucr.get("ucsschool/ldap/default/container/exam", "examusers")
container_computerrooms = ucr.get("ucsschool/ldap/default/container/rooms", "raeume")
exam_students_group = ucr.get(
    "ucsschool/ldap/default/groupname/exam", "OU%(ou)s-Klassenarbeit"
)

teachers_group_regex = re.compile(
    r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(
        container_teachers, ucr["ldap/base"]
    ),
    flags=re.IGNORECASE,
)
staff_group_regex = re.compile(
    r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(
        container_staff, ucr["ldap/base"]
    ),
    flags=re.IGNORECASE,
)
students_group_regex = re.compile(
    r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(
        container_students, ucr["ldap/base"]
    ),
    flags=re.IGNORECASE,
)


def split_roles(roles):  # type(List[str]) -> List[List[str]]
    return [r.split(":") for r in roles]


def obj_to_dict_conversion(func):
    """
    Decorator which converts an obj object to dict.
    To make testing easier, objects of type dicts are passed directly.
    """

    def _inner(obj, logger):
        if type(obj) is dict:
            dict_obj = obj
        else:
            dict_obj = obj.to_dict()
        return func(dict_obj, logger)

    return _inner


def is_student_role(role):  # type(str) -> bool
    return role in (role_student, role_exam_user)


def validate_group_membership(
    dn, student=False, teacher=False, staff=False
):  # type(str, bool, bool, bool) -> Optional[str]
    """
    Check if user is allowed in group with group_dn.
    E.g. a Teacher should not be part of any students groups.
    """
    if (
        (students_group_regex.match(dn) and not student)
        or (teachers_group_regex.match(dn) and not teacher)
        or (staff_group_regex.match(dn) and not staff)
    ):
        return "Disallowed member of group {}".format(dn)


class SchoolValidator(object):
    position_regex = None
    attributes = []
    roles = []
    container = ""

    @classmethod
    def validate(cls, obj, **kwargs):  # type(Dict[Any], Dict[Any]) -> List[str]
        expected_groups = kwargs.get("expected_groups", [])
        expected_roles = kwargs.get("expected_roles", [])
        errors = list()
        errors.append(cls.required_attributes(obj["props"]))
        errors.append(cls.position(obj["position"]))
        if expected_roles:
            errors.append(
                cls.required_roles(
                    obj["props"].get("ucsschoolRole", []), expected_roles
                )
            )
        if expected_groups:
            errors.append(
                cls.required_groups(obj["props"].get("groups", []), expected_groups)
            )
        return errors

    @classmethod
    def required_groups(
        cls, groups, expected_groups
    ):  # type(List[str], List[Any]) -> Optional[str]
        """
        Object should be in all groups. I test with g.endswith(group) to
        also catch classes without using regexes.
        """
        missing_groups = []
        for group in expected_groups:
            if not any([g for g in groups if g.endswith(group)]):
                missing_groups.append(group)
        if missing_groups:
            return "is missing groups at positions {!r}".format(missing_groups)

    @classmethod
    def required_attributes(cls, props):  # type(Dict[Any]) -> Optional[str]
        missing_attributes = [
            attr for attr in cls.attributes if not props.get(attr, "")
        ]
        if missing_attributes:
            return "is missing required attributes: {!r}.".format(missing_attributes)

    @classmethod
    def position(cls, position):  # type(str) -> Optional[str]
        if not cls.position_regex.match(position):
            return "has wrong position in ldap."

    @classmethod
    def required_roles(
        cls, roles, expected_roles
    ):  # type(List[str], List[str]) -> Optional[str]
        missing_roles = [role for role in expected_roles if role not in roles]
        if missing_roles:
            return "is missing roles {!r}".format(missing_roles)

    @classmethod
    def roles_at_school(cls, schools):  # type(List[str]) -> List[str]
        """
        Get all roles for all schools which the object is expected to have.
        """
        expected_roles = []
        for role in cls.roles:
            for school in schools:
                expected_roles.append(create_ucsschool_role_string(role, school))
        return expected_roles


class UserValidator(SchoolValidator):
    is_student = False
    is_exam_user = False
    is_teacher = False
    is_staff = False
    attributes = [
        "username",
        "ucsschoolRole",
        "school",
        "firstname",
        "lastname",
    ]

    @classmethod
    def validate(cls, obj, **kwargs):  # type(Dict[Any], Dict[Any]) -> List[str]
        expected_groups = kwargs.get("expected_groups", [])
        expected_roles = kwargs.get("expected_roles", [])
        schools = obj["props"].get("school", [])
        groups = obj["props"].get("groups", [])
        roles = split_roles(obj["props"].get("ucsschoolRole", []))

        expected_roles.extend(cls.roles_at_school(schools))
        expected_groups.extend(cls.domain_users_group(schools))
        expected_groups.extend(cls.role_groups(schools))
        errors = super(UserValidator, cls).validate(
            obj, expected_roles=expected_roles, expected_groups=expected_groups
        )

        errors.append(cls.part_of_school(roles, schools))
        errors.append(cls.student_roles(roles))
        errors.extend(cls.group_membership(groups))
        return errors

    @classmethod
    def part_of_school(
        cls, roles, schools
    ):  # type(List[str], List[str]) -> Optional[str]
        """
        Users should not have roles with schools which they don't have.
        """
        missing_schools = list(
            set([s for r, c, s in roles if c == "school" and s not in schools])
        )
        if missing_schools:
            return "is not part of schools: {!r}.".format(missing_schools)

    @classmethod
    def student_roles(cls, roles):  # type(List[str]) -> Optional[str]
        """
        Students should not have teacher, staff or school_admin role.
        """
        not_allowed_for_students = [role_teacher, role_staff, role_school_admin]
        for r, c, s in roles:
            if (cls.is_student and r in not_allowed_for_students) or (
                not cls.is_student and r in [role_student, role_exam_user]
            ):
                return "Students must not have these roles: {!r}.".format(
                    not_allowed_for_students
                )

    @classmethod
    def domain_users_group(cls, schools):  # type(List[str]) -> List[str]
        """
        Users should be inside the `Domain Users OU` of their schools.
        """
        return [
            "cn=Domain Users {0},cn=groups,ou={0},{1}".format(school, ucr["ldap/base"])
            for school in schools
        ]

    @classmethod
    def role_groups(cls, schools):  # type(List[str]) -> List[str]
        """
        Users with `cls.role` should be in the corresponding group at
        each school they are part of.
        Special cases ExamUsers and TeachersAndStaff are handled in subclasses.
        """
        if cls in [ExamStudentValidator, TeachersAndStaffValidator]:
            return []
        return [
            "cn={}-{},cn=groups,ou={},{}".format(
                cls.container, school.lower(), school, ucr["ldap/base"]
            )
            for school in schools
        ]

    @classmethod
    def group_membership(cls, groups):  # type(List[str]) -> List[str]
        """
        Validate group membership, e.g. students should not be in teachers group.
        """
        return [
            validate_group_membership(
                group,
                student=cls.is_student,
                teacher=cls.is_teacher,
                staff=cls.is_staff,
            )
            for group in groups
        ]


class StudentValidator(UserValidator):
    container = container_students
    position_regex = re.compile(
        r"cn={},cn=users,ou=[^,]+,{}".format(container, ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )
    is_student = True
    roles = [role_student]

    @classmethod
    def validate(cls, obj, **kwargs):  # type(Dict[Any], Dict[Any]) -> List[str]
        expected_groups = kwargs.get("expected_groups", [])
        expected_roles = kwargs.get("expected_roles", [])

        expected_groups.extend(cls.classes_at_schools(obj["props"]["school"]))
        return super(StudentValidator, cls).validate(
            obj, expected_roles=expected_roles, expected_groups=expected_groups
        )

    @classmethod
    def classes_at_schools(cls, schools):  # type(List[str]) -> List[str]
        """
        Students have at least one class at every school.
        """
        return [
            "cn=klassen,cn={},cn=groups,ou={},{}".format(
                container_students, school, ucr["ldap/base"]
            )
            for school in schools
        ]


class TeacherValidator(UserValidator):
    container = container_teachers
    position_regex = re.compile(
        r"cn={},cn=users,ou=[^,]+,{}".format(container, ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )
    is_teacher = True
    roles = [role_teacher]


class ExamStudentValidator(StudentValidator):
    container = container_exam_students
    position_regex = re.compile(
        r"cn={},ou=[^,]+,{}".format(container, ucr["ldap/base"]), flags=re.IGNORECASE
    )
    is_exam_user = True
    is_student = True
    roles = [role_exam_user]

    @classmethod
    def validate(cls, obj, **kwargs):  # type(Dict[Any], Dict[Any]) -> List[str]
        expected_groups = kwargs.get("expected_groups", [])
        expected_roles = kwargs.get("expected_roles", [])
        schools = obj["props"].get("school", [])
        roles = obj["props"].get("ucsschoolRole", [])

        expected_groups.extend(cls.exam_group(schools))
        errors = super(ExamStudentValidator, cls).validate(
            obj, expected_roles=expected_roles, expected_groups=expected_groups
        )
        errors.append(cls.exam_contexts(roles))
        return errors

    @classmethod
    def exam_contexts(cls, roles):  # type(List[str]) -> List[str]
        """
        ExamUsers should have a role with context `exam`,
        e.g exam_user:exam:demo-exam-DEMOSCHOOL.
        """
        exam_roles = [
            r for r, c, s in split_roles(roles) if c == "exam" and r == role_exam_user
        ]
        if not exam_roles:
            return "is missing role with context exam."

    @classmethod
    def exam_group(cls, schools):  # type(List[str]) -> List[str]
        """
        ExamUsers should be inside a corresponding group in each of their schools.
        """
        return [
            "cn={},cn=ucsschool,cn=groups,{}".format(
                exam_students_group % {"ou": school.lower()}, ucr["ldap/base"]
            )
            for school in schools
        ]


class StaffValidator(UserValidator):
    container = container_staff
    position_regex = re.compile(
        r"cn={},cn=users,ou=[^,]+,{}".format(container, ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )
    is_staff = True
    roles = [role_staff]


class TeachersAndStaffValidator(UserValidator):
    container = container_teachers_and_staff
    position_regex = re.compile(
        r"cn={},cn=users,ou=[^,]+,{}".format(container, ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )
    is_teacher = True
    is_staff = True
    roles = [role_teacher, role_staff]

    @classmethod
    def validate(cls, obj, **kwargs):  # type(Dict[Any], Dict[Any]) -> List[str]
        expected_groups = kwargs.get("expected_groups", [])
        expected_roles = kwargs.get("expected_roles", [])

        schools = obj["props"]["school"]
        expected_groups.extend(cls.teachers_and_staff_groups(schools))
        return super(TeachersAndStaffValidator, cls).validate(
            obj, expected_roles=expected_roles, expected_groups=expected_groups
        )

    @classmethod
    def teachers_and_staff_groups(cls, schools):  # type(List[str]) -> List[str]
        """
        TeachersAndStaff Users should be inside teachers and staff groups in
        all of their schools.
        """
        expected_groups = []
        for school in schools:
            for container in [container_teachers, container_staff]:
                expected_groups.append(
                    "cn={}-{},cn=groups,ou={},{}".format(
                        container, school.lower(), school, ucr["ldap/base"]
                    )
                )
        return expected_groups


class GroupAndShareValidator(SchoolValidator):
    attributes = [
        "name",
        "ucsschoolRole",
    ]

    @staticmethod
    def _extract_ou(dn):  # type(str) -> str
        """
        Groups and shares do not have the property school,
        so it is extracted of the dn.
        """
        res = re.search(r"ou=([^,]+)", dn)
        if res:
            return res.group(1)

    @classmethod
    def validate(cls, obj, **kwargs):  # type(Dict[Any], Dict[Any]) -> List[str]
        expected_roles = kwargs.get("expected_roles", [])
        expected_groups = kwargs.get("expected_groups", [])

        school = GroupAndShareValidator._extract_ou(obj["dn"])
        # note: groups and shares exist only at one ou.
        expected_roles.extend(cls.roles_at_school([school]))
        errors = super(GroupAndShareValidator, cls).validate(
            obj, expected_roles=expected_roles, expected_groups=expected_groups
        )
        errors.append(cls.school_prefix(obj["props"]["name"], school))
        return errors

    @classmethod
    def school_prefix(cls, name, school):  # type(str, str) -> Optional[str]
        """
        Groups and Shares should have a school prefix in their name, like `DEMOSCHOOL-Democlass`
        """
        if role_marketplace_share not in cls.roles:
            if school and name and not name.startswith("{}-".format(school)):
                return "has an incorrect school prefix for school {}.".format(school)


class SchoolClassValidator(GroupAndShareValidator):
    roles = [role_school_class]
    position_regex = re.compile(
        r"cn=klassen,cn={},cn=groups,ou=[^,]+?,{}".format(
            container_students, ucr["ldap/base"]
        ),
        flags=re.IGNORECASE,
    )


class WorkGroupValidator(GroupAndShareValidator):
    roles = [role_workgroup]
    position_regex = re.compile(
        r"cn={},cn=groups,ou=[^,]+?,{}".format(container_students, ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )


class ComputerroomValidator(GroupAndShareValidator):
    roles = [role_computer_room]
    position_regex = re.compile(
        r"cn={},cn=groups,ou=[^,]+?,{}".format(
            container_computerrooms, ucr["ldap/base"]
        ),
        flags=re.IGNORECASE,
    )


class WorkGroupShareValidator(GroupAndShareValidator):
    roles = [role_workgroup_share]
    position_regex = re.compile(
        r"cn=shares,ou=[^,]+?,{}".format(ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )


class ClasshareValidator(GroupAndShareValidator):
    roles = [role_school_class_share]
    position_regex = re.compile(
        r"cn=klassen,cn=shares,ou=[^,]+?,{}".format(ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )


class MarketplaceShareValidator(GroupAndShareValidator):
    roles = [role_marketplace_share]
    position_regex = re.compile(
        r"cn=shares,ou=[^,]+?,{}".format(ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )
    dn_regex = re.compile(
        r"cn=Marktplatz,cn=shares,ou=[^,]+?,{}".format(ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )


def get_class(obj):  # type(Dict[Any]) -> Optional[SchoolValidator]
    options = obj["options"]
    position = obj["position"]
    if "ucsschoolExam" in options:
        return ExamStudentValidator
    elif {"ucsschoolTeacher", "ucsschoolStaff"}.issubset(set(options)):
        return TeachersAndStaffValidator
    elif "ucsschoolStudent" in options:
        return StudentValidator
    elif "ucsschoolTeacher" in options:
        return TeacherValidator
    elif "ucsschoolStaff" in options:
        return StaffValidator
    elif SchoolClassValidator.position_regex.match(position):
        return SchoolClassValidator
    elif WorkGroupValidator.position_regex.match(position):
        return WorkGroupValidator
    elif ComputerroomValidator.position_regex.match(position):
        return ComputerroomValidator
    elif ClasshareValidator.position_regex.match(position):
        return ClasshareValidator
    elif MarketplaceShareValidator.dn_regex.match(obj["dn"]):
        # note: MarketplaceShares have the same position as WorkgroupShares,
        # but are unique for ous.
        return MarketplaceShareValidator
    elif WorkGroupShareValidator.position_regex.match(position):
        return WorkGroupShareValidator


@obj_to_dict_conversion
def validate(obj, logger=None):  # type(Dict[Any], logging.Logger) -> None
    """
    Objects are validated as dicts and errors are logged to
    the passed logger. Sensitive data is only logged to /var/log/univention/ucs-school-validation.log
    """

    validation_class = get_class(obj)
    if validation_class:
        options = obj["options"]
        errors = validation_class.validate(obj)
        errors = list(filter(None, errors))
        if errors:
            validation_uuid = str(uuid.uuid4())
            errors_str = "{} UCS@school Object {} with options {} has validation errors:\n\t- {}\n".format(
                validation_uuid,
                obj.get("dn", ""),
                "{!r}".format(options),
                "\n\t- ".join(errors),
            )
            if logger:
                logger.error(errors_str)
            private_data_logger.error(errors_str)
            private_data_logger.error(obj)
            stack_trace = " ".join(traceback.format_stack()[:-2]).replace("\n", " ")
            private_data_logger.error(stack_trace)
