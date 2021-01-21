import logging
import re
import traceback
import uuid

try:
    from functools import lru_cache
    from typing import List
except ImportError:
    from backports.functools_lru_cache import lru_cache

from ucsschool.lib.models.group import ComputerRoom, SchoolClass, WorkGroup
from ucsschool.lib.models.share import ClassShare, MarketplaceShare, WorkGroupShare
from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff
from ucsschool.lib.models.utils import get_file_handler, get_stream_handler, ucr
from ucsschool.lib.roles import (
    role_computer_room,
    role_exam_user,
    role_marketplace_share,
    role_school_class,
    role_school_class_share,
    role_staff,
    role_student,
    role_teacher,
    role_workgroup,
    role_workgroup_share,
)

STUDENT_CLASS_NAME = Student.__name__
EXAM_STUDENT_CLASS_NAME = ExamStudent.__name__
TEACHER_CLASS_NAME = Teacher.__name__
STAFF_CLASS_NAME = Staff.__name__
TEACHER_AND_STAFF_CLASS_NAME = TeachersAndStaff.__name__
SCHOOLCLASS_CLASS_NAME = SchoolClass.__name__
WORKGROUP_CLASS_NAME = WorkGroup.__name__
COMPUTERROOM_CLASS_NAME = ComputerRoom.__name__
CLASS_SHARE_CLASS_NAME = ClassShare.__name__
WORKGOUP_SHARE_CLASS_NAME = WorkGroupShare.__name__
MARKTPLATZ_SHARE_CLASS_NAME = MarketplaceShare.__name__

role_mapping = {
    STUDENT_CLASS_NAME: role_student,
    EXAM_STUDENT_CLASS_NAME: role_exam_user,
    TEACHER_CLASS_NAME: role_teacher,
    STAFF_CLASS_NAME: role_staff,
    TEACHER_AND_STAFF_CLASS_NAME: role_teacher,
    SCHOOLCLASS_CLASS_NAME: role_school_class,
    WORKGROUP_CLASS_NAME: role_workgroup,
    COMPUTERROOM_CLASS_NAME: role_computer_room,
    CLASS_SHARE_CLASS_NAME: role_school_class_share,
    WORKGOUP_SHARE_CLASS_NAME: role_workgroup_share,
    MARKTPLATZ_SHARE_CLASS_NAME: role_marketplace_share,
}


LOG_FILE = "/var/log/univention/ucs-school-validation.log"
LOGGER_NAME = "UCSSchool-Validation"
private_data_logger = logging.getLogger(LOGGER_NAME)
private_data_logger.setLevel("DEBUG")
private_data_logger.addHandler(get_file_handler("DEBUG", LOG_FILE, uid=0, gid=0, backupCount=1000))


@lru_cache(maxsize=32)
def ucr_get(value, default=""):  # type(str) -> str
    return ucr.get(value, default)


container_teachers = ucr_get("ucsschool/ldap/default/containers/teachers", "lehrer")
container_staff = ucr_get("ucsschool/ldap/default/containers/staff", "mitarbeiter")
container_teachers_and_staff = ucr_get(
    "ucsschool/ldap/default/containers/teachers-and-staff", "lehrer und mitarbeiter"
)
container_students = ucr_get("ucsschool/ldap/default/containers/pupils", "schueler")
container_exam_students = ucr_get("ucsschool/ldap/default/container/exam", "examusers")
container_computerrooms = ucr_get("ucsschool/ldap/default/container/rooms", "raeume")
exam_students_group = ucr_get("ucsschool/ldap/default/groupname/exam", "OU%(ou)s-Klassenarbeit")

teachers_group_regex = re.compile(
    r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(container_teachers, ucr_get("ldap/base")),
    flags=re.IGNORECASE,
)
staff_group_regex = re.compile(
    r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(container_staff, ucr_get("ldap/base")),
    flags=re.IGNORECASE,
)
students_group_regex = re.compile(
    r"cn={}-(?P<ou>[^,]+?),cn=groups,ou=(?P=ou),{}".format(container_students, ucr_get("ldap/base")),
    flags=re.IGNORECASE,
)
# Group regexes
klassen_position_regex = re.compile(
    r"cn=klassen,cn=groups,ou=[^,]+?,{}".format(container_students, ucr_get("ldap/base")),
    flags=re.IGNORECASE,
)
workgroup_position_regex = re.compile(
    r"cn={},cn=groups,ou=[^,]+?,{}".format(container_students, ucr_get("ldap/base")),
    flags=re.IGNORECASE,
)
computerroom_position_regex = re.compile(
    r"cn={},cn=groups,ou=[^,]+?,{}".format(container_computerrooms, ucr_get("ldap/base")),
    flags=re.IGNORECASE,
)
# Share regexes
workgroup_share_position_regex = re.compile(
    r"cn=shares,ou=[^,]+?,{}".format(ucr_get("ldap/base")), flags=re.IGNORECASE,
)
marktplatz_share_position_regex = workgroup_share_position_regex
klassen_share_position_regex = re.compile(
    r"cn=klassen,cn=shares,ou=[^,]+?,{}".format(ucr_get("ldap/base")), flags=re.IGNORECASE,
)
# User regexes
teachers_position_regex = re.compile(
    r"cn={},cn=users,ou=[^,]+,{}".format(container_teachers, ucr_get("ldap/base")), flags=re.IGNORECASE,
)
staff_position_regex = re.compile(
    r"cn={},cn=users,ou=[^,]+,{}".format(container_staff, ucr_get("ldap/base")), flags=re.IGNORECASE,
)
teachers_and_staff_position_regex = re.compile(
    r"cn={},cn=users,ou=[^,]+,{}".format(container_teachers_and_staff, ucr_get("ldap/base")),
    flags=re.IGNORECASE,
)

students_position_regex = re.compile(
    r"cn={},cn=users,ou=[^,]+,{}".format(container_students, ucr_get("ldap/base")), flags=re.IGNORECASE,
)
exam_students_position_regex = re.compile(
    r"cn={},ou=[^,]+,{}".format(container_exam_students, ucr_get("ldap/base")), flags=re.IGNORECASE,
)


def get_role_container(expected_role):  # type(str) -> str
    role_container = ""
    if expected_role == STUDENT_CLASS_NAME:
        role_container = container_students
    elif expected_role == TEACHER_CLASS_NAME:
        role_container = container_teachers
    elif expected_role == STAFF_CLASS_NAME:
        role_container = container_staff
    elif expected_role == TEACHER_AND_STAFF_CLASS_NAME:
        role_container = container_teachers_and_staff
    elif expected_role == EXAM_STUDENT_CLASS_NAME:
        role_container = container_exam_students

    return role_container


def obj_to_dict(udm_obj):
    dict_obj = dict()
    dict_obj["properties"] = dict(udm_obj.items())
    dict_obj["dn"] = udm_obj.position.getDn()
    dict_obj["position"] = re.search(r"[^=]+=[^,]+,(.+)", dict_obj["dn"]).group(1)
    keys = [
        "ucsschoolAdministrator",
        "ucsschoolExam",
        "ucsschoolTeacher",
        "ucsschoolStudent",
        "ucsschoolStaff",
        "ucsschoolAdministratorGroup",
        "ucsschoolImportGroup",
    ]
    values = len(keys) * [False]
    dict_obj["options"] = dict(zip(keys, values))
    for option in udm_obj.options:
        dict_obj["options"][option] = True
    return dict_obj


def obj_to_dict_conversion(func):
    """
    Decorator which converts an udm object to dict.
    To make testing easier, objects of type dicts are passed directly.
    """

    def _inner(udm_obj, class_name, logger):
        if type(udm_obj) is dict:
            dict_obj = udm_obj
        else:
            dict_obj = obj_to_dict(udm_obj)
        return func(dict_obj, class_name, logger)

    return _inner


def is_student(role):  # type(str) -> bool
    return role in (STUDENT_CLASS_NAME, EXAM_STUDENT_CLASS_NAME,) or role in (
        role_student,
        role_exam_user,
    )


def validate_group_membership(
    group_dn, students=False, teachers=False, staff=False
):  # type(str, bool, bool, bool)
    """
    Check if user is allowed in group with group_dn.
    E.g. a Teacher should not be part of any students groups.
    """
    errors = []
    if (
        (students_group_regex.match(group_dn) and not students)
        or (teachers_group_regex.match(group_dn) and not teachers)
        or (staff_group_regex.match(group_dn) and not staff)
    ):
        errors = ["Disallowed member of group {}".format(group_dn)]
    return errors


def validate_user_roles(obj, class_name):  # type(dict, str)
    """
    check if user has the correct roles.
    - Students should only have student or exam_student.
    - Students must not have any roles of 'teacher', 'staff', 'school_admin'.
    - Other roles must also not have the students role.
    - A student must contain at least one student role.
    - An exam-student must have a r with context 'exam'.
    - User is with r x is not part of schools x,y.
    """
    errors = []
    props = obj["properties"]
    ucsschool_roles = props.get("ucsschoolRole", [])
    ucsschool_roles = [r.split(":") for r in ucsschool_roles]
    ucsschool_roles = [(r, c, s) for r, c, s in ucsschool_roles if c == "school"]
    obligatory_roles = [True for r, c, s in ucsschool_roles if role_mapping[class_name] == r]
    if not obligatory_roles:
        errors.append("{} does not have {}-role.".format(class_name, role_mapping[class_name]))

    schools = props["school"]
    for r, c, s in ucsschool_roles:
        if role_mapping[class_name] != r:
            if (not is_student(class_name) and is_student(r)) or (
                is_student(class_name) and (not is_student(r))
            ):
                errors.append("Students must not any other roles than 'student' or 'exam_student'.")

    if class_name == EXAM_STUDENT_CLASS_NAME:
        if not [r for r, c, s in ucsschool_roles if c == "exam"]:
            errors.append("Exam-Students must have an ucsschoolRole with context exam.")

    missing_schools = []
    missing_student_role_schools = []
    for school in schools:
        missing_schools.extend([s for r, c, s in ucsschool_roles if s not in schools])
        if is_student(class_name) and not [
            r for r, c, s in ucsschool_roles if s == school and r == role_student
        ]:
            missing_student_role_schools.append(school)

    if missing_schools:
        errors.append("{} is not part of schools: {}.".format(class_name, ",".join(schools)))
    if missing_student_role_schools:
        errors.append(
            "Student is missing a student role at schools: {}.".format(
                ",".join(missing_student_role_schools)
            )
        )
    return errors


def validate_user_groups(obj, class_name):  # type(dict, str) -> List
    """
    For all schools check if
    - User is part of the Domain Users OU group.
    - Students have at least one class at all schools they are part of.
    - TeachersAndStaff have both teacher and staff.
    - ExamStudents have a special container.
    - Validate group membership, e.g. students should not be part of teacher-group, see validate_group_membership.
    """
    errors = []
    props = obj["properties"]
    schools = props.get("school", [])
    groups = props.get("groups", [])
    missing_schools = []
    for school in schools:
        if not [
            group
            for group in groups
            if group == "cn=Domain Users {0},cn=groups,ou={0},{1}".format(school, ucr_get("ldap/base"))
        ]:
            missing_schools.append(school)
    if missing_schools:
        errors.append(
            "User is missing the Domain Users groups for the following schools: {}.".format(
                ",".join(missing_schools)
            )
        )
    if is_student(class_name):
        missing_classes = []
        for school in schools:
            klassen = [group for group in groups if re.search(klassen_position_regex, group)]
            if not klassen:
                missing_classes.append(school)
        if missing_classes:
            errors.append(
                "User is missing a class for the following schools: {}.".format(
                    ",".join(missing_classes)
                )
            )

    if class_name == TEACHER_AND_STAFF_CLASS_NAME:
        teacher_roles = [True for group in groups if re.match(teachers_group_regex, group)]
        staff_roles = [True for group in groups if re.match(staff_group_regex, group)]
        if not (teacher_roles and staff_roles):
            errors.append("{} is missing a teacher- or staff-group".format(class_name))
    missing_role_groups = []
    role_container = get_role_container(class_name)
    for school in schools:
        if class_name == EXAM_STUDENT_CLASS_NAME:
            _exam_students_group = exam_students_group % {"ou": school.lower()}
            role_groups = [
                True
                for group in groups
                if re.match(
                    r".+?cn={},cn=ucsschool,cn=groups,{}".format(
                        _exam_students_group, ucr_get("ldap/base")
                    ),
                    group,
                    flags=re.IGNORECASE,
                )
            ]
            if not role_groups:
                missing_role_groups.append(school)
            # exam-student is also in students group
            role_container = container_students

        role_groups = [
            True
            for group in groups
            if group
            == "cn={}-{},cn=groups,ou={},{}".format(
                role_container, school.lower(), school, ucr_get("ldap/base")
            )
        ]
        if not role_groups:
            missing_role_groups.append(school)

    if missing_role_groups:
        errors.append(
            "User is missing the {}s groups for the following schools: {}.".format(
                class_name, ",".join(missing_role_groups)
            )
        )

    students = True if class_name == STUDENT_CLASS_NAME else False
    teachers = True if class_name == TEACHER_CLASS_NAME else False
    staff = True if class_name == STAFF_CLASS_NAME else False
    if class_name == TEACHER_AND_STAFF_CLASS_NAME:
        teachers = True
        staff = True
    for group in groups:
        errors.extend(validate_group_membership(group, students, teachers, staff))
    return errors


def validate_user_position(obj, class_name):  # type(dict, str) -> List
    """
    Validate user position given a user with class_name, i.e. Student, ExamStudent, Teacher, Staff
    and TeacherAndStaff to match a regex defined in *_position_regex.
    """
    position = obj["position"]
    errors = []
    if (
        (class_name == STUDENT_CLASS_NAME and not students_position_regex.match(position))
        or (class_name == EXAM_STUDENT_CLASS_NAME and not exam_students_position_regex.match(position))
        or (class_name == TEACHER_CLASS_NAME and not teachers_position_regex.match(position))
        or (class_name == STAFF_CLASS_NAME and not staff_position_regex.match(position))
        or (
            class_name == TEACHER_AND_STAFF_CLASS_NAME
            and not teachers_and_staff_position_regex.match(position)
        )
    ):
        errors = ["{} has wrong position in ldap.".format(class_name)]
    return errors


def validate_user_required_attributes(obj):  # type(dict) -> List
    """
    Validate User has values for
     "username", "ucsschoolRole",  "school", "firstname", "lastname", "groups", "primaryGroup
    """
    errors = []
    props = obj["properties"]
    required_attr = [
        "username",
        "ucsschoolRole",
        "school",
        "firstname",
        "lastname",
        "groups",
        "primaryGroup",
    ]
    missing_attributes = [attr for attr in required_attr if not props.get(attr, "")]
    if missing_attributes:
        errors.append("User is missing required attributes: {}.".format(",".join(missing_attributes)))
    return errors


def validate_user_udm_options(obj, class_name):  # type(dict, str) -> List
    """
    Validate UDM Options:
    - Students must not have ucsschoolTeacher, ucsschoolStaff or ucsschoolAdministrator
    - Objects need to have their options set, e.g. Teacher -> ucsschoolTeacher
    """
    errors = []
    if (
        (
            class_name == STUDENT_CLASS_NAME
            and not obj["options"]["ucsschoolStudent"]
            or any(
                obj["options"][key]
                for key in ["ucsschoolTeacher", "ucsschoolStaff", "ucsschoolAdministrator",]
            )
        )
        or (class_name == TEACHER_CLASS_NAME and not obj["options"]["ucsschoolTeacher"])
        or (class_name == STAFF_CLASS_NAME and not obj["options"]["ucsschoolStaff"])
        or (class_name == EXAM_STUDENT_CLASS_NAME and not obj["options"]["ucsschoolExam"])
    ):
        errors.append("{} has incorrect UDM options.".format(class_name))
    return errors


def validate_group_position(obj, class_name):  # type(dict, str) -> List
    """
    Validate user position given a group with class_name, i.e. ComputerRoom, SchoolClass or WorkGroup
    to match a regex defined in *_position_regex.
    """
    dn = obj["position"]
    errors = []
    if (
        (class_name == SCHOOLCLASS_CLASS_NAME and not re.match(klassen_position_regex, dn))
        or (class_name == WORKGROUP_CLASS_NAME and not re.match(workgroup_position_regex, dn))
        or (class_name == COMPUTERROOM_CLASS_NAME and not re.match(computerroom_position_regex, dn))
    ):
        errors = ["{} has wrong position in ldap.".format(class_name)]
    return errors


def validate_group_and_share_required_attributes(obj, class_name):  # type(dict, str)
    """
    todo that is the absolute minimum for both.
    -> check tonis article.
    Validate Group or Share has values for
     "name", "ucsschoolRole"
    """
    errors = []
    props = obj["properties"]
    required_attr = [
        "name",
        "ucsschoolRole",
    ]
    missing_attributes = [attr for attr in required_attr if not props.get(attr, "")]
    if missing_attributes:
        errors.append(
            "{} is missing required attributes: {}.".format(class_name, ",".join(missing_attributes))
        )
    return errors


def validate_obligatory_roles(obj, class_name):  # type(dict, str)
    """
    Each object with class should have a corresponding role.
    E.g. a SchoolClass should have at least one school_class
    """
    errors = []
    props = obj["properties"]
    ucsschool_roles = props.get("ucsschoolRole", [])
    ucsschool_roles = [r.split(":") for r in ucsschool_roles]
    obligatory_roles = [
        True for r, c, s in ucsschool_roles if c == "school" and role_mapping[class_name] == r
    ]
    if not obligatory_roles:
        errors.append("{} does not have {}-role.".format(class_name, role_mapping[class_name]))
    return errors


def validate_share_position(obj, class_name):  # type(dict, str) -> List
    """
    Validate user position given a group with class_name, i.e. WorkGroupShare, ClassShare or MarketplaceShare
    to match a regex defined in *_position_regex.
    """
    dn = obj["position"]
    errors = []
    if (
        (class_name == CLASS_SHARE_CLASS_NAME and not re.match(klassen_share_position_regex, dn))
        or (class_name == WORKGOUP_SHARE_CLASS_NAME and not re.match(workgroup_share_position_regex, dn))
        or (
            class_name == MARKTPLATZ_SHARE_CLASS_NAME
            and not re.match(marktplatz_share_position_regex, dn)
        )
    ):
        errors = ["{} has wrong position in ldap.".format(class_name)]
    return errors


def validate_school_prefix(obj, class_name):  # type(dict, str) -> List
    """
    Validate school-prefix by extracting the ou-name from the dn.
    """
    errors = []
    dn = obj["dn"]
    props = obj["properties"]
    school = re.search(r"ou=([^,]+)", dn)
    name = props.get("name", [])
    if school and name:
        expect_school = school.group(1)
        parts = name[0].split("-")
        if len(parts) != 2 or parts[0] != expect_school:
            errors = [
                "{} has an incorrect school prefix for school {}.".format(class_name, expect_school)
            ]
    return errors


@obj_to_dict_conversion
def validate_udm(obj, class_name, logger=None):
    """
    UDM objects are validated as dicts and errors are logged to
    the passed logger. Sensitive data is logged to /var/log/univention/ucs-school-validation.log
    """
    errors = []
    # todo -> enum
    if class_name in [
        STUDENT_CLASS_NAME,
        TEACHER_CLASS_NAME,
        EXAM_STUDENT_CLASS_NAME,
        TEACHER_CLASS_NAME,
        STAFF_CLASS_NAME,
        TEACHER_AND_STAFF_CLASS_NAME,
    ]:
        errors.extend(validate_user_udm_options(obj, class_name))
        errors.extend(validate_user_position(obj, class_name))
        errors.extend(validate_user_required_attributes(obj))
        errors.extend(validate_user_roles(obj, class_name))
        errors.extend(validate_user_groups(obj, class_name))
    elif class_name in [SCHOOLCLASS_CLASS_NAME, WORKGROUP_CLASS_NAME, COMPUTERROOM_CLASS_NAME]:
        errors.extend(validate_group_position(obj, class_name))
        errors.extend(validate_group_and_share_required_attributes(obj, class_name))
        errors.extend(validate_obligatory_roles(obj, class_name))
        errors.extend(validate_school_prefix(obj, class_name))
    elif class_name in [CLASS_SHARE_CLASS_NAME, WORKGOUP_SHARE_CLASS_NAME, MARKTPLATZ_SHARE_CLASS_NAME]:
        errors.extend(validate_share_position(obj, class_name))
        errors.extend(validate_group_and_share_required_attributes(obj, class_name))
        errors.extend(validate_obligatory_roles(obj, class_name))
        errors.extend(validate_school_prefix(obj, class_name))

    if errors:
        user_uuid = str(uuid.uuid4())
        if logger:
            logger.error(
                "UCS@school Object {} has validation errors:\n\t- {}\n".format(
                    obj.get("dn", ""), "\n\t- ".join(errors)
                )
            )
            logger.error("Grep for {} in {} for more information.".format(user_uuid, LOG_FILE))
        private_data_logger.error(
            "UCS@school Object with UUID {} has validation errors:\n\t- {}".format(
                user_uuid, "\n\t- ".join(errors)
            )
        )
        private_data_logger.error("{}".format(obj))
        private_data_logger.error("{}".format("\n".join(traceback.format_stack())))
