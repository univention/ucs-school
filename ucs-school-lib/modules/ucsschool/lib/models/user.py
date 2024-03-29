#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2024 Univention GmbH
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

import os.path
from collections import Mapping
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple, Type  # noqa: F401

from ldap.dn import escape_dn_chars, explode_rdn
from ldap.filter import filter_format
from six import iteritems

import univention.admin.modules as udm_modules
from univention.admin import syntax
from univention.admin.filter import conjunction, parse
from univention.admin.uexceptions import noObject, valueError

from ..roles import role_exam_user, role_pupil, role_school_admin, role_staff, role_student, role_teacher
from .attributes import (
    Birthday,
    Disabled,
    Email,
    Firstname,
    Lastname,
    Password,
    SchoolClassesAttribute,
    Schools,
    UserExpirationDate,
    Username,
    WorkgroupsAttribute,
)
from .base import NoObject, RoleSupportMixin, UCSSchoolHelperAbstractClass, UnknownModel, WrongModel
from .computer import AnyComputer
from .group import BasicGroup, Group, SchoolClass, SchoolGroup, WorkGroup
from .misc import MailDomain
from .school import School
from .utils import _, create_passwd, ucr

if TYPE_CHECKING:
    from .base import LoType, SuperOrdinateType, UdmObject, UldapFilter  # noqa: F401


class User(RoleSupportMixin, UCSSchoolHelperAbstractClass):
    name = Username(_("Username"), aka=["Username", "Benutzername"])  # type: str
    schools = Schools(_("Schools"))  # type: List[str]
    firstname = Firstname(
        _("First name"),
        aka=["First name", "Vorname"],
        required=True,
        unlikely_to_change=True,
    )  # type: str
    lastname = Lastname(
        _("Last name"),
        aka=["Last name", "Nachname"],
        required=True,
        unlikely_to_change=True,
    )  # type: str
    birthday = Birthday(
        _("Birthday"), aka=["Birthday", "Geburtstag"], unlikely_to_change=True
    )  # type: str
    expiration_date = UserExpirationDate(
        _("Expiration date"), aka=["Expiration date", "Ablaufdatum"]
    )  # type: str
    email = Email(_("Email"), aka=["Email", "E-Mail"], unlikely_to_change=True)  # type: str
    password = Password(_("Password"), aka=["Password", "Passwort"])  # type: Optional[str]
    disabled = Disabled(_("Disabled"), aka=["Disabled", "Gesperrt"])  # type: bool
    school_classes = SchoolClassesAttribute(
        _("Class"), aka=["Class", "Klasse"]
    )  # type: Dict[str, List[str]]
    workgroups = WorkgroupsAttribute(
        _("WorkGroup"), aka=["WorkGroup", "Workgroup"]
    )  # type: Dict[str, List[str]]

    type_name = None  # type: str
    type_filter = (
        "(|(objectClass=ucsschoolTeacher)(objectClass=ucsschoolStaff)(objectClass=ucsschoolStudent))"
    )

    _profile_path_cache = {}  # type: Dict[str, str]
    _samba_home_path_cache = {}  # type: Dict[str, str]
    # _samba_home_path_cache is invalidated in School.invalidate_cache()

    roles = []  # type: List[str]
    default_roles = []  # type: List[str]
    default_options = ()  # type: Tuple[str]

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self.check_password_policies = False
        if self.school_classes is None:
            self.school_classes = {}  # set a dict for Staff
        if self.school and not self.schools:
            self.schools.append(self.school)

    @classmethod
    def shall_create_mail_domain(cls):  # type: () -> bool
        return ucr.is_true("ucsschool/import/generate/mail/domain")

    def get_roleshare_home_subdir(self):  # type: () -> str
        from ucsschool.lib.roleshares import roleshare_home_subdir

        return roleshare_home_subdir(self.school, self.roles, ucr)

    def get_samba_home_drive(self):  # type: () -> str
        return ucr.get("ucsschool/import/set/homedrive")

    def get_samba_netlogon_script_path(self):  # type: () -> str
        return ucr.get("ucsschool/import/set/netlogon/script/path")

    def get_samba_home_path(self, lo):  # type: (LoType) -> str
        school = School.cache(self.school)
        # if defined then use UCR value
        ucr_variable = ucr.get("ucsschool/import/set/sambahome")
        if ucr_variable is not None:
            samba_home_path = r"\\%s" % ucr_variable.strip("\\")
        elif ucr.is_true("ucsschool/singlemaster", False):
            # in single server environments the Primary Directory Node is always the fileserver
            samba_home_path = r"\\%s" % ucr.get("hostname")
        # if there's a cached result then use it
        elif school.dn not in self._samba_home_path_cache:
            samba_home_path = None
            # get windows home server from OU object
            school = self.get_school_obj(lo)
            home_share_file_server = school.home_share_file_server
            if home_share_file_server:
                samba_home_path = r"\\%s" % self.get_name_from_dn(home_share_file_server)
            self._samba_home_path_cache[school.dn] = samba_home_path
        else:
            samba_home_path = self._samba_home_path_cache[school.dn]
        if samba_home_path is not None:
            return r"%s\%s" % (samba_home_path, self.name)

    def get_profile_path(self, lo):  # type: (LoType) -> str
        ucr_variable = ucr.get("ucsschool/import/set/serverprofile/path")
        if ucr_variable is not None:
            return ucr_variable
        school = School.cache(self.school)
        if school.dn not in self._profile_path_cache:
            profile_path = r"%s\%%USERNAME%%\windows-profiles\default"
            for computer in AnyComputer.get_all(
                lo, self.school, "univentionService=Windows Profile Server"
            ):
                profile_path = profile_path % (r"\\%s" % computer.name)
                break
            else:
                profile_path = profile_path % "%LOGONSERVER%"
            self._profile_path_cache[school.dn] = profile_path
        return self._profile_path_cache[school.dn]

    def is_student(self, lo):  # type: (LoType) -> bool
        return self.__check_object_class(lo, "ucsschoolStudent", self._legacy_is_student)

    def is_exam_student(self, lo):  # type: (LoType) -> bool
        return self.__check_object_class(lo, "ucsschoolExam", self._legacy_is_exam_student)

    def is_teacher(self, lo):  # type: (LoType) -> bool
        return self.__check_object_class(lo, "ucsschoolTeacher", self._legacy_is_teacher)

    def is_staff(self, lo):  # type: (LoType) -> bool
        return self.__check_object_class(lo, "ucsschoolStaff", self._legacy_is_staff)

    def is_administrator(self, lo):  # type: (LoType) -> bool
        return self.__check_object_class(lo, "ucsschoolAdministrator", self._legacy_is_admininstrator)

    @classmethod
    def _legacy_is_student(cls, school, dn):  # type: (str, str) -> bool
        cls.logger.warning("Using deprecated method is_student()")
        return dn.lower().endswith(cls.get_search_base(school).students.lower())

    @classmethod
    def _legacy_is_exam_student(cls, school, dn):  # type: (str, str) -> bool
        cls.logger.warning("Using deprecated method is_exam_student()")
        return dn.lower().endswith(cls.get_search_base(school).examUsers.lower())

    @classmethod
    def _legacy_is_teacher(cls, school, dn):  # type: (str, str) -> bool
        cls.logger.warning("Using deprecated method is_teacher()")
        search_base = cls.get_search_base(school)
        return (
            dn.lower().endswith(search_base.teachers.lower())
            or dn.lower().endswith(search_base.teachersAndStaff.lower())
            or dn.lower().endswith(search_base.admins.lower())
        )

    @classmethod
    def _legacy_is_staff(cls, school, dn):  # type: (str, str) -> bool
        cls.logger.warning("Using deprecated method is_staff()")
        search_base = cls.get_search_base(school)
        return dn.lower().endswith(search_base.staff.lower()) or dn.lower().endswith(
            search_base.teachersAndStaff.lower()
        )

    @classmethod
    def _legacy_is_admininstrator(cls, school, dn):  # type: (str, str) -> bool
        cls.logger.warning("Using deprecated method is_admininstrator()")
        return dn.lower().endswith(cls.get_search_base(school).admins.lower())

    def __check_object_class(self, lo, object_class, fallback):
        # type: (LoType, str, Callable[[str, str], bool]) -> bool
        obj = self.get_udm_object(lo)
        if not obj:
            raise noObject("Could not read %r" % (self.dn,))
        if "ucsschoolSchool" in obj.oldattr:
            return object_class.encode("UTF-8") in obj.oldattr.get("objectClass", [])
        return fallback(self.school, self.dn)

    @classmethod
    def get_class_for_udm_obj(cls, udm_obj, school):  # type: (UdmObject, str) -> Type["User"]
        ocs = {x.decode("UTF-8") for x in udm_obj.oldattr.get("objectClass", [])}
        if ocs >= {"ucsschoolTeacher", "ucsschoolStaff"}:
            return TeachersAndStaff
        if ocs >= {"ucsschoolExam", "ucsschoolStudent"}:
            return ExamStudent
        if "ucsschoolTeacher" in ocs:
            return Teacher
        if "ucsschoolStaff" in ocs:
            return Staff
        if "ucsschoolStudent" in ocs:
            return Student
        if "ucsschoolAdministrator" in ocs:
            return SchoolAdmin

        # legacy DN based checks
        if cls._legacy_is_student(school, udm_obj.dn):
            return Student
        if cls._legacy_is_teacher(school, udm_obj.dn):
            if cls._legacy_is_staff(school, udm_obj.dn):
                return TeachersAndStaff
            return Teacher
        if cls._legacy_is_staff(school, udm_obj.dn):
            return Staff
        if cls._legacy_is_exam_student(school, udm_obj.dn):
            return ExamStudent

        return User

    @classmethod
    def from_udm_obj(cls, udm_obj, school, lo):  # type: (UdmObject, str, LoType) -> "User"
        obj = super(User, cls).from_udm_obj(udm_obj, school, lo)
        obj.password = None
        obj.school_classes = cls.get_school_classes(udm_obj, obj)
        obj.workgroups = cls.get_workgroups(udm_obj, obj)
        return obj

    def create(
        self, lo, validate=True, check_password_policies=False
    ):  # type: (LoType, Optional[bool], Optional[bool]) -> bool
        self.check_password_policies = check_password_policies
        return super(User, self).create(lo=lo, validate=validate)

    def do_create(self, udm_obj, lo):  # type: (UdmObject, LoType) -> None
        if not self.schools:
            self.schools = [self.school]
        self.set_default_options(udm_obj)
        self.create_mail_domain(lo)
        password_created = False
        if not self.password:
            self.logger.debug("No password given. Generating random one")
            self.password = create_passwd(dn=self.dn)
            password_created = True
        udm_obj["primaryGroup"] = self.primary_group_dn(lo)
        udm_obj["groups"] = self.groups_used(lo)
        subdir = self.get_roleshare_home_subdir()
        udm_obj["unixhome"] = "/home/" + os.path.join(subdir, self.name)
        if password_created or not self.check_password_policies:
            udm_obj["overridePWHistory"] = "1"
            udm_obj["overridePWLength"] = "1"
        else:
            udm_obj["overridePWHistory"] = "0"
            udm_obj["overridePWLength"] = "0"
        if self.disabled is None:
            udm_obj["disabled"] = "0"
        if "mailbox" in udm_obj:
            udm_obj["mailbox"] = "/var/spool/%s/" % self.name
        samba_home = self.get_samba_home_path(lo)
        if samba_home:
            udm_obj["sambahome"] = samba_home
        profile_path = self.get_profile_path(lo)
        if profile_path:
            udm_obj["profilepath"] = profile_path
        home_drive = self.get_samba_home_drive()
        if home_drive is not None:
            udm_obj["homedrive"] = home_drive
        script_path = self.get_samba_netlogon_script_path()
        if script_path is not None:
            udm_obj["scriptpath"] = script_path
        success = super(User, self).do_create(udm_obj, lo)
        if password_created:
            # dont' show password in post_hooks
            # (it has already been saved to LDAP in super().do_create() above)
            self.password = ""  # nosec
        return success

    def modify(
        self, lo, validate=True, move_if_necessary=None, check_password_policies=False
    ):  # type: (LoType, Optional[bool], Optional[bool], Optional[bool]) -> bool
        self.check_password_policies = check_password_policies
        return super(User, self).modify(lo=lo, validate=validate, move_if_necessary=move_if_necessary)

    def do_modify(self, udm_obj, lo):  # type: (UdmObject, LoType) -> None
        self.create_mail_domain(lo)
        self.password = self.password or None

        removed_schools = set(udm_obj["school"]) - set(self.schools)
        if removed_schools:
            # change self.schools back, so schools can be removed by remove_from_school()
            self.schools = udm_obj["school"]
        for removed_school in removed_schools:
            self.logger.info("Removing %r from school %r...", self, removed_school)
            if not self.remove_from_school(removed_school, lo):
                self.logger.error("Error removing %r from school %r.", self, removed_school)
                return

        # remove SchoolClasses or WorkGroups the user is not part of anymore
        # ignore all others (global groups and $OU-groups)
        mandatory_groups = self.groups_used(lo)
        for group_dn in [dn for dn in udm_obj["groups"] if dn not in mandatory_groups]:
            try:
                school_class = SchoolClass.from_dn(group_dn, None, lo)
                classes = self.school_classes.get(school_class.school, [])
                if school_class.name not in classes and school_class.get_relative_name() not in classes:
                    self.logger.debug("Removing %r from SchoolClass %r.", self, group_dn)
                    udm_obj["groups"].remove(group_dn)
            # it's not a class but could be a workgroup
            except noObject:
                try:
                    workgroup = WorkGroup.from_dn(group_dn, None, lo)
                    workgroups = self.workgroups.get(workgroup.school, [])
                    if (
                        workgroup.name not in workgroups
                        and workgroup.get_relative_name() not in workgroups
                    ):
                        self.logger.debug("Removing %r from WorkGroup %r.", self, group_dn)
                        udm_obj["groups"].remove(group_dn)
                except noObject:
                    continue

        # make sure user is in all mandatory groups and school classes
        current_groups = {grp_dn.lower() for grp_dn in udm_obj["groups"]}
        groups_to_add = [dn for dn in mandatory_groups if dn.lower() not in current_groups]
        # [dn for dn in mandatory_groups if dn.lower() not in current_groups]
        if groups_to_add:
            self.logger.debug("Adding %r to groups %r.", self, groups_to_add)
            udm_obj["groups"].extend(groups_to_add)
        if self.check_password_policies:
            udm_obj["overridePWHistory"] = "0"
            udm_obj["overridePWLength"] = "0"
        else:
            udm_obj["overridePWHistory"] = "1"
            udm_obj["overridePWLength"] = "1"
        return super(User, self).do_modify(udm_obj, lo)

    def do_school_change(self, udm_obj, lo, old_school):  # type: (UdmObject, LoType, str) -> None
        super(User, self).do_school_change(udm_obj, lo, old_school)
        school = self.school

        self.logger.info("User is part of the following groups: %r", udm_obj["groups"])
        self.remove_from_groups_of_school(old_school, lo)
        self._udm_obj_searched = False
        self.school_classes.pop(old_school, None)
        self.workgroups.pop(old_school, None)
        udm_obj = self.get_udm_object(lo)
        udm_obj["primaryGroup"] = self.primary_group_dn(lo)
        groups = set(udm_obj["groups"])
        at_least_groups = set(self.groups_used(lo))
        if (groups | at_least_groups) != groups:
            udm_obj["groups"] = list(groups | at_least_groups)
        subdir = self.get_roleshare_home_subdir()
        udm_obj["unixhome"] = "/home/" + os.path.join(subdir, self.name)
        samba_home = self.get_samba_home_path(lo)
        if samba_home:
            udm_obj["sambahome"] = samba_home
        profile_path = self.get_profile_path(lo)
        if profile_path:
            udm_obj["profilepath"] = profile_path
        home_drive = self.get_samba_home_drive()
        if home_drive is not None:
            udm_obj["homedrive"] = home_drive
        script_path = self.get_samba_netlogon_script_path()
        if script_path is not None:
            udm_obj["scriptpath"] = script_path
        if udm_obj["departmentNumber"] == [old_school]:
            udm_obj["departmentNumber"] = [school]
        if school not in udm_obj["school"]:
            udm_obj["school"].append(school)
        if old_school in udm_obj["school"]:
            udm_obj["school"].remove(old_school)
        udm_obj.modify(ignore_license=True)

    def _alter_udm_obj(self, udm_obj):  # type: (UdmObject) -> None
        if self.email is not None:
            udm_obj["e-mail"] = self.email
        udm_obj["departmentNumber"] = [self.school]
        return super(User, self)._alter_udm_obj(udm_obj)

    def get_mail_domain(self):  # type: () -> MailDomain
        if self.email:
            domain_name = self.email.split("@")[-1]
            return MailDomain.cache(domain_name)

    def create_mail_domain(self, lo):  # type: (LoType) -> None
        mail_domain = self.get_mail_domain()
        if mail_domain is not None and not mail_domain.exists(lo):
            if self.shall_create_mail_domain():
                mail_domain.create(lo)
            else:
                self.logger.warning("Not allowed to create %r.", mail_domain)

    def set_default_options(self, udm_obj):  # type: (UdmObject) -> None
        for option in self.get_default_options():
            if option not in udm_obj.options:
                udm_obj.options.append(option)

    @classmethod
    def get_default_options(cls):  # type: () -> Set[str]
        options = set()
        # u-s-import uses multiple inheritance, we have to cover all parents
        for kls in cls.__bases__:  # type: "User"
            try:
                options.update(kls.get_default_options())
            except AttributeError:
                pass
        options.update(cls.default_options)
        return options

    def get_specific_groups(self, lo):  # type: (LoType) -> List[str]
        groups = self.get_domain_users_groups()
        for school_class in self.get_school_class_objs():
            groups.append(self.get_class_dn(school_class.name, school_class.school, lo))
        for workgroup in self.get_workgroup_objs():
            groups.append(self.get_workgroup_dn(workgroup.name, workgroup.school, lo))
        return groups

    def validate(
        self, lo, validate_unlikely_changes=False, check_name=True
    ):  # type: (LoType, Optional[bool]) -> None
        super(User, self).validate(
            lo, validate_unlikely_changes=validate_unlikely_changes, check_name=check_name
        )
        try:
            udm_obj = self.get_udm_object(lo)
        except UnknownModel:
            udm_obj = None
        except WrongModel as exc:
            udm_obj = None
            self.add_error(
                "name",
                _(
                    "It is not supported to change the role of a user. %(old_role)s %(name)s cannot "
                    "become a %(new_role)s."
                )
                % {
                    "old_role": exc.model.type_name,
                    "name": self.name,
                    "new_role": self.type_name,
                },
            )
        if udm_obj:
            original_class = self.get_class_for_udm_obj(udm_obj, self.school)
            if original_class is not self.__class__:
                self.add_error(
                    "name",
                    _(
                        "It is not supported to change the role of a user. %(old_role)s %(name)s cannot"
                        " become a %(new_role)s."
                    )
                    % {
                        "old_role": original_class.type_name,
                        "name": self.name,
                        "new_role": self.type_name,
                    },
                )
        if self.email:
            if self.get_first_udm_obj(
                lo,
                filter_format("&(!(uid=%s))(mailPrimaryAddress=%s)", (self.name, self.email)),
            ):
                self.add_error(
                    "email",
                    _(
                        "The email address is already taken by another user. Please change the email "
                        "address."
                    ),
                )
            # mail_domain = self.get_mail_domain(lo)
            # if not mail_domain.exists(lo) and not self.shall_create_mail_domain():
            # 	self.add_error(
            # 	'email',
            # 	_('The mail domain is unknown. Please change the email address or create the mail \
            # 	   domain "%s" using the Univention Directory Manager.') % mail_domain.name)

        if not isinstance(self.school_classes, Mapping):
            self.add_error(
                "school_classes",
                _("Type of 'school_classes' is {type!r}, but must be dictionary.").format(
                    type=type(self.school_classes)
                ),
            )

        # verify user is (or will be) in all schools of its school_classes
        for school, _classes in iteritems(self.school_classes):
            if school.lower() not in (s.lower() for s in self.schools + [self.school]):
                self.add_error(
                    "school_classes",
                    _(
                        "School {school!r} in 'school_classes' is missing in the users 'school(s)' "
                        "attribute."
                    ).format(school=school),
                )
        # check syntax of all class names
        for school, classes in iteritems(self.school_classes):
            for class_name in classes:
                try:
                    syntax.gid.parse(class_name)
                except valueError as exc:
                    self.add_error("school_classes", str(exc))

        if not isinstance(self.workgroups, Mapping):
            self.add_error(
                "workgroups",
                _("Type of 'workgroups' is {type!r}, but must be dictionary.").format(
                    type=type(self.workgroups)
                ),
            )

        # verify user is (or will be) in all schools of its work groups
        for school, _workgroups in iteritems(self.workgroups):
            if school.lower() not in (s.lower() for s in self.schools + [self.school]):
                self.add_error(
                    "workgroups",
                    _(
                        "School {school!r} in 'workgroups' is missing in the users 'school(s)' "
                        "attributes."
                    ).format(school=school),
                )
        # check syntax of all work group names
        for school, workgroups in iteritems(self.workgroups):
            for work_group_name in workgroups:
                try:
                    syntax.gid.parse(work_group_name)
                except valueError as exc:
                    self.add_error("workgroups", str(exc))

    def remove_from_school(self, school, lo):  # type: (str, LoType) -> bool
        if not self.exists(lo):
            self.logger.warning("User does not exists, not going to remove.")
            return False
        try:
            (self.schools or [school]).remove(school)
        except ValueError:
            self.logger.warning("User is not part of school %r. Not removing.", school)
            return False
        if not self.schools:
            self.logger.warning("User %r not part of any school, removing it.", self)
            return self.remove(lo)
        if self.school == school:
            if not self.change_school(self.schools[0], lo):
                return False
        else:
            self.remove_from_groups_of_school(school, lo)
        self.school_classes.pop(school, None)
        self.workgroups.pop(school, None)
        return True

    def remove_from_groups_of_school(self, school, lo):  # type: (str, LoType) -> None

        for cls in (SchoolClass, WorkGroup, SchoolGroup):
            for group in cls.get_all(lo, school, filter_format("uniqueMember=%s", (self.dn,))):
                try:
                    group.users.remove(self.dn)
                except ValueError:
                    pass
                else:
                    self.logger.info(
                        "Removing %r from group %r of school %r.",
                        self.dn,
                        group.dn,
                        school,
                    )
                    group.modify(lo)

        if self.is_administrator(lo):
            # Bug 54368
            # remove_from_groups_of_school() doesn't remove school admins from admins-OU group
            admin_group_dns = self.get_school_admin_groups([school])
            for dn in admin_group_dns:
                try:
                    admin_group = BasicGroup.from_dn(dn, school, lo)
                except NoObject:
                    continue

                try:
                    admin_group.users.remove(self.dn)
                except ValueError:
                    pass
                else:
                    self.logger.info(
                        "Removing %r from group %r of school %r.",
                        self.dn,
                        admin_group.dn,
                        school,
                    )
                    admin_group.modify(lo)

    def get_group_dn(self, group_name, school):  # type: (str, str) -> str
        return Group.cache(group_name, school).dn

    def get_class_dn(self, class_name, school, lo):  # type: (str, str, LoType) -> str
        # Bug #32337: check if the class exists without OU prefix
        # if it does not exist the class name with OU prefix is used
        school_class = SchoolClass.cache(class_name, school)
        if school_class.get_relative_name() == school_class.name:
            if not school_class.exists(lo):
                class_name = "%s-%s" % (school, class_name)
                school_class = SchoolClass.cache(class_name, school)
        return school_class.dn

    def get_workgroup_dn(self, workgroup_name, school, lo):  # type: (str, str, LoType) -> str
        school_workgroup = WorkGroup.cache(workgroup_name, school)
        if school_workgroup.get_relative_name() == school_workgroup.name:
            wg = WorkGroup.cache(workgroup_name, school)
            if not wg.exists(lo):
                workgroup_name = "%s-%s" % (school, workgroup_name)
                school_workgroup = WorkGroup.cache(workgroup_name, school)
        return school_workgroup.dn

    def primary_group_dn(self, lo):  # type: (LoType) -> str
        dn = self.get_group_dn("Domain Users %s" % self.school, self.school)
        return self.get_or_create_group_udm_object(dn, lo).dn

    def get_domain_users_groups(self, schools=None):  # type: (Optional[List[str]]) -> List[str]
        return [
            self.get_group_dn("Domain Users %s" % school, school) for school in (schools or self.schools)
        ]

    def get_students_groups(self, schools=None):  # type: (Optional[List[str]]) -> List[str]
        prefix = ucr.get("ucsschool/ldap/default/groupprefix/pupils", "schueler-")
        return [
            self.get_group_dn("%s%s" % (prefix, school), school) for school in (schools or self.schools)
        ]

    def get_teachers_groups(self, schools=None):  # type: (Optional[List[str]]) -> List[str]
        prefix = ucr.get("ucsschool/ldap/default/groupprefix/teachers", "lehrer-")
        return [
            self.get_group_dn("%s%s" % (prefix, school), school) for school in (schools or self.schools)
        ]

    def get_staff_groups(self, schools=None):  # type: (Optional[List[str]]) -> List[str]
        prefix = ucr.get("ucsschool/ldap/default/groupprefix/staff", "mitarbeiter-")
        return [
            self.get_group_dn("%s%s" % (prefix, school), school) for school in (schools or self.schools)
        ]

    def get_school_admin_groups(self, schools=None):  # type: (Optional[List[str]]) -> List[str]
        prefix = self.get_search_base("DEMOSCHOOL").group_prefix_admins
        ldap_base = ucr.get("ldap/base")
        return [
            "cn=%s%s,cn=ouadmins,cn=groups,%s"
            % (escape_dn_chars(prefix), escape_dn_chars(school.lower()), ldap_base)
            for school in (schools or self.schools)
        ]

    def groups_used(self, lo):  # type: (LoType) -> List[str]
        group_dns = self.get_specific_groups(lo)

        for group_dn in group_dns:
            self.get_or_create_group_udm_object(group_dn, lo)

        return group_dns

    @classmethod
    def get_or_create_group_udm_object(cls, group_dn, lo, fresh=False):
        # type: (str, LoType, Optional[bool]) -> Group
        """
        In the case of work groups, this function assumes that they already exists.

        :raises RuntimeError: if a work group does not exist.
        """
        name = cls.get_name_from_dn(group_dn)
        school = cls.get_school_from_dn(group_dn)
        if school is None and name.startswith(cls.get_search_base(school).group_prefix_admins):
            # Should only happen for ouadmin groups
            group = BasicGroup.from_dn(group_dn, None, lo)
        elif Group.is_school_class(school, group_dn):
            group = SchoolClass.cache(name, school)
        elif Group.is_school_workgroup(school, group_dn):
            group = WorkGroup.cache(name, school)
            if group.exists(lo):
                return group
            # this should not happen
            raise RuntimeError("Work group '%s' does not exist, please create it first." % group_dn)
        else:
            group = Group.cache(name, school)
        if fresh:
            group._udm_obj_searched = False
        group.create(lo)
        return group

    def is_active(self):  # type: () -> bool
        return self.disabled != "1"

    def to_dict(self):  # type: () -> Dict[str, Any]
        ret = super(User, self).to_dict()
        display_name = []
        if self.firstname:
            display_name.append(self.firstname)
        if self.lastname:
            display_name.append(self.lastname)
        ret["display_name"] = " ".join(display_name)
        school_classes = {}
        for school_class in self.get_school_class_objs():
            school_classes.setdefault(school_class.school, []).append(school_class.name)
        ret["school_classes"] = school_classes
        workgroups = {}
        for workgroup in self.get_workgroup_objs():
            workgroups.setdefault(workgroup.school, []).append(workgroup.name)
        ret["workgroups"] = workgroups
        ret["type_name"] = self.type_name
        ret["type"] = self.__class__.__name__
        ret["type"] = ret["type"][0].lower() + ret["type"][1:]
        return ret

    def get_school_class_objs(self):  # type: () -> List[SchoolClass]
        ret = []
        for school, classes in iteritems(self.school_classes):
            for school_class in classes:
                ret.append(SchoolClass.cache(school_class, school))
        return ret

    def get_workgroup_objs(self):  # type: () -> List[WorkGroup]
        ret = []
        for school, workgroups in iteritems(self.workgroups):
            for workgroup in workgroups:
                ret.append(WorkGroup.cache(workgroup, school))
        return ret

    @classmethod
    def get_school_classes(cls, udm_obj, obj):  # type: (UdmObject, "User") -> Dict[str, List[str]]
        school_classes = {}
        for group in udm_obj["groups"]:
            for school in obj.schools:
                if Group.is_school_class(school, group):
                    school_class_name = cls.get_name_from_dn(group)
                    school_classes.setdefault(school, []).append(school_class_name)
        return school_classes

    @classmethod
    def get_workgroups(cls, udm_obj, obj):  # type: (UdmObject, "User") -> Dict[str, List[str]]
        workgroups = {}
        for group in udm_obj["groups"]:
            for school in obj.schools:
                if Group.is_school_workgroup(school, group):
                    workgroup_name = cls.get_name_from_dn(group)
                    workgroups.setdefault(school, []).append(workgroup_name)
        return workgroups

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).users

    @classmethod
    def lookup(cls, lo, school, filter_s="", superordinate=None):
        # type: (LoType, str, Optional[UldapFilter], Optional[SuperOrdinateType]) -> List[UdmObject]
        filter_object_type = conjunction(
            "&",
            [
                parse(cls.type_filter),
                parse(filter_format("ucsschoolSchool=%s", [school])),
            ],
        )
        if filter_s:
            filter_object_type = conjunction("&", [filter_object_type, parse(filter_s)])
        objects = udm_modules.lookup(
            cls._meta.udm_module,
            None,
            lo,
            filter="{}".format(filter_object_type),
            scope="sub",
            superordinate=superordinate,
        )
        objects.extend(
            obj
            for obj in super(User, cls).lookup(lo, school, filter_s, superordinate=superordinate)
            if not any(obj.dn == x.dn for x in objects)
        )
        return objects

    class Meta:
        udm_module = "users/user"
        name_is_unique = True
        allow_school_change = False


class Student(User):
    type_name = _("Student")
    type_filter = "(&(objectClass=ucsschoolStudent)(!(objectClass=ucsschoolExam)))"
    roles = [role_pupil]
    default_options = ("ucsschoolStudent",)
    default_roles = [role_student]

    def do_school_change(self, udm_obj, lo, old_school):  # type: (UdmObject, LoType, str) -> None
        try:
            exam_user = ExamStudent.from_student_dn(lo, old_school, self.old_dn)
        except noObject as exc:
            self.logger.info("No exam user for %r found: %s", self.old_dn, exc)
        else:
            self.logger.info("Removing exam user %r", exam_user.dn)
            exam_user.remove(lo)

        super(Student, self).do_school_change(udm_obj, lo, old_school)

    @classmethod
    def get_container(cls, school):  # type: (str) -> UdmObject
        return cls.get_search_base(school).students

    @classmethod
    def get_exam_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).examUsers

    def get_specific_groups(self, lo):  # type: (LoType) -> List[str]
        groups = super(Student, self).get_specific_groups(lo)
        groups.extend(self.get_students_groups())
        return groups


class Teacher(User):
    type_name = _("Teacher")
    type_filter = "(&(objectClass=ucsschoolTeacher)(!(objectClass=ucsschoolStaff)))"
    roles = [role_teacher]
    default_roles = [role_teacher]
    default_options = ("ucsschoolTeacher",)

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).teachers

    def get_specific_groups(self, lo):  # type: (LoType) -> List[str]
        groups = super(Teacher, self).get_specific_groups(lo)
        groups.extend(self.get_teachers_groups())
        return groups


class SchoolAdmin(User):
    type_name = _("School Administrator")
    type_filter = "(objectClass=ucsschoolAdministrator)"
    roles = [role_school_admin]
    default_roles = [role_school_admin]
    default_options = ("ucsschoolAdministrator",)

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).admins

    def get_specific_groups(self, lo):  # type: (LoType) -> List[str]
        groups = super(SchoolAdmin, self).get_specific_groups(lo)
        groups.extend(self.get_school_admin_groups())
        return groups


class Staff(User):
    school_classes = None
    type_name = _("Staff")
    roles = [role_staff]
    default_roles = [role_staff]
    type_filter = "(&(!(objectClass=ucsschoolTeacher))(objectClass=ucsschoolStaff))"
    default_options = ("ucsschoolStaff",)

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).staff

    def get_samba_home_path(self, lo):  # type: (LoType) -> None
        """Do not set sambaHomePath for staff users."""
        return

    def get_samba_home_drive(self):  # type: () -> None
        """Do not set sambaHomeDrive for staff users."""
        return

    def get_samba_netlogon_script_path(self):  # type: () -> None
        """Do not set sambaLogonScript for staff users."""
        return

    def get_profile_path(self, lo):  # type: (LoType) -> None
        """Do not set sambaProfilePath for staff users."""
        return

    def get_school_class_objs(self):  # type: () -> List[SchoolClass]
        return []

    @classmethod
    def get_school_classes(cls, udm_obj, obj):  # type: (UdmObject, "Staff") -> Dict[str, List[str]]
        return {}

    def get_specific_groups(self, lo):  # type: (LoType) -> List[str]
        groups = super(Staff, self).get_specific_groups(lo)
        groups.extend(self.get_staff_groups())
        return groups


class TeachersAndStaff(Teacher):
    type_name = _("Teacher and Staff")
    type_filter = "(&(objectClass=ucsschoolStaff)(objectClass=ucsschoolTeacher))"
    roles = [role_teacher, role_staff]
    default_roles = [role_teacher, role_staff]
    default_options = ("ucsschoolStaff",)

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).teachersAndStaff

    def get_specific_groups(self, lo):  # type: (LoType) -> List[str]
        groups = super(TeachersAndStaff, self).get_specific_groups(lo)
        groups.extend(self.get_staff_groups())
        return groups


class ExamStudent(Student):
    type_name = _("Exam student")
    type_filter = "(&(objectClass=ucsschoolStudent)(objectClass=ucsschoolExam))"
    default_roles = [role_exam_user]
    default_options = ("ucsschoolExam",)

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).examUsers

    @classmethod
    def from_student_dn(cls, lo, school, dn):  # type: (LoType, str, str) -> "ExamStudent"
        examUserPrefix = ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-")
        dn = "uid=%s%s,%s" % (
            escape_dn_chars(examUserPrefix),
            escape_dn_chars(explode_rdn(dn, True)[0]),
            cls.get_container(school),
        )
        return cls.from_dn(dn, school, lo)
