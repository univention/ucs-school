# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import random
import tempfile
from typing import List, Optional  # noqa: F401

import ldap
import passlib.hash
from ldap.filter import filter_format

import ucsschool.lib.models.utils
import univention.config_registry
import univention.testing.strings as uts
import univention.testing.ucr
import univention.testing.udm as udm_test
import univention.uldap
from ucsschool.lib.models.school import School as SchoolLib
from ucsschool.lib.models.user import (
    Staff as StaffLib,
    Student as StudentLib,
    Teacher as TeacherLib,
    TeachersAndStaff as TeachersAndStaffLib,
)
from ucsschool.lib.roles import create_ucsschool_role_string, role_staff, role_student, role_teacher
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_s4connector
from univention.testing.ucsschool.importou import create_ou_cli, get_school_base, remove_ou
from univention.testing.ucsschool.ucs_test_school import udm_formula_for_shadowExpire

configRegistry = univention.config_registry.ConfigRegistry()
configRegistry.load()

cn_pupils = configRegistry.get("ucsschool/ldap/default/container/pupils", "schueler")
cn_teachers = configRegistry.get("ucsschool/ldap/default/container/teachers", "lehrer")
cn_teachers_staff = configRegistry.get(
    "ucsschool/ldap/default/container/teachers-and-staff", "lehrer und mitarbeiter"
)
cn_staff = configRegistry.get("ucsschool/ldap/default/container/staff", "mitarbeiter")

grp_prefix_pupils = configRegistry.get("ucsschool/ldap/default/groupprefix/pupils", "schueler-")
grp_prefix_teachers = configRegistry.get("ucsschool/ldap/default/groupprefix/teachers", "lehrer-")
grp_prefix_admins = configRegistry.get("ucsschool/ldap/default/groupprefix/admins", "admins-")
grp_prefix_staff = configRegistry.get("ucsschool/ldap/default/groupprefix/staff", "mitarbeiter-")

samba_logon_script = configRegistry.get("ucsschool/import/set/netlogon/script/path")
homedrive = configRegistry.get("ucsschool/import/set/homedrive")


class Person(object):
    _samba_info = {}

    def __init__(self, school, role, **kwargs):
        self.school = school
        self.role = role
        self.firstname = kwargs.get("firstname", uts.random_name())
        self.lastname = kwargs.get("lastname", uts.random_name())
        self.username = kwargs.get("username", uts.random_name())
        self.legacy_v2 = kwargs.get("legacy_v2", False)
        self.schools = kwargs.get("schools", [school])
        self.record_uid = kwargs.get("record_uid")
        self.source_uid = kwargs.get("source_uid")
        self.description = kwargs.get("description")
        self.mail = kwargs.get("mail", "{}@{}".format(self.username, get_mail_domain()))
        self.school_classes = kwargs.get("school_classes", {})
        self.mode = kwargs.get("mode", "A")
        self.active = kwargs.get("active", True)
        self.password = kwargs.get("password")
        self.birthday = kwargs.get("birthday")
        self.expiration_date = kwargs.get("expiration_date")
        self.override_pw_history = kwargs.get("override_pw_history", "0")
        if self.is_student():
            self.cn = cn_pupils
            self.grp_prefix = grp_prefix_pupils
        elif self.is_teacher():
            self.cn = cn_teachers
            self.grp_prefix = grp_prefix_teachers
        elif self.is_teacher_staff():
            self.cn = cn_teachers_staff
            self.grp_prefix = grp_prefix_teachers
        elif self.is_staff():
            self.cn = cn_staff
            self.grp_prefix = grp_prefix_staff
        self.school_base = self.make_school_base()
        self.dn = self.make_dn()
        self.append_random_groups()

    def make_dn(self):
        return "uid=%s,cn=%s,cn=users,%s" % (self.username, self.cn, self.school_base)

    @property
    def homedir(self):
        subdir = ""
        if configRegistry.is_true("ucsschool/import/roleshare", True):
            if self.is_student():
                subdir = os.path.join(self.school, "schueler")
            elif self.is_teacher() or self.is_teacher_staff():
                subdir = os.path.join(self.school, "lehrer")
            elif self.is_staff():
                subdir = os.path.join(self.school, "mitarbeiter")
        return os.path.join("/home", subdir, self.username)

    def make_school_base(self):
        return get_school_base(self.school)

    def append_random_groups(self):
        if self.is_student():
            self.append_random_class()
            self.append_random_working_group()
        elif self.is_teacher():
            self.append_random_class()
            self.append_random_class()
            self.append_random_class()
            self.append_random_working_group()
            self.append_random_working_group()
        elif self.is_teacher_staff():
            self.append_random_class()
            self.append_random_working_group()
            self.append_random_working_group()
        elif self.is_staff():
            pass

    def set_mode_to_modify(self):
        self.mode = "M"

    def set_mode_to_delete(self):
        self.mode = "D"

    def set_active(self):
        self.active = True

    def set_inactive(self):
        self.active = False

    def is_active(self):
        return self.active

    def _set_school(self, school):
        old_school = self.school
        self.school = school
        if len(self.schools) == 1:
            self.schools = [self.school]
        elif self.school not in self.schools:
            self.schools.append(self.school)
        self.school_base = self.make_school_base()
        self.dn = self.make_dn()
        if old_school not in self.schools and old_school in self.school_classes:
            self.move_school_classes(old_school, self.school)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key == "dn":
                self.username = ldap.explode_rdn(value, notypes=True)[0]
                self.dn = value
            if key == "username":
                self.username = value
                self.dn = self.make_dn()
            elif key == "school":
                self._set_school(value)
            elif key == "schools":
                if not self.school and "school" not in kwargs:
                    self._set_school(sorted(value)[0])
                self.schools = value
            elif hasattr(self, key):
                setattr(self, key, value)
            else:
                print("ERROR: cannot update Person(): unknown option %r=%r" % (key, value))

    def move_school_classes(self, old_school, new_school):
        assert new_school in self.schools

        for school, classes in list(self.school_classes.items()):
            if school == old_school:
                new_classes = [
                    cls.replace("{}-".format(old_school), "{}-".format(new_school)) for cls in classes
                ]
                self.school_classes[new_school] = new_classes

        self.school_classes.pop(old_school, None)

    def map_to_dict(self, value_map, prefix_schools=True):
        result = {
            value_map.get("firstname", "__EMPTY__"): self.firstname,
            value_map.get("lastname", "__EMPTY__"): self.lastname,
            value_map.get("name", "__EMPTY__"): self.username,
            value_map.get("schools", "__EMPTY__"): ",".join(self.schools),
            value_map.get("role", "__EMPTY__"): self.role,
            value_map.get("record_uid", "__EMPTY__"): self.record_uid,
            value_map.get("source_uid", "__EMPTY__"): self.source_uid,
            value_map.get("description", "__EMPTY__"): self.description,
            value_map.get("overridePWHistory", "__EMPTY__"): self.override_pw_history,
            value_map.get("school_classes", "__EMPTY__"): ",".join(
                [
                    x
                    if not prefix_schools or x.startswith("{school}-".format(school=school))
                    else "{school}-{x}".format(school=school, x=x)
                    for school, classes in self.school_classes.items()
                    for x in classes
                ]
            ),
            value_map.get("email", "__EMPTY__"): self.mail,
            value_map.get("__action", "__EMPTY__"): self.mode,
            value_map.get("__role", "__EMPTY__"): self.role,
            value_map.get("password", "__EMPTY__"): self.password,
            value_map.get("birthday", "__EMPTY__"): self.birthday,
            value_map.get("expiration_date", "__EMPTY__"): self.expiration_date,
        }
        if "__EMPTY__" in result:
            del result["__EMPTY__"]
        return result

    def __str__(self):
        delimiter = "\t"
        return delimiter.join(self.get_csv_line())

    def get_csv_line(self):
        line = [
            self.mode,
            self.username,
            self.lastname,
            self.firstname,
            self.school,
            ",".join([x for school_, classes in self.school_classes.items() for x in classes]),
            "",
            self.mail,
            str(int(self.is_teacher() or self.is_teacher_staff())),
            str(int(self.is_active())),
            str(int(self.is_staff() or self.is_teacher_staff())),
        ]
        if self.password:
            line.append(self.password)
        return line

    def append_random_class(self, schools=None):
        if not schools:
            schools = [self.school]
        for school in schools:
            self.school_classes.setdefault(school, []).append(
                "%s-%s%s%s"
                % (
                    school,
                    uts.random_int(),
                    uts.random_int(),
                    uts.random_string(length=2, alpha=True, numeric=False),
                )
            )

    def append_random_working_group(self):
        return
        # working groups cannot be specified, neither in file for CLI nor by API in Python
        # self.school_classes.setdefault(self.school, []).append('%s-%s' % (
        #   self.school, uts.random_string(length=9, alpha=True, numeric=False)))

    def is_student(self):
        return self.role == "student"

    def is_teacher(self):
        return self.role == "teacher"

    def is_staff(self):
        return self.role == "staff"

    def is_teacher_staff(self):
        return self.role in ("teacher_staff", "teacher_and_staff")

    def expected_attributes(self):
        samba_home_path_server = self.get_samba_home_path_server()
        profile_path_server = self.get_profile_path_server()
        # If one of "krb5ValidEnd", "shadowExpire", "sambaKickoffTime" is set,
        # we assume the rest to be correct.
        shadow_expire = [] if self.active else ["1"]
        if self.expiration_date:
            shadow_expire = [udm_formula_for_shadowExpire(self.expiration_date)]
        attr = {
            "departmentNumber": [self.school],
            "givenName": [self.firstname],
            "homeDirectory": [self.homedir],
            "krb5KDCFlags": ["126"] if self.is_active() else ["254"],
            "mail": [self.mail] if self.mail else [],
            "mailPrimaryAddress": [self.mail] if self.mail else [],
            "sambaAcctFlags": ["[U          ]"] if self.active else ["[UD         ]"],
            "shadowExpire": shadow_expire,
            "sn": [self.lastname],
            "uid": [self.username],
            "ucsschoolRole": self.roles,
            "ucsschoolSourceUID": [self.source_uid] if self.source_uid else [],
            "ucsschoolRecordUID": [self.record_uid] if self.record_uid else [],
            "description": [self.description] if self.description else [],
            "ucsschoolSchool": self.schools,
            "univentionBirthday": [self.birthday] if self.birthday else [],
            "sambaLogonScript": [samba_logon_script]
            if samba_logon_script and not self.is_staff()
            else [],
            "sambaHomeDrive": [homedrive] if homedrive and not self.is_staff() else [],
            "sambaHomePath": []
            if self.is_staff() or not samba_home_path_server
            else ["\\\\{}\\{}".format(samba_home_path_server, self.username)],
            "sambaProfilePath": []
            if self.is_staff() or not profile_path_server
            else [profile_path_server],
        }

        if self.password:
            attr["sambaNTPassword"] = [passlib.hash.nthash.hash(self.password).upper()]

        return attr

    def _add_to_samba_info_school_base_cache(self, school_base):
        self._samba_info[school_base] = {}
        lo = univention.uldap.getMachineConnection()
        query_result = lo.search(
            base=school_base, scope=ldap.SCOPE_BASE, attr=["ucsschoolHomeShareFileServer"]
        )
        if query_result:
            share_file_server_dn = (
                query_result[0][1].get("ucsschoolHomeShareFileServer")[0].decode("UTF-8")
            )
            res = ldap.explode_rdn(share_file_server_dn, True)[0]
        else:
            res = None
        self._samba_info[school_base]["ucsschoolHomeShareFileServer"] = res

        query_result = lo.search(
            base=self.school_base, filter="univentionService=Windows Profile Server", attr=["cn"]
        )
        if query_result:
            server = "\\\\%s" % query_result[0][1].get("cn")[0].decode("UTF-8")
        else:
            server = "%LOGONSERVER%"
        self._samba_info[school_base][
            "WindowsProfileServer"
        ] = "{}\\%USERNAME%\\windows-profiles\\default".format(server)

    def get_samba_home_path_server(self):
        sambahome = configRegistry.get("ucsschool/import/set/sambahome")
        if sambahome:
            print("UCR variable ucsschool/import/set/sambahome is set")
            return sambahome
        is_singlemaster = configRegistry.is_true("ucsschool/singlemaster", False)
        if is_singlemaster:
            print("UCR variable ucsschool/singlemaster is set")
            return configRegistry.get("hostname")
        if self.school_base not in self._samba_info:
            self._add_to_samba_info_school_base_cache(self.school_base)
        return self._samba_info[self.school_base]["ucsschoolHomeShareFileServer"]

    def get_profile_path_server(self):
        serverprofile_path = configRegistry.get("ucsschool/import/set/serverprofile/path")
        if serverprofile_path:
            print("UCR variable ucsschool/import/set/serverprofile/path is set")
            return serverprofile_path
        if self.school_base not in self._samba_info:
            self._add_to_samba_info_school_base_cache(self.school_base)
        return self._samba_info[self.school_base]["WindowsProfileServer"]

    @property
    def roles(self):
        roles = {
            "student": [role_student],
            "teacher": [role_teacher],
            "staff": [role_staff],
            "teacher_staff": [role_teacher, role_staff],
            "teacher_and_staff": [role_teacher, role_staff],
        }[self.role]
        res = []
        for role in roles:
            res.extend([create_ucsschool_role_string(role, school) for school in self.schools])
        return res

    def verify(self):
        print("verify %s: %s" % (self.role, self.username))
        utils.wait_for_replication()
        # reload UCR
        configRegistry.load()

        if self.mode == "D":
            utils.verify_ldap_object(self.dn, should_exist=False)
            return

        utils.verify_ldap_object(
            self.dn, expected_attr=self.expected_attributes(), strict=True, should_exist=True
        )

        default_group_dn = "cn=Domain Users %s,cn=groups,%s" % (self.school, self.school_base)
        utils.verify_ldap_object(
            default_group_dn,
            expected_attr={"uniqueMember": [self.dn], "memberUid": [self.username]},
            strict=False,
            should_exist=True,
        )

        for school, classes in self.school_classes.items():
            for cl in classes:
                cl_group_dn = "cn=%s,cn=klassen,cn=%s,cn=groups,%s" % (
                    cl if cl.startswith("%s-" % school) else "%s-%s" % (school, cl),
                    cn_pupils,
                    get_school_base(school),
                )
                utils.verify_ldap_object(
                    cl_group_dn,
                    expected_attr={"uniqueMember": [self.dn], "memberUid": [self.username]},
                    strict=False,
                    should_exist=True,
                )

        assert self.school in self.schools

        for school in self.schools:
            role_group_dn = "cn=%s%s,cn=groups,%s" % (self.grp_prefix, school, get_school_base(school))
            utils.verify_ldap_object(
                role_group_dn,
                expected_attr={"uniqueMember": [self.dn], "memberUid": [self.username]},
                strict=False,
                should_exist=True,
            )

        print("person OK: %s" % self.username)

    def update_from_ldap(self, lo, attrs, source_uid=None, record_uid=None):
        # type: (univention.admin.uldap.access, List[str], Optional[str], Optional[str]) -> None
        """
        Fetch attributes listed in `attrs` and set them on self.

        source_uid and record_uid must either be set on self or given.
        """
        assert source_uid or self.source_uid
        assert record_uid or self.record_uid

        ldap2person = {
            "dn": "dn",
            "mail": "mailPrimaryAddress",
            "username": "uid",
        }

        filter_s = filter_format(
            "(&(objectClass=ucsschoolType)(ucsschoolSourceUID=%s)(ucsschoolRecordUID=%s))",
            (source_uid or self.source_uid, record_uid or self.record_uid),
        )
        res = lo.search(filter=filter_s)
        if len(res) != 1:
            raise RuntimeError(
                "Search with filter={!r} did not return 1 result:\n{}".format(
                    filter_s, "\n".join(repr(res))
                )
            )
        try:
            dn = res[0][0]
            attrs_from_ldap = res[0][1]
        except KeyError as exc:
            raise KeyError("Error searching for user: {} res={!r}".format(exc, res))
        kwargs = {}
        for attr in attrs:
            if attr == "dn":
                value = dn
            else:
                try:
                    key = ldap2person[attr]
                except KeyError:
                    raise NotImplementedError("Mapping for {!r} not yet implemented.".format(attr))
                value = attrs_from_ldap.get(key, [b""])[0].decode("UTF-8")
            kwargs[attr] = value
        self.update(**kwargs)

    def set_random_birthday(self):
        self.update(
            birthday="19{}-0{}-{}{}".format(
                2 * uts.random_int(), uts.random_int(1, 9), uts.random_int(0, 2), uts.random_int(1, 8)
            )
        )


class Student(Person):
    def __init__(self, school):
        Person.__init__(self, school, "student")


class Teacher(Person):
    def __init__(self, school):
        Person.__init__(self, school, "teacher")


class Staff(Person):
    def __init__(self, school):
        Person.__init__(self, school, "staff")


class TeacherStaff(Person):
    def __init__(self, school):
        Person.__init__(self, school, "teacher_staff")


class ImportFile:
    def __init__(self):
        self.import_fd, self.import_file = tempfile.mkstemp()
        os.close(self.import_fd)
        self.user_import = None

    def write_import(self):
        self.import_fd = os.open(self.import_file, os.O_RDWR | os.O_CREAT)
        os.write(self.import_fd, str(self.user_import).encode("utf-8"))
        os.close(self.import_fd)

    def run_import(self, user_import):
        self.user_import = user_import
        try:
            self._run_import_via_python_api()
            print("SCHOOL DATA     :\n%s" % str(self.user_import))
        finally:
            try:
                os.remove(self.import_file)
            except OSError as e:
                print("WARNING: %s not removed. %s" % (self.import_file, e))

    def _run_import_via_python_api(self):
        # reload UCR
        ucsschool.lib.models.utils.ucr.load()

        lo = univention.admin.uldap.getAdminConnection()[0]

        # get school from first user
        school = self.user_import.students[0].school

        school_obj = SchoolLib.cache(school, display_name=school)
        if not school_obj.exists(lo):
            school_obj.dc_name = uts.random_name()
            school_obj.create(lo)

        def _set_kwargs(user):
            kwargs = {
                "school": user.school,
                "schools": [user.school],
                "name": user.username,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "school_classes": user.school_classes,
                "email": user.mail,
                "password": user.password,
                "disabled": "0" if user.is_active() else "1",
                "birthday": user.birthday,
                "expiration_date": user.expiration_date,
            }
            return kwargs

        for user in self.user_import.students:
            kwargs = _set_kwargs(user)
            print("* student username=%r mode=%r kwargs=%r" % (user.username, user.mode, kwargs))
            if user.mode == "A":
                StudentLib(**kwargs).create(lo)
            elif user.mode == "M":
                StudentLib(**kwargs).modify(lo)
            elif user.mode == "D":
                StudentLib(**kwargs).remove(lo)

        for user in self.user_import.teachers:
            kwargs = _set_kwargs(user)
            print("* teacher username=%r mode=%r kwargs=%r" % (user.username, user.mode, kwargs))
            if user.mode == "A":
                TeacherLib(**kwargs).create(lo)
            elif user.mode == "M":
                TeacherLib(**kwargs).modify(lo)
            elif user.mode == "D":
                TeacherLib(**kwargs).remove(lo)

        for user in self.user_import.staff:
            kwargs = _set_kwargs(user)
            print("* staff username=%r mode=%r kwargs=%r" % (user.username, user.mode, kwargs))
            if user.mode == "A":
                StaffLib(**kwargs).create(lo)
            elif user.mode == "M":
                StaffLib(**kwargs).modify(lo)
            elif user.mode == "D":
                StaffLib(**kwargs).remove(lo)

        for user in self.user_import.teacher_staff:
            kwargs = _set_kwargs(user)
            print("* teacher_staff username=%r mode=%r kwargs=%r" % (user.username, user.mode, kwargs))
            if user.mode == "A":
                TeachersAndStaffLib(**kwargs).create(lo)
            elif user.mode == "M":
                TeachersAndStaffLib(**kwargs).modify(lo)
            elif user.mode == "D":
                TeachersAndStaffLib(**kwargs).remove(lo)


class UserImport:
    def __init__(self, school_name=None, nr_students=20, nr_teachers=10, nr_staff=5, nr_teacher_staff=3):
        assert nr_students > 2
        assert nr_teachers > 2
        assert nr_staff > 2
        assert nr_teacher_staff > 2

        self.school = school_name

        self.students = [Student(self.school) for _i in range(nr_students)]
        self.students[2].set_inactive()
        self.students[0].password = uts.random_name()

        self.teachers = [Teacher(self.school) for _i in range(nr_teachers)]
        self.teachers[1].set_inactive()
        self.teachers[1].password = uts.random_name()

        self.staff = [Staff(self.school) for _i in range(nr_staff)]
        self.staff[2].set_inactive()
        self.staff[1].password = uts.random_name()

        self.teacher_staff = [TeacherStaff(self.school) for _i in range(nr_teacher_staff)]
        self.teacher_staff[1].set_inactive()
        self.teacher_staff[2].password = uts.random_name()

    def __str__(self):
        lines = [str(student) for student in self.students]
        lines.extend(str(teacher) for teacher in self.teachers)
        lines.extend(str(staff) for staff in self.staff)
        lines.extend(str(teacher_staff) for teacher_staff in self.teacher_staff)
        return "\n".join(lines)

    def verify(self):
        for student in self.students:
            student.verify()

        for teacher in self.teachers:
            teacher.verify()

        for staff in self.staff:
            staff.verify()

        for teacher_staff in self.teacher_staff:
            teacher_staff.verify()

    def modify(self):
        for student in self.students:
            student.set_mode_to_modify()
        self.students[1].mail = "%s@%s" % (uts.random_name(), get_mail_domain())
        self.students[2].firstname = uts.random_name()
        self.students[2].lastname = uts.random_name()
        self.students[2].set_inactive()

        for teacher in self.teachers:
            teacher.set_mode_to_modify()
        self.students[0].mail = "%s@%s" % (uts.random_name(), get_mail_domain())
        self.students[2].firstname = uts.random_name()
        self.students[2].lastname = uts.random_name()

        for staff in self.staff:
            staff.set_mode_to_modify()
        self.students[0].set_inactive()
        self.students[2].firstname = uts.random_name()
        self.students[2].lastname = uts.random_name()

        for teacher_staff in self.teacher_staff:
            teacher_staff.set_mode_to_modify()
        self.students[0].set_inactive()
        self.students[2].firstname = uts.random_name()
        self.students[2].lastname = uts.random_name()

    def delete(self):
        for student in self.students:
            student.set_mode_to_delete()

        for teacher in self.teachers:
            teacher.set_mode_to_delete()

        for staff in self.staff:
            staff.set_mode_to_delete()

        for teacher_staff in self.teacher_staff:
            teacher_staff.set_mode_to_delete()


def create_and_verify_users(
    school_name=None,
    nr_students=3,
    nr_teachers=3,
    nr_staff=3,
    nr_teacher_staff=3,
):
    print("********** Generate school data")
    user_import = UserImport(
        school_name=school_name,
        nr_students=nr_students,
        nr_teachers=nr_teachers,
        nr_staff=nr_staff,
        nr_teacher_staff=nr_teacher_staff,
    )
    import_file = ImportFile()

    print(user_import)

    print("********** Create users")
    import_file.run_import(user_import)
    utils.wait_for_replication()
    wait_for_s4connector()
    user_import.verify()

    print("********** Modify users")
    user_import.modify()
    import_file.run_import(user_import)
    utils.wait_for_replication()
    wait_for_s4connector()
    user_import.verify()

    print("********** Delete users")
    user_import.delete()
    import_file.run_import(user_import)
    utils.wait_for_replication()
    wait_for_s4connector()
    user_import.verify()


def create_windows_profile_server(udm, ou, name):
    properties = {
        "name": name,
        "service": "Windows Profile Server",
    }
    school_base = get_school_base(ou)

    udm.create_object("computers/memberserver", position=school_base, **properties)


def create_home_server(udm, name):
    properties = {
        "name": name,
    }
    udm.create_object("computers/memberserver", **properties)


def import_users_basics():
    with univention.testing.ucr.UCSTestConfigRegistry() as ucr, udm_test.UCSTestUDM() as udm:
        ucr.load()
        return _import_users_basics(udm)


def _import_users_basics(udm):
    for singlemaster in [False, True]:
        for samba_home_server in [None, "generate"]:
            for profile_path_server in [None, "generate"]:
                for home_server_at_ou in [None, "generate"]:
                    for windows_profile_server in [None, "generate"]:
                        if samba_home_server == "generate":
                            samba_home_server = uts.random_name()

                        if profile_path_server == "generate":
                            profile_path_server = uts.random_name()

                        school_name = uts.random_name()

                        if home_server_at_ou:
                            home_server_at_ou = uts.random_name()
                            create_home_server(udm, home_server_at_ou)
                            create_ou_cli(school_name, sharefileserver=home_server_at_ou)
                        else:
                            create_ou_cli(school_name)

                        try:
                            if windows_profile_server:
                                windows_profile_server = uts.random_name()
                                create_windows_profile_server(
                                    udm=udm, ou=school_name, name=windows_profile_server
                                )

                            univention.config_registry.handler_set(
                                [
                                    "ucsschool/singlemaster=%s" % ("true" if singlemaster else "false"),
                                    "ucsschool/import/set/sambahome=%s" % samba_home_server,
                                    "ucsschool/import/set/serverprofile/path=%s" % profile_path_server,
                                ]
                            )

                            if not samba_home_server:
                                univention.config_registry.handler_unset(
                                    ["ucsschool/import/set/sambahome"]
                                )

                            if not profile_path_server:
                                univention.config_registry.handler_unset(
                                    ["ucsschool/import/set/serverprofile/path"]
                                )

                            print("")
                            print("**** import_users_basics:")
                            print("****    singlemaster: %s" % singlemaster)
                            print("****    samba_home_server: %s" % samba_home_server)
                            print("****    profile_path_server: %s" % profile_path_server)
                            print("****    home_server_at_ou: %s" % home_server_at_ou)
                            print("****    windows_profile_server: %s" % windows_profile_server)
                            print("")
                            create_and_verify_users(school_name, 3, 3, 3, 3)
                        finally:
                            remove_ou(school_name)

    utils.wait_for_replication()


def get_mail_domain():  # type: () -> str
    try:
        mail_domain = random.choice(configRegistry["mail/hosteddomains"].split())
    except (AttributeError, IndexError):
        mail_domain = configRegistry["domainname"]
    udm = udm_test.UCSTestUDM()
    if not udm.list_objects("mail/domain", filter="cn={}".format(mail_domain)):
        udm.create_object(
            "mail/domain",
            position="cn=domain,cn=mail,{}".format(configRegistry["ldap/base"]),
            name=mail_domain,
        )
    return mail_domain


class NonPrefixPerson(Person):
    def append_random_class(self, schools=None):
        if not schools:
            schools = [self.school]
        for school in schools:
            self.school_classes.setdefault(school, []).append(
                "%s%s%s"
                % (
                    uts.random_int(),
                    uts.random_int(),
                    uts.random_string(length=2, alpha=True, numeric=False),
                )
            )
