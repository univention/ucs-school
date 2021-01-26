import logging
import re
import traceback
import uuid

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

try:
    from typing import List
except ImportError:
    pass

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

STUDENT_CLASS_NAME = "Student"
IMPORT_STUDENT_CLASS_NAME = "ImportStudent"
EXAM_STUDENT_CLASS_NAME = "ExamStudent"
IMPORT_TEACHER_CLASS_NAME = "Teacher"
TEACHER_CLASS_NAME = "ImportTeacher"
STAFF_CLASS_NAME = "Staff"
IMPORT_STAFF_CLASS_NAME = "ImportStaff"
TEACHER_AND_STAFF_CLASS_NAME = "TeachersAndStaff"
IMPORT_TEACHER_AND_STAFF_CLASS_NAME = "ImportTeachersAndStaff"
SCHOOLCLASS_CLASS_NAME = "SchoolClass"
WORKGROUP_CLASS_NAME = "WorkGroup"
COMPUTERROOM_CLASS_NAME = "ComputerRoom"
CLASS_SHARE_CLASS_NAME = "ClassShare"
WORKGOUP_SHARE_CLASS_NAME = "WorkGroupShare"
MARKTPLATZ_SHARE_CLASS_NAME = "MarketplaceShare"

role_mapping = {
    STUDENT_CLASS_NAME: role_student,
    IMPORT_STUDENT_CLASS_NAME: role_student,
    EXAM_STUDENT_CLASS_NAME: role_exam_user,
    TEACHER_CLASS_NAME: role_teacher,
    IMPORT_TEACHER_CLASS_NAME: role_teacher,
    STAFF_CLASS_NAME: role_staff,
    IMPORT_STAFF_CLASS_NAME: role_staff,
    TEACHER_AND_STAFF_CLASS_NAME: role_teacher,
    IMPORT_TEACHER_AND_STAFF_CLASS_NAME: role_teacher,
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
klassen_position_regex = re.compile(
    r"cn=klassen,cn={},cn=groups,ou=[^,]+?,{}".format(container_students, ucr_get("ldap/base")),
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
workgroup_share_position_regex = re.compile(
    r"cn=shares,ou=[^,]+?,{}".format(ucr_get("ldap/base")), flags=re.IGNORECASE,
)
marktplatz_share_position_regex = workgroup_share_position_regex
klassen_share_position_regex = re.compile(
    r"cn=klassen,cn=shares,ou=[^,]+?,{}".format(ucr_get("ldap/base")), flags=re.IGNORECASE,
)
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


def get_role_container(class_name):  # type(str) -> str
    role_container = ""
    if class_name in (STUDENT_CLASS_NAME, IMPORT_STUDENT_CLASS_NAME):
        role_container = container_students
    elif is_teacher(class_name):
        role_container = container_teachers
    elif is_staff(class_name):
        role_container = container_staff
    elif is_teachers_and_staff(class_name):
        role_container = container_teachers_and_staff
    elif class_name == EXAM_STUDENT_CLASS_NAME:
        role_container = container_exam_students

    return role_container


def obj_to_dict(obj):
    dict_obj = dict()
    dict_obj["props"] = dict(obj.items())
    dict_obj["dn"] = obj.position.getDn()
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
    for option in obj.options:
        dict_obj["options"][option] = True
    return dict_obj


def obj_to_dict_conversion(func):
    """
    Decorator which converts an obj object to dict.
    To make testing easier, objects of type dicts are passed directly.
    """

    def _inner(obj, class_name, logger):
        if type(obj) is dict:
            dict_obj = obj
        else:
            dict_obj = obj_to_dict(obj)
        return func(dict_obj, class_name, logger)

    return _inner


def is_student(role):  # type(str) -> bool
    return role in (STUDENT_CLASS_NAME, EXAM_STUDENT_CLASS_NAME, IMPORT_STUDENT_CLASS_NAME,) or role in (
        role_student,
        role_exam_user,
    )


def is_teacher(class_name):  # type(str) -> bool
    return class_name in (TEACHER_CLASS_NAME, IMPORT_TEACHER_CLASS_NAME)


def is_teachers_and_staff(class_name):  # type(str) -> bool
    return class_name in (TEACHER_AND_STAFF_CLASS_NAME, IMPORT_TEACHER_AND_STAFF_CLASS_NAME)


def is_staff(class_name):  # type(str) -> bool
    return class_name in (STAFF_CLASS_NAME, IMPORT_STAFF_CLASS_NAME)


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
    props = obj["props"]
    schools = props["school"]
    roles = props.get("ucsschoolRole", [])

    roles = [r.split(":") for r in roles]
    ucsschool_roles = [(r, c, s) for r, c, s in roles if c == "school"]
    obligatory_roles = [True for r, c, s in ucsschool_roles if role_mapping[class_name] == r]
    if not obligatory_roles:
        errors.append("does not have {}-role.".format(role_mapping[class_name]))

    for r, c, s in ucsschool_roles:
        if role_mapping[class_name] != r:
            if (not is_student(class_name) and is_student(r)) or (
                is_student(class_name) and (not is_student(r))
            ):
                errors.append("Students must not any other roles than 'student' or 'exam_student'.")

    if class_name == EXAM_STUDENT_CLASS_NAME:
        if not [r for r, c, s in roles if c == "exam"]:
            errors.append("ExamStudents must have an ucsschoolRole with context exam.")

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
            "is missing a student role at schools: {}.".format(",".join(missing_student_role_schools))
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
    props = obj["props"]
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
            "is missing the Domain Users groups for the following schools: {}.".format(
                ",".join(missing_schools)
            )
        )
    if is_student(class_name):
        missing_classes = []
        for school in schools:
            klassen = [
                group
                for group in groups
                if group.endswith(
                    "cn=klassen,cn={},cn=groups,ou={},{}".format(
                        container_students, school, ucr_get("ldap/base")
                    )
                )
            ]
            if not klassen:
                missing_classes.append(school)
        if missing_classes:
            errors.append(
                "is missing a class for the following schools: {}.".format(",".join(missing_classes))
            )

    if class_name == TEACHER_AND_STAFF_CLASS_NAME:
        teacher_roles = [True for group in groups if re.match(teachers_group_regex, group)]
        staff_roles = [True for group in groups if re.match(staff_group_regex, group)]
        if not (teacher_roles and staff_roles):
            errors.append("is missing a Teacher or Staff group".format(TEACHER_AND_STAFF_CLASS_NAME))
    missing_role_groups = []
    role_container = get_role_container(class_name)
    for school in schools:
        if class_name == TEACHER_AND_STAFF_CLASS_NAME:
            continue
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
            "is missing the {}s groups for the following schools: {}.".format(
                class_name, ",".join(set(missing_role_groups))
            )
        )

    students = True if is_student(class_name) else False
    teachers = True if is_teacher(class_name) else False
    staff = True if is_staff(class_name) else False
    if is_teachers_and_staff(class_name):
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
        (
            class_name in (STUDENT_CLASS_NAME, IMPORT_STUDENT_CLASS_NAME)
            and not students_position_regex.match(position)
        )
        or (class_name == EXAM_STUDENT_CLASS_NAME and not exam_students_position_regex.match(position))
        or (is_teacher(class_name) and not teachers_position_regex.match(position))
        or (is_staff(class_name) and not staff_position_regex.match(position))
        or (is_teachers_and_staff(class_name) and not teachers_and_staff_position_regex.match(position))
    ):
        errors = ["has wrong position in ldap."]
    return errors


def validate_user_required_attributes(obj):  # type(dict) -> List
    """
    Validate User has values for
     "username", "ucsschoolRole",  "school", "firstname", "lastname", "groups", "primaryGroup
    """
    errors = []
    props = obj["props"]
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
        errors.append("is missing required attributes: {}.".format(",".join(missing_attributes)))
    return errors


def validate_user_options(obj, class_name):  # type(dict, str) -> List
    """
    Validate Options:
    - Students must not have ucsschoolTeacher, ucsschoolStaff or ucsschoolAdministrator
    - Objects need to have their options set, e.g. Teacher -> ucsschoolTeacher
    """
    errors = []
    options = obj["options"]
    if (
        (
            class_name in (STUDENT_CLASS_NAME, IMPORT_STUDENT_CLASS_NAME)
            and "ucsschoolStudent" not in options
        )
        or (is_teacher(class_name) and "ucsschoolTeacher" not in options)
        or (is_staff(class_name) and "ucsschoolStaff" not in options)
        or (class_name == EXAM_STUDENT_CLASS_NAME and "ucsschoolExam" not in options)
        or (
            is_teachers_and_staff(class_name)
            and not ("ucsschoolTeacher" in options and "ucsschoolStaff" not in options)
        )
        or (
            is_student(class_name)
            and any(
                key in options
                for key in ["ucsschoolTeacher", "ucsschoolStaff", "ucsschoolAdministrator",]
            )
        )
    ):
        errors.append("has incorrect options.")
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
        errors = ["has wrong position in ldap."]
    return errors


def validate_group_and_share_required_attributes(obj, class_name):  # type(dict, str)
    """
    Validate Group or Share has values for
     "name", "ucsschoolRole"
    """
    errors = []
    props = obj["props"]
    required_attr = [
        "name",
        "ucsschoolRole",
    ]
    missing_attributes = [attr for attr in required_attr if not props.get(attr, "")]
    if missing_attributes:
        errors.append("is missing required attributes: {}.".format(",".join(missing_attributes)))
    return errors


def validate_obligatory_roles(obj, class_name):  # type(dict, str)
    """
    Each object with class should have a corresponding role.
    E.g. a SchoolClass should have at least one school_class
    """
    errors = []
    props = obj["props"]
    ucsschool_roles = props.get("ucsschoolRole", [])
    ucsschool_roles = [r.split(":") for r in ucsschool_roles]
    obligatory_roles = [
        True for r, c, s in ucsschool_roles if c == "school" and role_mapping[class_name] == r
    ]
    if not obligatory_roles:
        errors.append("does not have {}-role.".format(role_mapping[class_name]))
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
        errors = ["has wrong position in ldap."]
    return errors


def validate_school_prefix(obj, class_name):  # type(dict, str) -> List
    """
    Validate school-prefix by extracting the ou-name from the dn.
    """
    errors = []
    dn = obj["dn"]
    props = obj["props"]
    school = re.search(r"ou=([^,]+)", dn)
    name = props.get("name", "")
    if school and name:
        expect_school = school.group(1)
        parts = name.split("-")
        if parts[0] != expect_school:
            errors = ["has an incorrect school prefix for school {}.".format(expect_school)]
    return errors


@obj_to_dict_conversion
def validate(obj, class_name, logger=None):
    """
    Objects are validated as dicts and errors are logged to
    the passed logger. Sensitive data is logged to /var/log/univention/ucs-school-validation.log
    """
    errors = []
    if class_name in [
        STUDENT_CLASS_NAME,
        IMPORT_STUDENT_CLASS_NAME,
        TEACHER_CLASS_NAME,
        IMPORT_TEACHER_CLASS_NAME,
        EXAM_STUDENT_CLASS_NAME,
        TEACHER_CLASS_NAME,
        IMPORT_TEACHER_CLASS_NAME,
        STAFF_CLASS_NAME,
        IMPORT_STAFF_CLASS_NAME,
        TEACHER_AND_STAFF_CLASS_NAME,
        IMPORT_TEACHER_AND_STAFF_CLASS_NAME,
    ]:
        errors.extend(validate_user_required_attributes(obj))
        errors.extend(validate_user_options(obj, class_name))
        errors.extend(validate_user_position(obj, class_name))
        errors.extend(validate_user_roles(obj.copy(), class_name))
        errors.extend(validate_user_groups(obj, class_name))
    elif class_name in [SCHOOLCLASS_CLASS_NAME, WORKGROUP_CLASS_NAME, COMPUTERROOM_CLASS_NAME]:
        errors.extend(validate_group_and_share_required_attributes(obj, class_name))
        errors.extend(validate_group_position(obj, class_name))
        errors.extend(validate_obligatory_roles(obj, class_name))
        errors.extend(validate_school_prefix(obj, class_name))
    elif class_name in [CLASS_SHARE_CLASS_NAME, WORKGOUP_SHARE_CLASS_NAME, MARKTPLATZ_SHARE_CLASS_NAME]:
        errors.extend(validate_group_and_share_required_attributes(obj, class_name))
        errors.extend(validate_share_position(obj, class_name))
        errors.extend(validate_obligatory_roles(obj, class_name))
        errors.extend(validate_school_prefix(obj, class_name))

    if errors:
        user_uuid = str(uuid.uuid4())
        errors_str = "UCS@school Object {} with class {} and UUID {} has validation errors:\n\n\t- {}\n".format(
            obj.get("dn", ""), class_name, user_uuid, "\n\t- ".join(errors)
        )
        if logger:
            logger.error(errors_str)
            logger.error("Grep for {} in {} for more information.".format(user_uuid, LOG_FILE))
        private_data_logger.error(errors_str)
        private_data_logger.error("{}".format(obj))
        private_data_logger.error("{}".format("\n".join(traceback.format_stack())))
