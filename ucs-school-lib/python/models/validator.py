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

SCHOOLCLASS_CLASS_NAME = "SchoolClass"
WORKGROUP_CLASS_NAME = "WorkGroup"
COMPUTERROOM_CLASS_NAME = "ComputerRoom"
CLASS_SHARE_CLASS_NAME = "ClassShare"
WORKGOUP_SHARE_CLASS_NAME = "WorkGroupShare"
MARKTPLATZ_SHARE_CLASS_NAME = "MarketplaceShare"

group_and_share_role_mapping = {
    SCHOOLCLASS_CLASS_NAME: role_school_class,
    WORKGROUP_CLASS_NAME: role_workgroup,
    COMPUTERROOM_CLASS_NAME: role_computer_room,
    CLASS_SHARE_CLASS_NAME: role_school_class_share,
    WORKGOUP_SHARE_CLASS_NAME: role_workgroup_share,
    MARKTPLATZ_SHARE_CLASS_NAME: role_marketplace_share,
}


def user_role_mapping(options):
    if is_teacher(options):
        return role_teacher
    elif is_staff(options):
        return role_staff
    elif is_exam_student(options):
        return role_exam_user
    elif is_student(options):
        return role_student


LOG_FILE = "/var/log/univention/ucs-school-validation.log"
LOGGER_NAME = "UCSSchool-Validation"
private_data_logger = logging.getLogger(LOGGER_NAME)
private_data_logger.setLevel("DEBUG")
private_data_logger.addHandler(get_file_handler("DEBUG", LOG_FILE, uid=0, gid=0, backupCount=1000))


class SecretFilter(logging.Filter):
    def filter(self, record):
        return record.name != LOGGER_NAME


for handler in logging.root.handlers:
    handler.addFilter(SecretFilter())


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
marktplatz_share_position_regex = re.compile(
    r"cn=Marktplatz,cn=shares,ou=[^,]+?,{}".format(ucr_get("ldap/base")), flags=re.IGNORECASE,
)
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


def get_role_container(options):  # type(List) -> str
    if is_exam_student(options):
        return container_exam_students
    elif is_student(options):
        return container_students
    elif is_teachers_and_staff(options):
        return container_teachers_and_staff
    elif is_teacher(options):
        return container_teachers
    elif is_staff(options):
        return container_staff
    else:
        return ""


def get_pseudo_class_name(obj):  # type(dict, str) -> Optional[str]
    """
    Groups & shares don't have udm options.
    We need to calculate them by their ldap-position. Since the class
    could be derived, the actual class name can be different, like CustomSchoolClass.
    """
    position = obj["position"]
    if re.match(klassen_position_regex, position):
        return SCHOOLCLASS_CLASS_NAME
    elif re.match(workgroup_position_regex, position):
        return WORKGROUP_CLASS_NAME
    elif re.match(computerroom_position_regex, position):
        return COMPUTERROOM_CLASS_NAME
    elif re.match(klassen_share_position_regex, position):
        return CLASS_SHARE_CLASS_NAME
    elif re.match(marktplatz_share_position_regex, obj["dn"]):
        return MARKTPLATZ_SHARE_CLASS_NAME
    elif re.match(workgroup_share_position_regex, position):
        return WORKGOUP_SHARE_CLASS_NAME


def obj_to_dict(obj):
    dict_obj = dict()
    dict_obj["props"] = dict(obj.items())
    dict_obj["dn"] = obj.position.getDn()
    dict_obj["position"] = re.search(r"[^=]+=[^,]+,(.+)", dict_obj["dn"]).group(1)
    dict_obj["options"] = obj.options
    return dict_obj


def obj_to_dict_conversion(func):
    """
    Decorator which converts an obj object to dict.
    To make testing easier, objects of type dicts are passed directly.
    """

    def _inner(obj, logger):
        if type(obj) is dict:
            dict_obj = obj
        else:
            dict_obj = obj_to_dict(obj)
        return func(dict_obj, logger)

    return _inner


def is_student_role(role):  # type(str) -> bool
    return role in (role_student, role_exam_user,)


def is_student(options):  # type(List) -> bool
    return "ucsschoolStudent" in options


def is_teacher(options):  # type(List) -> bool
    return "ucsschoolTeacher" in options


def is_teachers_and_staff(options):  # type(List) -> bool
    return is_teacher(options) and is_staff(options)


def is_staff(options):  # type(List) -> bool
    return "ucsschoolStaff" in options


def is_exam_student(options):  # type(List) -> bool
    return "ucsschoolExam" in options


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


def validate_user_roles(obj):  # type(dict)
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
    options = obj["options"]

    roles = [r.split(":") for r in roles]
    ucsschool_roles = [(r, c, s) for r, c, s in roles if c == "school"]
    expected_role_name = user_role_mapping(options)
    obligatory_roles = [True for r, c, s in ucsschool_roles if expected_role_name == r]

    if not obligatory_roles:
        errors.append("does not have {}-role.".format(expected_role_name))

    for r, c, s in ucsschool_roles:
        if expected_role_name != r:
            if (not is_student_role(expected_role_name) and is_student_role(r)) or (
                is_student_role(expected_role_name) and (not is_student_role(r))
            ):
                errors.append("Students must not any other roles than 'student' or 'exam_student'.")

    if is_exam_student(options):
        if not [r for r, c, s in roles if c == "exam"]:
            errors.append("ExamStudents must have an ucsschoolRole with context exam.")

    missing_schools = []
    missing_student_role_schools = []
    for school in schools:
        missing_schools.extend([s for r, c, s in ucsschool_roles if s not in schools])
        if is_student(options) and not [
            r for r, c, s in ucsschool_roles if s == school and r == role_student
        ]:
            missing_student_role_schools.append(school)

    if missing_schools:
        errors.append("is not part of schools: {}.".format(",".join(schools)))
    if missing_student_role_schools:
        errors.append(
            "is missing a student role at schools: {}.".format(",".join(missing_student_role_schools))
        )
    return errors


def validate_user_groups(obj):  # type(dict) -> List
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
    options = obj["options"]

    missing_schools = []
    for school in schools:
        expected_group_dn = "cn=Domain Users {0},cn=groups,ou={0},{1}".format(
            school, ucr_get("ldap/base")
        )
        if expected_group_dn not in groups:
            missing_schools.append(school)
    if missing_schools:
        errors.append(
            "is missing the Domain Users groups for the following schools: {}.".format(
                ",".join(missing_schools)
            )
        )
    if is_student(options):
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

    if is_teachers_and_staff(options):
        teacher_groups = [True for group in groups if re.match(teachers_group_regex, group)]
        staff_groups = [True for group in groups if re.match(staff_group_regex, group)]
        if not (teacher_groups and staff_groups):
            errors.append("is missing a Teacher or Staff group")
    missing_role_groups = []
    role_container = get_role_container(options)
    for school in schools:
        if is_teachers_and_staff(options):
            continue
        if is_exam_student(options):
            _exam_students_group = exam_students_group % {"ou": school.lower()}
            role_groups = [
                True
                for group in groups
                if re.match(
                    r"cn={},cn=ucsschool,cn=groups,{}".format(
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

        expected_group_dn = "cn={}-{},cn=groups,ou={},{}".format(
            role_container, school.lower(), school, ucr_get("ldap/base")
        )
        if expected_group_dn not in groups:
            missing_role_groups.append(school)

    if missing_role_groups:
        errors.append(
            "is missing groups for the following schools: {}.".format(",".join(set(missing_role_groups)))
        )

    for group in groups:
        errors.extend(
            validate_group_membership(
                group,
                students=is_student(options),
                teachers=is_teacher(options),
                staff=is_staff(options),
            )
        )
    return errors


def validate_user_position(obj):  # type(dict, str) -> List
    """
    Validate user position given a user with class_name, i.e. Student, ExamStudent, Teacher, Staff
    and TeacherAndStaff to match a regex defined in *_position_regex.
    """
    position = obj["position"]
    options = obj["options"]
    errors = []
    teachers_and_staff = is_teachers_and_staff(options)
    exam_user = is_exam_student(options)
    if (
        (is_student(options) and not exam_user and not students_position_regex.match(position))
        or (exam_user and not exam_students_position_regex.match(position))
        or (
            is_teacher(options)
            and not teachers_and_staff
            and not teachers_position_regex.match(position)
        )
        or (is_staff(options) and not teachers_and_staff and not staff_position_regex.match(position))
        or (teachers_and_staff and not teachers_and_staff_position_regex.match(position))
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


def validate_group_and_share_required_attributes(obj):  # type(dict)
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
        True
        for r, c, s in ucsschool_roles
        if c == "school" and group_and_share_role_mapping[class_name] == r
    ]
    if not obligatory_roles:
        errors.append("does not have {}-role.".format(group_and_share_role_mapping[class_name]))
    return errors


def validate_school_prefix(obj):  # type(dict) -> List
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
def validate(obj, logger=None):
    """
    Objects are validated as dicts and errors are logged to
    the passed logger. Sensitive data is logged to /var/log/univention/ucs-school-validation.log
    """
    errors = []
    options = obj["options"]
    object_type = obj.get("objectType", "")
    class_name = ""
    if object_type in ["groups/group", "shares/share"]:
        class_name = get_pseudo_class_name(obj)
    if any([is_student(options), is_teacher(options), is_staff(options), is_exam_student(options)]):
        errors.extend(validate_user_required_attributes(obj))
        errors.extend(validate_user_position(obj))
        errors.extend(validate_user_roles(obj))
        errors.extend(validate_user_groups(obj))
    elif class_name in [SCHOOLCLASS_CLASS_NAME, WORKGROUP_CLASS_NAME, COMPUTERROOM_CLASS_NAME]:
        class_name = get_pseudo_class_name(obj)
        errors.extend(validate_group_and_share_required_attributes(obj))
        errors.extend(validate_obligatory_roles(obj, class_name))
        errors.extend(validate_school_prefix(obj))
    elif class_name in [CLASS_SHARE_CLASS_NAME, WORKGOUP_SHARE_CLASS_NAME, MARKTPLATZ_SHARE_CLASS_NAME]:
        errors.extend(validate_group_and_share_required_attributes(obj))
        errors.extend(validate_obligatory_roles(obj, class_name))
        errors.extend(validate_school_prefix(obj))

    if errors:
        user_uuid = str(uuid.uuid4())
        errors_str = "UCS@school Object {} with options {} has validation errors:\n\n\t- {}\n".format(
            obj.get("dn", ""), "{}".format(",".join(options)), "\n\t- ".join(errors)
        )
        if logger:
            logger.error(errors_str)
            logger.error("Grep for {} in {} for more information.".format(user_uuid, LOG_FILE))
        private_data_logger.error("{}".format(errors_str))
        private_data_logger.error("{}".format(obj))
        private_data_logger.error("{}".format("\n".join(traceback.format_stack())))
