# -*- coding: utf-8 -*-
#
# UCS@school python lib
#
# Copyright 2021 Univention GmbH
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
import os
import re
import traceback
import uuid
from typing import Any, Dict, List, Optional, Type, Union

import ldap

from ucsschool.lib.models.utils import get_file_handler, ucr
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
from ucsschool.lib.schoolldap import SchoolSearchBase
from udm_rest_client import UdmObject

private_data_logger = None
if os.geteuid() == 0:
    LOG_FILE = "/var/log/univention/ucsschool-kelvin-rest-api/ucs-school-validation.log"
    VALIDATION_LOGGER = "UCSSchool-Validation"
    private_data_logger = logging.getLogger(VALIDATION_LOGGER)
    private_data_logger.setLevel("DEBUG")
    backup_count = int(ucr.get("ucsschool/validation/logging/backupcount", "").strip() or 60)
    private_data_logger.addHandler(
        get_file_handler("DEBUG", LOG_FILE, uid=0, gid=0, backupCount=backup_count)
    )


def split_roles(roles: List[str]) -> List[List[str]]:
    return [r.split(":") for r in roles]


def get_position_from(dn: str) -> Optional[str]:
    # note: obj.position does not have a position
    return ldap.dn.dn2str(ldap.dn.str2dn(dn)[1:])


def obj_to_dict(obj: UdmObject) -> Dict[str, Any]:
    return obj.to_dict()


def obj_to_dict_conversion(obj: Union[UdmObject, Dict[str, Any]]) -> Dict[str, Any]:
    if type(obj) is dict:
        dict_obj = obj
    else:
        dict_obj = obj_to_dict(obj)
    return dict_obj


def is_student_role(role: str) -> bool:
    return role in (role_student, role_exam_user)


class SchoolValidator(object):
    position_regex = None
    attributes = []
    roles = []

    @classmethod
    def validate(cls, obj: Dict[str, Any]) -> List[str]:
        errors = []
        roles = obj["props"].get("ucsschoolRole", [])
        errors.append(cls.required_roles(roles, cls.expected_roles(obj)))
        errors.append(cls.required_attributes(obj["props"]))
        errors.append(cls.position(obj["position"]))
        return errors

    @classmethod
    def required_attributes(cls, props: Dict[str, Any]) -> Optional[str]:
        missing_attributes = [attr for attr in cls.attributes if not props.get(attr, "")]
        if missing_attributes:
            return "is missing required attributes: {!r}.".format(missing_attributes)

    @classmethod
    def position(cls, position: str) -> Optional[str]:
        if not cls.position_regex.match(position):
            return "has wrong position in ldap."

    @classmethod
    def required_roles(cls, roles: List[str], expected_roles: List[str]) -> Optional[str]:
        missing_roles = [role for role in expected_roles if role not in roles]
        if missing_roles:
            return "is missing roles {!r}".format(missing_roles)

    @classmethod
    def roles_at_school(cls, schools: List[str]) -> List[str]:
        """
        Get all roles for all schools which the object is expected to have.
        """
        expected_roles = []
        for role in cls.roles:
            for school in schools:
                expected_roles.append(create_ucsschool_role_string(role, school))
        return expected_roles

    @classmethod
    def expected_roles(cls, obj: Dict[str, Any]) -> List[str]:
        return []

    @classmethod
    def get_search_base(cls, school: str) -> SchoolSearchBase:
        from .base import UCSSchoolHelperAbstractClass

        return UCSSchoolHelperAbstractClass.get_search_base(school)


class UserValidator(SchoolValidator):
    is_student = False
    is_exam_user = False
    is_teacher = False
    is_staff = False
    is_school_admin = False
    attributes = [
        "username",
        "ucsschoolRole",
        "school",
        "firstname",
        "lastname",
    ]

    @classmethod
    def validate(cls, obj: Dict[str, Any]) -> List[str]:
        schools = obj["props"].get("school", [])
        groups = obj["props"].get("groups", [])
        roles = split_roles(obj["props"].get("ucsschoolRole", []))
        errors = super(UserValidator, cls).validate(obj)
        errors.append(cls.validate_required_groups(groups, cls.expected_groups(obj)))
        errors.append(cls.validate_part_of_school(roles, schools))
        errors.append(cls.validate_student_roles(roles))
        errors.extend(cls.validate_group_membership(groups))
        return errors

    @classmethod
    def expected_roles(cls, obj: Dict[str, Any]) -> List[str]:
        schools = obj["props"].get("school", [])
        return cls.roles_at_school(schools)

    @classmethod
    def expected_groups(cls, obj: Dict[str, Any]) -> List[str]:
        """
        Collect expected groups of user. Overwrite for special cases in subclasses.
        """
        expected_groups = []
        schools = obj["props"].get("school", [])
        expected_groups.extend(cls.domain_users_group(schools))
        expected_groups.extend(cls.role_groups(schools))
        return expected_groups

    @classmethod
    def validate_required_groups(cls, groups: List[str], expected_groups: List[Any]) -> Optional[str]:
        """
        Object should be in all groups/ containers.
        E.g.: Students must have at least one group in `cn=klassen,cn=schueler,cn=groups,ou=ou`,
        which is true if the string ends with the classes position.
        For groups like `cn=schueler-ou` endwith is the same as equal.
        """
        missing_groups = [
            exp_group
            for exp_group in expected_groups
            if not any([grp.endswith(exp_group) for grp in groups])
        ]
        if missing_groups:
            return "is missing groups at positions {!r}".format(missing_groups)

    @classmethod
    def validate_part_of_school(cls, roles: List[List[str]], schools: List[str]) -> Optional[str]:
        """
        Users should not have roles with schools which they don't have.
        """
        missing_schools = set([s for r, c, s in roles if c == "school" and s not in schools])
        if missing_schools:
            return "is not part of schools: {!r}.".format(list(missing_schools))

    @classmethod
    def validate_student_roles(cls, roles: List[List[str]]) -> Optional[str]:
        """
        Students should not have teacher, staff or school_admin role.
        """
        not_allowed_for_students = [role_teacher, role_staff, role_school_admin]
        for r, c, s in roles:
            if (cls.is_student and r in not_allowed_for_students) or (
                not cls.is_student and r in [role_student, role_exam_user]
            ):
                return "must not have these roles: {!r}.".format(not_allowed_for_students)

    @classmethod
    def domain_users_group(cls, schools: List[str]) -> List[str]:
        """
        Users should be inside the `Domain Users OU` of their schools.
        """
        return [
            "cn=Domain Users {0},cn=groups,ou={0},{1}".format(school, ucr["ldap/base"])
            for school in schools
        ]

    @classmethod
    def role_groups(cls, schools: List[str]) -> List[str]:
        """
        Users with `cls.role` should be in the corresponding group at
        each school they are part of.
        Implemented in subclasses.
        """
        return []

    @classmethod
    def validate_group_membership(cls, groups: List[str]) -> List[str]:
        """
        Validate group membership, e.g. students should not be in teachers group.
        """
        return [
            "Disallowed member of group {}".format(dn)
            for dn in groups
            if (
                (SchoolSearchBase.get_is_student_group_regex().match(dn) and not cls.is_student)
                or (SchoolSearchBase.get_is_teachers_group_regex().match(dn) and not cls.is_teacher)
                or (SchoolSearchBase.get_is_staff_group_regex().match(dn) and not cls.is_staff)
                or (SchoolSearchBase.get_is_admins_group_regex().match(dn) and cls.is_student)
            )
        ]


class StudentValidator(UserValidator):
    position_regex = SchoolSearchBase.get_students_pos_regex()
    is_student = True
    roles = [role_student]

    @classmethod
    def expected_groups(cls, obj: Dict[str, Any]) -> List[str]:
        """
        Students have at least one class at every school.
        """
        schools = obj["props"].get("school", [])
        expected_groups = super(StudentValidator, cls).expected_groups(obj)
        expected_groups.extend([cls.get_search_base(school).classes for school in schools])
        return expected_groups

    @classmethod
    def role_groups(cls, schools: List[str]) -> List[str]:
        return [cls.get_search_base(school).students_group for school in schools]


class TeacherValidator(UserValidator):
    position_regex = SchoolSearchBase.get_teachers_pos_regex()
    is_teacher = True
    roles = [role_teacher]

    @classmethod
    def role_groups(cls, schools: List[str]) -> List[str]:
        return [cls.get_search_base(school).teachers_group for school in schools]


class ExamStudentValidator(StudentValidator):
    position_regex = SchoolSearchBase.get_exam_users_pos_regex()
    is_exam_user = True
    is_student = True
    roles = [role_exam_user]

    @classmethod
    def validate(cls, obj: Dict[str, Any]) -> List[str]:
        roles = obj["props"].get("ucsschoolRole", [])
        errors = super(ExamStudentValidator, cls).validate(obj)
        errors.append(cls.validate_exam_contexts(roles))
        return errors

    @classmethod
    def validate_exam_contexts(cls, roles: List[str]) -> str:
        """
        ExamUsers should have a role with context `exam`,
        e.g exam_user:exam:demo-exam-DEMOSCHOOL.
        """
        exam_roles = [r for r, c, s in split_roles(roles) if c == "exam" and r == role_exam_user]
        if not exam_roles:
            return "is missing role with context exam."

    @classmethod
    def role_groups(cls, schools: List[str]) -> List[str]:
        """
        ExamUsers should be inside a corresponding group in each of their schools.
        SchoolSearchBase.examGroup has no school.lower()
        """
        return [
            "cn={},cn=ucsschool,cn=groups,{}".format(
                SchoolSearchBase._examGroupNameTemplate % {"ou": school.lower()}, ucr["ldap/base"]
            )
            for school in schools
        ]


class StaffValidator(UserValidator):
    position_regex = SchoolSearchBase.get_staff_pos_regex()
    is_staff = True
    roles = [role_staff]

    @classmethod
    def role_groups(cls, schools: List[str]) -> List[str]:
        return [cls.get_search_base(school).staff_group for school in schools]


class TeachersAndStaffValidator(UserValidator):
    position_regex = SchoolSearchBase.get_teachers_and_staff_pos_regex()
    is_teacher = True
    is_staff = True
    roles = [role_teacher, role_staff]

    @classmethod
    def role_groups(cls, schools: List[str]) -> List[str]:
        """
        TeachersAndStaff Users should be inside teachers and staff groups in
        all of their schools.
        """
        expected_groups = []
        for school in schools:
            expected_groups.append(cls.get_search_base(school).teachers_group)
            expected_groups.append(cls.get_search_base(school).staff_group)
        return expected_groups


class SchoolAdminValidator(UserValidator):
    position_regex = SchoolSearchBase.get_admins_pos_regex()
    is_school_admin = True
    roles = [role_school_admin]

    @classmethod
    def role_groups(cls, schools):  # type: (List[str]) -> List[str]
        return [cls.get_search_base(school).admins_group for school in schools]


class GroupAndShareValidator(SchoolValidator):
    attributes = [
        "name",
        "ucsschoolRole",
    ]

    @staticmethod
    def _extract_ou(dn: str) -> Optional[str]:
        """
        Groups and shares do not have the property school,
        so it is extracted of the dn.
        """
        res = re.search(r"ou=([^,]+)", dn)
        if res:
            return res.group(1)

    @classmethod
    def validate(cls, obj: Dict[str, Any]) -> List[str]:
        school = GroupAndShareValidator._extract_ou(obj["dn"])
        errors = super(GroupAndShareValidator, cls).validate(obj)
        errors.append(cls.school_prefix(obj["props"]["name"], school))
        return errors

    @classmethod
    def expected_roles(cls, obj: Dict[str, Any]) -> List[str]:
        school = GroupAndShareValidator._extract_ou(obj["dn"])
        return cls.roles_at_school([school])

    @classmethod
    def school_prefix(cls, name: str, school: str) -> Optional[str]:
        """
        Groups and Shares should have a school prefix in their name, like `DEMOSCHOOL-Democlass`
        """
        if role_marketplace_share not in cls.roles:
            if school and name and not name.startswith("{}-".format(school)):
                return "has an incorrect school prefix for school {}.".format(school)


class SchoolClassValidator(GroupAndShareValidator):
    roles = [role_school_class]
    position_regex = SchoolSearchBase.get_schoolclass_pos_regex()


class WorkGroupValidator(GroupAndShareValidator):
    roles = [role_workgroup]
    position_regex = SchoolSearchBase.get_workgroup_pos_regex()


class ComputerroomValidator(GroupAndShareValidator):
    roles = [role_computer_room]
    position_regex = SchoolSearchBase.get_computerroom_pos_regex()


class WorkGroupShareValidator(GroupAndShareValidator):
    roles = [role_workgroup_share]
    position_regex = SchoolSearchBase.get_workgroup_share_pos_regex()


class ClassShareValidator(GroupAndShareValidator):
    roles = [role_school_class_share]
    position_regex = SchoolSearchBase.get_school_class_share_pos_regex()


class MarketplaceShareValidator(GroupAndShareValidator):
    roles = [role_marketplace_share]
    position_regex = SchoolSearchBase.get_workgroup_share_pos_regex()
    dn_regex = re.compile(
        r"cn=Marktplatz,cn=shares,ou=[^,]+?,{}".format(ucr["ldap/base"]),
        flags=re.IGNORECASE,
    )


def get_class(obj: Dict[str, Any]) -> Optional[Type[SchoolValidator]]:
    options = obj["options"]
    position = obj["position"]
    if options.get("ucsschoolExam", False):
        return ExamStudentValidator
    if options.get("ucsschoolTeacher", False) and options.get("ucsschoolStaff", False):
        return TeachersAndStaffValidator
    if options.get("ucsschoolStudent", False):
        return StudentValidator
    if options.get("ucsschoolTeacher", False):
        return TeacherValidator
    if options.get("ucsschoolStaff", False):
        return StaffValidator
    if options.get("ucsschoolAdministrator", False):
        return SchoolAdminValidator
    if SchoolClassValidator.position_regex.match(position):
        return SchoolClassValidator
    if WorkGroupValidator.position_regex.match(position):
        return WorkGroupValidator
    if ComputerroomValidator.position_regex.match(position):
        return ComputerroomValidator
    if ClassShareValidator.position_regex.match(position):
        return ClassShareValidator
    if MarketplaceShareValidator.dn_regex.match(obj["dn"]):
        # note: MarketplaceShares have the same position as WorkgroupShares,
        # but are unique for ous.
        return MarketplaceShareValidator
    if WorkGroupShareValidator.position_regex.match(position):
        return WorkGroupShareValidator


def validate(obj: UdmObject, logger: logging.Logger = None) -> None:
    """
    Objects are validated as dicts and errors are logged to
    the passed logger. Sensitive data is only logged to /var/log/univention/ucs-school-validation.log
    """
    dict_obj = obj_to_dict_conversion(obj)
    validation_class = get_class(dict_obj)
    if validation_class:
        options = dict_obj["options"]
        errors = validation_class.validate(dict_obj)
        errors = list(filter(None, errors))
        if errors:
            validation_uuid = str(uuid.uuid4())
            errors_str = "{} UCS@school Object {} with options {} has validation errors:\n\t- {}".format(
                validation_uuid,
                dict_obj.get("dn", ""),
                "{!r}".format(options),
                "\n\t- ".join(errors),
            )
            # ucrvs get copied from the host. In this process variables that are not
            # set on the host get set as empty strings in the container (instead of being not set).
            # Therefore I had to use this workaround of handling empty strings.
            # TODO fix workaround when 00_sync_to_docker has been improved.
            varname = "ucsschool/validation/logging/enabled"
            if ucr.is_true(varname, True) or ucr.get(varname) in (
                "",
                None,
            ):  # tests: 00_validation_log_enabled
                if logger:
                    logger.error(errors_str)
                if private_data_logger:
                    private_data_logger.error(errors_str)
                    private_data_logger.error(dict_obj)
                    stack_trace = " ".join(traceback.format_stack()[:-2]).replace("\n", " ")
                    private_data_logger.error(stack_trace)
