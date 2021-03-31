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

import itertools
import random
from typing import List, NamedTuple, Tuple, Type, Union

import pytest

from ucsschool.importer.models.import_user import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
    ImportUser,
    ImportUserTypeConverter,
    convert_to_staff,
    convert_to_student,
    convert_to_teacher,
    convert_to_teacher_and_staff,
)
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff
from udm_rest_client import UDM

UserType = Union[
    Type[ImportStaff],
    Type[ImportStudent],
    Type[ImportTeacher],
    Type[ImportTeachersAndStaff],
    Type[ImportUser],
]
Role = NamedTuple("Role", [("name", str), ("klass", UserType)])


def _inside_docker():
    try:
        import ucsschool.kelvin.constants
    except ImportError:
        return False
    return ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists()


pytestmark = pytest.mark.skipif(
    not _inside_docker(),
    reason="Must run inside Docker container started by appcenter.",
)
USER_ROLES: List[Role] = [
    Role("staff", ImportStaff),
    Role("student", ImportStudent),
    Role("teacher", ImportTeacher),
    Role("teacher_and_staff", ImportTeachersAndStaff),
]
random.shuffle(USER_ROLES)


def two_roles_id(value: List[Role]) -> str:
    return f"{value[0].name} -> {value[1].name}"


@pytest.mark.asyncio
@pytest.mark.parametrize("roles", itertools.product(USER_ROLES, USER_ROLES), ids=two_roles_id)
async def test_modify_role(
    ldap_base,
    new_school_class,
    new_user,
    udm_kwargs,
    roles: Tuple[Role, Role],
    schedule_delete_user_name,
    import_config,
    demoschool2,
    random_name,
):
    role_from, role_to = roles
    dn, attr = await new_user(role_from.name)
    async with UDM(**udm_kwargs) as udm:
        use_old_udm = await udm.get("users/user").get(dn)
        # add a school class also to staff users, so we can check if it is kept upon conversion to other
        # role
        cls_dn1, cls_attr1 = await new_school_class()
        cls_dn2, cls_attr2 = await new_school_class()
        demoschool2_dn, demoschool2_name = demoschool2
        role_demo2 = f"teacher:school:{demoschool2_name}"
        cls_dn3, cls_attr3 = await new_school_class(school=demoschool2_name)
        use_old_udm.props.school.append(demoschool2_name)
        role_group_prefix = {
            "staff": "mitarbeiter",
            "student": "schueler",
            "teacher": "lehrer",
            "teacher_and_staff": "mitarbeiter",
        }[role_from.name]
        demoschool2_group_cn = f"cn=groups,ou={demoschool2_name},{ldap_base}"
        use_old_udm.props.groups.extend(
            [
                cls_dn1,
                cls_dn3,
                f"cn=Domain Users {demoschool2_name},{demoschool2_group_cn}",
                f"cn={role_group_prefix}-{demoschool2_name.lower()},{demoschool2_group_cn}",
            ]
        )
        non_school_role = f"{random_name}:{random_name}:{random_name}"
        use_old_udm.props.ucsschoolRole.extend([role_demo2, non_school_role])
        await use_old_udm.save()
        user_old = await role_from.klass.from_dn(dn, attr["school"][0], udm)
        assert isinstance(user_old, role_from.klass)
        # check 'addition_class' functionality
        addition_class = {cls_attr2["school"]: [cls_attr2["name"]]}
        if issubclass(role_from.klass, Staff) and issubclass(role_to.klass, Student):
            # Staff user will have no school_class, but for conversion to Student it needs one class per
            # school:
            addition_class[demoschool2_name] = [cls_attr3["name"]]

        if issubclass(role_to.klass, Staff):
            user_new = await convert_to_staff(user_old, udm, addition_class)
        elif issubclass(role_to.klass, Student):
            user_new = await convert_to_student(user_old, udm, addition_class)
        elif issubclass(role_to.klass, TeachersAndStaff):
            user_new = await convert_to_teacher_and_staff(user_old, udm, addition_class)
        else:
            assert issubclass(role_to.klass, Teacher)
            user_new = await convert_to_teacher(user_old, udm, addition_class)
        schedule_delete_user_name(user_new.name)

        if role_from.klass == role_to.klass:
            assert user_old is user_new
            return

        user_new_udm = await udm.get("users/user").get(user_new.dn)
        user_new_ucsschool_roles = set(user_new.ucsschool_roles)
        new_groups = {grp.lower() for grp in user_new_udm.props.groups}

        # check class
        assert isinstance(user_new, role_to.klass)
        assert user_new.__class__ is role_to.klass
        # check domain users OU
        for ou in user_new.schools:
            assert f"cn=Domain Users {ou},cn=groups,ou={ou},{ldap_base}".lower() in new_groups
        # check non-school role is ignored
        assert non_school_role in user_new_ucsschool_roles
        if isinstance(user_new, ImportStaff):
            # check school class
            assert cls_dn1.lower() not in new_groups
            assert cls_dn2.lower() not in new_groups
            assert cls_dn3.lower() not in new_groups
            # check options
            assert user_new_udm.options.get("ucsschoolStaff") is True
            assert user_new_udm.options.get("ucsschoolStudent", False) is False
            assert user_new_udm.options.get("ucsschoolTeacher", False) is False
            # check position
            assert user_new_udm.position == f"cn=mitarbeiter,cn=users,ou={user_new.school},{ldap_base}"
            # check roles
            assert {f"staff:school:{ou}" for ou in user_new.schools}.issubset(user_new_ucsschool_roles)
            assert {
                f"{role}:school:{ou}" for ou in user_new.schools for role in ("student", "teacher")
            }.isdisjoint(user_new_ucsschool_roles)
        elif isinstance(user_new, Student):
            assert cls_dn1.lower() in new_groups
            assert cls_dn2.lower() in new_groups
            assert cls_dn3.lower() in new_groups
            assert user_new_udm.options.get("ucsschoolStudent") is True
            assert user_new_udm.options.get("ucsschoolAdministrator", False) is False
            assert user_new_udm.options.get("ucsschoolStaff", False) is False
            assert user_new_udm.options.get("ucsschoolTeacher", False) is False
            assert user_new_udm.position == f"cn=schueler,cn=users,ou={user_new.school},{ldap_base}"
            assert {f"student:school:{ou}" for ou in user_new.schools}.issubset(user_new_ucsschool_roles)
            assert {
                f"{role}:school:{ou}"
                for ou in user_new.schools
                for role in ("school_admin", "staff", "teacher")
            }.isdisjoint(user_new_ucsschool_roles)
        elif isinstance(user_new, TeachersAndStaff):
            assert cls_dn1.lower() in new_groups
            assert cls_dn2.lower() in new_groups
            assert cls_dn3.lower() in new_groups
            assert user_new_udm.options.get("ucsschoolStaff") is True
            assert user_new_udm.options.get("ucsschoolTeacher") is True
            assert user_new_udm.options.get("ucsschoolStudent", False) is False
            assert (
                user_new_udm.position == f"cn=lehrer und mitarbeiter,cn=users,ou={user_new.school},"
                f"{ldap_base}"
            )
            assert {
                f"{role}:school:{ou}" for ou in user_new.schools for role in ("staff", "teacher")
            }.issubset(user_new_ucsschool_roles)
            assert {f"student:school:{ou}" for ou in user_new.schools}.isdisjoint(
                user_new_ucsschool_roles
            )
        else:
            assert isinstance(user_new, Teacher)
            assert cls_dn1.lower() in new_groups
            assert cls_dn2.lower() in new_groups
            assert cls_dn3.lower() in new_groups
            assert user_new_udm.options.get("ucsschoolTeacher") is True
            assert user_new_udm.options.get("ucsschoolStaff", False) is False
            assert user_new_udm.options.get("ucsschoolStudent", False) is False
            assert user_new_udm.position == f"cn=lehrer,cn=users,ou={user_new.school},{ldap_base}"
            assert {f"teacher:school:{ou}" for ou in user_new.schools}.issubset(user_new_ucsschool_roles)
            assert {
                f"{role}:school:{ou}" for ou in user_new.schools for role in ("student", "staff")
            }.isdisjoint(user_new_ucsschool_roles)


@pytest.mark.asyncio
async def test_modify_role_forbidden(
    ldap_base,
    new_school_class,
    users_user_props,
    new_user,
    udm_kwargs,
    schedule_delete_user_name,
    import_config,
    demoschool2,
):
    # illegal source objects
    cls_dn, cls_attr = await new_school_class()
    async with UDM(**udm_kwargs) as udm:
        sc_obj = await SchoolClass.from_dn(cls_dn, cls_attr["school"], udm)
        with pytest.raises(TypeError, match=r"is not an object of a 'ImportUser' subclass"):
            await convert_to_staff(sc_obj, udm)

        dn, attr = await new_user("teacher")
        user_obj = await ImportTeacher.from_dn(dn, attr["school"][0], udm)
        user_udm = await user_obj.get_udm_object(udm)
        user_udm.options["ucsschoolAdministrator"] = True
        user_udm.props.ucsschoolRecordUID = user_obj.name
        user_udm.props.ucsschoolSourceUID = "TESTID"
        await user_udm.save()
        with pytest.raises(TypeError, match=r"not allowed for school administrator"):
            new_user_obj = await convert_to_student(user_obj, udm)
            schedule_delete_user_name(new_user_obj.name)

    user_props = users_user_props()
    user_props["name"] = user_props.pop("username")
    user_props["school"] = user_props["school"][0]
    user_props["email"] = user_props.pop("mailPrimaryAddress")
    del user_props["description"]

    user_obj = ImportUser(**user_props)
    with pytest.raises(TypeError, match=r"is not an object of a 'ImportUser' subclass"):
        new_user_obj = await convert_to_staff(user_obj, udm)
        schedule_delete_user_name(new_user_obj.name)

    user_obj = ExamStudent(**user_props)
    with pytest.raises(TypeError, match=r"is not an object of a 'ImportUser' subclass"):
        new_user_obj = await convert_to_teacher(user_obj, udm)
        schedule_delete_user_name(new_user_obj.name)

    # illegal convert target
    dn, attr = await new_user("student")
    async with UDM(**udm_kwargs) as udm:
        user_obj = await ImportStudent.from_dn(dn, attr["school"][0], udm)
        schedule_delete_user_name(user_obj.name)

        with pytest.raises(TypeError, match=r"is not a subclass of 'ImportUser'"):
            await ImportUserTypeConverter.convert(user_obj, ImportUser, udm)

        with pytest.raises(TypeError, match=r"is not a subclass of 'ImportUser'"):
            await ImportUserTypeConverter.convert(user_obj, ExamStudent, udm)

        with pytest.raises(TypeError, match=r"is not a subclass of 'ImportUser'"):
            await ImportUserTypeConverter.convert(user_obj, SchoolClass, udm)

        # no school_class for student target
        dn, attr = await new_user("staff")
        user_obj = await ImportStaff.from_dn(dn, attr["school"][0], udm)
        schedule_delete_user_name(user_obj.name)
        user_obj.record_uid = user_obj.name
        user_obj.source_uid = "TESTID"
        await user_obj.modify(udm)
        with pytest.raises(TypeError, match=r"requires at least one school class per school"):
            await ImportUserTypeConverter.convert(user_obj, ImportStudent, udm)

        # not enough school_classes for student target
        demoschool2_dn, demoschool2_name = demoschool2
        dn, attr = await new_user("teacher")
        user_obj = await ImportTeacher.from_dn(dn, attr["school"][0], udm)
        schedule_delete_user_name(user_obj.name)
        user_obj.schools.append(demoschool2_name)
        user_obj.record_uid = user_obj.name
        user_obj.source_uid = "TESTID"
        await user_obj.modify(udm)
        with pytest.raises(TypeError, match=r"requires at least one school class per school"):
            await ImportUserTypeConverter.convert(user_obj, ImportStudent, udm)
