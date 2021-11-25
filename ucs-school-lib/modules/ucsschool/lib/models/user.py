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

import copy
import os.path
from collections.abc import Mapping
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union

from ldap.dn import escape_dn_chars, explode_dn
from ldap.filter import escape_filter_chars, filter_format
from six import iteritems

import univention.admin.syntax as syntax
from udm_rest_client import UDM, UdmObject
from univention.admin.filter import conjunction, parse
from univention.admin.uexceptions import noObject, valueError

from ..roles import (
    context_type_school,
    create_ucsschool_role_string,
    role_exam_user,
    role_pupil,
    role_school_admin,
    role_staff,
    role_student,
    role_teacher,
)
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
)
from .base import RoleSupportMixin, UCSSchoolHelperAbstractClass, UnknownModel, WrongModel
from .computer import AnyComputer
from .group import BasicGroup, Group, SchoolClass, SchoolGroup, WorkGroup
from .misc import MailDomain
from .school import School
from .utils import _, create_passwd, env_or_ucr, ucr

SuperOrdinateType = Union[str, UdmObject]
unicode_s = str  # py3


class User(RoleSupportMixin, UCSSchoolHelperAbstractClass):
    name: str = Username(_("Username"), aka=["Username", "Benutzername"])
    schools: List[str] = Schools(_("Schools"))
    firstname: str = Firstname(
        _("First name"), aka=["First name", "Vorname"], required=True, unlikely_to_change=True
    )
    lastname: str = Lastname(
        _("Last name"), aka=["Last name", "Nachname"], required=True, unlikely_to_change=True
    )
    birthday: str = Birthday(_("Birthday"), aka=["Birthday", "Geburtstag"], unlikely_to_change=True)
    expiration_date: str = UserExpirationDate(
        _("Expiration date"), aka=["Expiration date", "Ablaufdatum"]
    )
    email: str = Email(_("Email"), aka=["Email", "E-Mail"], unlikely_to_change=True)
    password: Optional[str] = Password(_("Password"), aka=["Password", "Passwort"])
    disabled: bool = Disabled(_("Disabled"), aka=["Disabled", "Gesperrt"])
    school_classes: Dict[str, List[str]] = SchoolClassesAttribute(_("Class"), aka=["Class", "Klasse"])

    type_name: str = None
    type_filter = (
        "(|(objectClass=ucsschoolTeacher)(objectClass=ucsschoolStaff)(objectClass=ucsschoolStudent))"
    )

    _profile_path_cache: Dict[str, str] = {}
    _samba_home_path_cache: Dict[str, str] = {}
    # _samba_home_path_cache is invalidated in School.invalidate_cache()

    roles: List[str] = []
    default_roles: List[str] = []
    default_options: Tuple[str] = ()

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        if self.school_classes is None:
            self.school_classes = {}  # set a dict for Staff
        if self.school and not self.schools:
            self.schools.append(self.school)

    @classmethod
    def shall_create_mail_domain(cls) -> bool:
        return ucr.is_true("ucsschool/import/generate/mail/domain")

    def get_roleshare_home_subdir(self) -> str:
        from ucsschool.lib.roleshares import roleshare_home_subdir

        return roleshare_home_subdir(self.school, self.roles, ucr)

    def get_samba_home_drive(self) -> str:
        return ucr.get("ucsschool/import/set/homedrive")

    def get_samba_netlogon_script_path(self) -> str:
        return ucr.get("ucsschool/import/set/netlogon/script/path")

    async def get_samba_home_path(self, lo: UDM) -> str:
        school = School.cache(self.school)
        # if defined then use UCR value
        if ucr_variable := ucr.get("ucsschool/import/set/sambahome"):
            samba_home_path = r"\\%s" % ucr_variable.strip("\\")
        elif ucr.is_true("ucsschool/singlemaster", False):
            # in single server environments the master is always the fileserver
            samba_home_path = r"\\%s" % ucr.get("ldap/server/name").split(".")[0]
        # if there's a cached result then use it
        elif school.dn not in self._samba_home_path_cache:
            samba_home_path = None
            # get windows home server from OU object
            school = await self.get_school_obj(lo)
            home_share_file_server = school.home_share_file_server
            if home_share_file_server:
                samba_home_path = r"\\%s" % self.get_name_from_dn(home_share_file_server)
            self._samba_home_path_cache[school.dn] = samba_home_path
        else:
            samba_home_path = self._samba_home_path_cache[school.dn]
        if samba_home_path is not None:
            return r"%s\%s" % (samba_home_path, self.name)

    async def get_profile_path(self, lo: UDM) -> str:
        if ucr_variable := ucr.get("ucsschool/import/set/serverprofile/path"):
            return ucr_variable
        school = School.cache(self.school)
        if school.dn not in self._profile_path_cache:
            profile_path = r"%s\%%USERNAME%%\windows-profiles\default"
            for computer in await AnyComputer.get_all(
                lo, self.school, "univentionService=Windows Profile Server"
            ):
                profile_path = profile_path % (r"\\%s" % computer.name)
                break
            else:
                profile_path = profile_path % "%LOGONSERVER%"
            self._profile_path_cache[school.dn] = profile_path
        return self._profile_path_cache[school.dn]

    async def is_student(self, lo: UDM) -> bool:
        return await self.__check_object_class(lo, "ucsschoolStudent", self._legacy_is_student)

    async def is_exam_student(self, lo: UDM) -> bool:
        return await self.__check_object_class(lo, "ucsschoolExam", self._legacy_is_exam_student)

    async def is_teacher(self, lo: UDM) -> bool:
        return await self.__check_object_class(lo, "ucsschoolTeacher", self._legacy_is_teacher)

    async def is_staff(self, lo: UDM) -> bool:
        return await self.__check_object_class(lo, "ucsschoolStaff", self._legacy_is_staff)

    async def is_administrator(self, lo: UDM) -> bool:
        return await self.__check_object_class(
            lo, "ucsschoolAdministrator", self._legacy_is_admininstrator
        )

    @classmethod
    def _legacy_is_student(cls, school: str, dn: str) -> bool:
        cls.logger.warning("Using deprecated method is_student()")
        return dn.endswith(cls.get_search_base(school).students)

    @classmethod
    def _legacy_is_exam_student(cls, school: str, dn: str) -> bool:
        cls.logger.warning("Using deprecated method is_exam_student()")
        return dn.endswith(cls.get_search_base(school).examUsers)

    @classmethod
    def _legacy_is_teacher(cls, school: str, dn: str) -> bool:
        cls.logger.warning("Using deprecated method is_teacher()")
        search_base = cls.get_search_base(school)
        return (
            dn.endswith(search_base.teachers)
            or dn.endswith(search_base.teachersAndStaff)
            or dn.endswith(search_base.admins)
        )

    @classmethod
    def _legacy_is_staff(cls, school: str, dn: str) -> bool:
        cls.logger.warning("Using deprecated method is_staff()")
        search_base = cls.get_search_base(school)
        return dn.endswith(search_base.staff) or dn.endswith(search_base.teachersAndStaff)

    @classmethod
    def _legacy_is_admininstrator(cls, school: str, dn: str) -> bool:
        cls.logger.warning("Using deprecated method is_admininstrator()")
        return dn.endswith(cls.get_search_base(school).admins)

    async def __check_object_class(
        self, lo: UDM, object_class: str, fallback: Callable[[str, str], bool]
    ) -> bool:
        obj = await self.get_udm_object(lo)
        if not obj:
            raise noObject("Could not read %r" % (self.dn,))
        if "ucsschoolSchool" in obj.oldattr:  # TODO: HTTP UdmObject does not have "oldattr"!
            return object_class in obj.oldattr.get("objectClass", [])  # TODO: see line above
        return fallback(self.school, self.dn)

    @classmethod
    async def get_class_for_udm_obj(cls, udm_obj: UdmObject, school: str) -> Union[None, Type["User"]]:
        ocs = set(key for key, val in udm_obj.options.items() if val is True)
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
    async def from_udm_obj(cls, udm_obj: UdmObject, school: str, lo: UDM) -> "User":
        # cls.logger.debug("**** udm_obj=%r school=%r", udm_obj, school)
        obj = await super(User, cls).from_udm_obj(udm_obj, school, lo)
        obj.password = None
        obj.school_classes = await cls.get_school_classes(udm_obj, obj)
        return obj

    async def do_create(self, udm_obj: UdmObject, lo: UDM) -> None:
        if not self.schools:
            self.schools = [self.school]
        await self.set_default_options(udm_obj)
        await self.create_mail_domain(lo)
        password_created = False
        if not self.password:
            self.logger.debug("No password given. Generating random one")
            self.password = create_passwd(dn=self.dn)
            password_created = True
        udm_obj.props.primaryGroup = await self.primary_group_dn(lo)
        udm_obj.props.groups = await self.groups_used(lo)
        subdir = self.get_roleshare_home_subdir()
        udm_obj.props.unixhome = "/home/" + os.path.join(subdir, self.name)
        udm_obj.props.overridePWHistory = True
        udm_obj.props.overridePWLength = True
        if self.disabled is None:
            udm_obj.props.disabled = False
        if hasattr(udm_obj.props, "mailbox"):
            udm_obj.props.mailbox = "/var/spool/%s/" % self.name
        if samba_home := await self.get_samba_home_path(lo):
            udm_obj.props.sambahome = samba_home
        if profile_path := await self.get_profile_path(lo):
            udm_obj.props.profilepath = profile_path
        if home_drive := self.get_samba_home_drive():
            udm_obj.props.homedrive = home_drive
        if script_path := self.get_samba_netlogon_script_path():
            udm_obj.props.scriptpath = script_path
        success = await super(User, self).do_create(udm_obj, lo)
        if password_created:
            # dont' show password in post_hooks
            # (it has already been saved to LDAP in super().do_create() above)
            self.password = ""
        return success

    async def do_modify(self, udm_obj: UdmObject, lo: UDM) -> None:
        await self.create_mail_domain(lo)
        self.password = self.password or None

        removed_schools = set(udm_obj.props.school) - set(self.schools)
        if removed_schools:
            # change self.schools back, so schools can be removed by remove_from_school()
            self.schools = udm_obj.props.school
        for removed_school in removed_schools:
            self.logger.info("Removing %r from school %r...", self, removed_school)
            if not await self.remove_from_school(removed_school, lo):
                self.logger.error("Error removing %r from school %r.", self, removed_school)
                return

        # remove SchoolClasses the user is not part of anymore
        # ignore all others (global groups, $OU-groups and workgroups)
        mandatory_groups = await self.groups_used(lo)
        for group_dn in [dn for dn in udm_obj.props.groups if dn not in mandatory_groups]:
            try:
                school_class = await SchoolClass.from_dn(group_dn, None, lo)
            except noObject:
                continue
            classes = self.school_classes.get(school_class.school, [])
            if school_class.name not in classes and school_class.get_relative_name() not in classes:
                self.logger.debug("Removing %r from SchoolClass %r.", self, group_dn)
                udm_obj.props.groups.remove(group_dn)

        # make sure user is in all mandatory groups and school classes
        current_groups = set(grp_dn.lower() for grp_dn in udm_obj.props.groups)
        groups_to_add = [dn for dn in mandatory_groups if dn.lower() not in current_groups]
        if groups_to_add:
            self.logger.debug("Adding %r to groups %r.", self, groups_to_add)
            udm_obj.props.groups.extend(groups_to_add)
        return await super(User, self).do_modify(udm_obj, lo)

    async def do_school_change(self, udm_obj, lo, old_school) -> None:
        await super(User, self).do_school_change(udm_obj, lo, old_school)
        school = self.school

        self.logger.info("User is part of the following groups: %r", udm_obj.props.groups)
        await self.remove_from_groups_of_school(old_school, lo)
        self._udm_obj_searched = False
        self.school_classes.pop(old_school, None)
        udm_obj = await self.get_udm_object(lo)
        udm_obj.props.primaryGroup = await self.primary_group_dn(lo)
        groups = set(udm_obj.props.groups)
        at_least_groups = set(await self.groups_used(lo))
        if (groups | at_least_groups) != groups:
            udm_obj.props.groups = list(groups | at_least_groups)
        subdir = self.get_roleshare_home_subdir()
        udm_obj.props.unixhome = "/home/" + os.path.join(subdir, self.name)
        if samba_home := await self.get_samba_home_path(lo):
            udm_obj.props.sambahome = samba_home
        if profile_path := await self.get_profile_path(lo):
            udm_obj.props.profilepath = profile_path
        if home_drive := self.get_samba_home_drive():
            udm_obj.props.homedrive = home_drive
        if script_path := self.get_samba_netlogon_script_path():
            udm_obj.props.scriptpath = script_path
        if udm_obj.props.departmentNumber == [old_school]:
            udm_obj.props.departmentNumber = [school]
        if school not in udm_obj.props.school:
            udm_obj.props.school.append(school)
        if old_school in udm_obj.props.school:
            udm_obj.props.school.remove(old_school)
        await udm_obj.save()

    async def _alter_udm_obj(self, udm_obj: UdmObject) -> None:
        if self.email is not None:
            setattr(udm_obj.props, "e-mail", [self.email])
        udm_obj.props.departmentNumber = [self.school]
        return await super(User, self)._alter_udm_obj(udm_obj)

    def get_mail_domain(self) -> MailDomain:
        if self.email:
            domain_name = self.email.split("@")[-1]
            return MailDomain.cache(domain_name)

    async def create_mail_domain(self, lo: UDM) -> None:
        mail_domain = self.get_mail_domain()
        if mail_domain is not None and not await mail_domain.exists(lo):
            if self.shall_create_mail_domain():
                await mail_domain.create(lo)
            else:
                self.logger.warning("Not allowed to create %r.", mail_domain)

    async def set_default_options(self, udm_obj: UdmObject) -> None:
        udm_obj.options.update(dict((opt, True) for opt in self.get_default_options()))

    @classmethod
    def get_default_options(cls) -> Set[str]:
        options = set()
        for kls in cls.__bases__:  # type: "User"
            # u-s-import uses multiple inheritance, we have to cover all parents
            try:
                options.update(kls.get_default_options())
            except AttributeError:
                pass
        options.update(cls.default_options)
        return options

    async def get_specific_groups(self, lo: UDM) -> List[str]:
        groups = self.get_domain_users_groups()
        for school_class in self.get_school_class_objs():
            groups.append(await self.get_class_dn(school_class.name, school_class.school, lo))
        return groups

    async def validate(self, lo: UDM, validate_unlikely_changes: bool = False) -> None:
        await super(User, self).validate(lo, validate_unlikely_changes)
        try:
            udm_obj = await self.get_udm_object(lo)
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
                % {"old_role": exc.model.type_name, "name": self.name, "new_role": self.type_name},
            )
        if udm_obj:
            original_class = await self.get_class_for_udm_obj(udm_obj, self.school)
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
            name, email = escape_filter_chars(self.name), escape_filter_chars(self.email)
            if await self.get_first_udm_obj(lo, "(&(!(uid=%s))(mailPrimaryAddress=%s))" % (name, email)):
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
        for school, classes in iteritems(self.school_classes):
            if school.lower() not in (s.lower() for s in self.schools + [self.school]):
                self.add_error(
                    "school_classes",
                    _(
                        "School {school!r} in 'school_classes' is missing in the users 'school(s)' "
                        "attributes."
                    ).format(school=school),
                )
        # check syntax of all class names
        for school, classes in iteritems(self.school_classes):
            for class_name in classes:
                try:
                    syntax.gid.parse(class_name)
                except valueError as exc:
                    self.add_error("school_classes", str(exc))

    async def remove_from_school(self, school: str, lo: UDM) -> bool:
        if not await self.exists(lo):
            self.logger.warning("User does not exists, not going to remove.")
            return False
        try:
            (self.schools or [school]).remove(school)
        except ValueError:
            self.logger.warning("User is not part of school %r. Not removing.", school)
            return False
        if not self.schools:
            self.logger.warning("User %r not part of any school, removing it.", self)
            return await self.remove(lo)
        if self.school == school:
            if not await self.change_school(self.schools[0], lo):
                return False
        else:
            await self.remove_from_groups_of_school(school, lo)
        self.school_classes.pop(school, None)
        return True

    async def remove_from_groups_of_school(self, school: str, lo: UDM) -> None:
        for cls in (SchoolClass, WorkGroup, SchoolGroup):
            for group in await cls.get_all(lo, school, filter_format("uniqueMember=%s", (self.dn,))):
                try:
                    group.users.remove(self.dn)
                except ValueError:
                    pass
                else:
                    self.logger.info(
                        "Removing %r from group %r of school %r.", self.dn, group.dn, school
                    )
                    await group.modify(lo)

    def get_group_dn(self, group_name: str, school: str) -> str:
        return Group.cache(group_name, school).dn

    async def get_class_dn(self, class_name: str, school: str, lo: UDM) -> str:
        # Bug #32337: check if the class exists without OU prefix
        # if it does not exist the class name with OU prefix is used
        school_class = SchoolClass.cache(class_name, school)
        if school_class.get_relative_name() == school_class.name:
            if not await school_class.exists(lo):
                class_name = "%s-%s" % (school, class_name)
                school_class = SchoolClass.cache(class_name, school)
        return school_class.dn

    async def primary_group_dn(self, lo: UDM) -> str:
        dn = self.get_group_dn("Domain Users %s" % self.school, self.school)
        return (await self.get_or_create_group_udm_object(dn, lo)).dn

    def get_domain_users_groups(self) -> List[str]:
        return [self.get_group_dn("Domain Users %s" % school, school) for school in self.schools]

    def get_students_groups(self) -> List[str]:
        prefix = ucr.get("ucsschool/ldap/default/groupprefix/pupils", "schueler-")
        return [self.get_group_dn("%s%s" % (prefix, school), school) for school in self.schools]

    def get_teachers_groups(self) -> List[str]:
        prefix = ucr.get("ucsschool/ldap/default/groupprefix/teachers", "lehrer-")
        return [self.get_group_dn("%s%s" % (prefix, school), school) for school in self.schools]

    def get_staff_groups(self) -> List[str]:
        prefix = ucr.get("ucsschool/ldap/default/groupprefix/staff", "mitarbeiter-")
        return [self.get_group_dn("%s%s" % (prefix, school), school) for school in self.schools]

    def get_school_admin_groups(self) -> List[str]:
        prefix = self.get_search_base(self.school).group_prefix_admins
        ldap_base = env_or_ucr("ldap/base")
        return [
            "cn=%s%s,cn=ouadmins,cn=groups,%s" % (prefix, school.lower(), ldap_base)
            for school in self.schools
        ]

    async def groups_used(self, lo: UDM) -> List[str]:
        group_dns = await self.get_specific_groups(lo)

        for group_dn in group_dns:
            await self.get_or_create_group_udm_object(group_dn, lo)

        return group_dns

    @classmethod
    async def get_or_create_group_udm_object(cls, group_dn: str, lo: UDM, fresh: bool = False) -> Group:
        name = cls.get_name_from_dn(group_dn)
        school = cls.get_school_from_dn(group_dn)
        if school is None and name.startswith(cls.get_search_base(school).group_prefix_admins):
            # Should only happen for ouadmin groups
            group = await BasicGroup.from_dn(group_dn, None, lo)
        elif Group.is_school_class(school, group_dn):
            group = SchoolClass.cache(name, school)
        else:
            group = Group.cache(name, school)
        if fresh:
            group._udm_obj_searched = False
        await group.create(lo)
        return group

    def is_active(self) -> bool:
        return self.disabled != "1"

    def to_dict(self) -> Dict[str, Any]:
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
        ret["type_name"] = self.type_name
        ret["type"] = self.__class__.__name__
        ret["type"] = ret["type"][0].lower() + ret["type"][1:]
        return ret

    def get_school_class_objs(self) -> List[SchoolClass]:
        ret = []
        for school, classes in iteritems(self.school_classes):
            for school_class in classes:
                ret.append(SchoolClass.cache(school_class, school))
        return ret

    @classmethod
    async def get_school_classes(cls, udm_obj: UdmObject, obj: "User") -> Dict[str, List[str]]:
        school_classes = {}
        for group in udm_obj.props.groups:
            for school in obj.schools:
                if Group.is_school_class(school, group):
                    school_class_name = cls.get_name_from_dn(group)
                    school_classes.setdefault(school, []).append(school_class_name)
        return school_classes

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).users

    @classmethod
    async def lookup(
        cls, lo: UDM, school: str, filter_s: str = "", superordinate: SuperOrdinateType = None
    ) -> List[UdmObject]:
        # cls.logger.debug("**** school=%r filter_s=%r", school, filter_s)
        filter_object_type = conjunction(
            "&", [parse(cls.type_filter), parse(filter_format("ucsschoolSchool=%s", [school]))]
        )
        if filter_s:
            filter_object_type = conjunction("&", [filter_object_type, parse(filter_s)])
        objects = [
            o
            async for o in lo.get(cls._meta.udm_module).search(
                filter_s=unicode_s(filter_object_type), scope="sub"
            )
        ]
        # objects = await udm_modules.lookup(cls._meta.udm_module, None, lo, filter=unicode_s(filter_object_type), scope='sub', superordinate=superordinate)
        # legacy objects (find by position in LDAP) support:
        more_objs = await super(User, cls).lookup(lo, school, filter_s, superordinate=superordinate)
        dns = {o.dn for o in objects}
        objects.extend(obj for obj in more_objs if obj.dn not in dns)
        return objects

    class Meta:
        udm_module = "users/user"
        name_is_unique = True
        allow_school_change = False
        ldap_name_part = "uid"


class Student(User):
    type_name = _("Student")
    type_filter = "(&(objectClass=ucsschoolStudent)(!(objectClass=ucsschoolExam)))"
    roles = [role_pupil]
    default_options = ("ucsschoolStudent",)
    default_roles = [role_student]

    async def do_school_change(self, udm_obj: UdmObject, lo: UDM, old_school: str) -> None:
        try:
            exam_user = await ExamStudent.from_student_dn(lo, old_school, self.old_dn)
        except noObject as exc:
            self.logger.info("No exam user for %r found: %s", self.old_dn, exc)
        else:
            self.logger.info("Removing exam user %r", exam_user.dn)
            await exam_user.remove(lo)

        await super(Student, self).do_school_change(udm_obj, lo, old_school)

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).students

    @classmethod
    def get_exam_container(cls, school: str) -> str:
        return cls.get_search_base(school).examUsers

    async def get_specific_groups(self, lo: UDM) -> List[str]:
        groups = await super(Student, self).get_specific_groups(lo)
        groups.extend(self.get_students_groups())
        return groups


class Teacher(User):
    type_name = _("Teacher")
    type_filter = "(&(objectClass=ucsschoolTeacher)(!(objectClass=ucsschoolStaff)))"
    roles = [role_teacher]
    default_roles = [role_teacher]
    default_options = ("ucsschoolTeacher",)

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).teachers

    async def get_specific_groups(self, lo: UDM) -> List[str]:
        groups = await super(Teacher, self).get_specific_groups(lo)
        groups.extend(self.get_teachers_groups())
        return groups


class SchoolAdmin(User):
    type_name = _("School Administrator")
    type_filter = "(objectClass=ucsschoolAdministrator)"
    roles = [role_school_admin]
    default_roles = [role_school_admin]
    default_options = ("ucsschoolAdministrator",)

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).admins

    async def get_specific_groups(self, lo: UDM) -> List[str]:
        groups = await super(SchoolAdmin, self).get_specific_groups(lo)
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
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).staff

    async def get_samba_home_path(self, lo: UDM) -> None:
        """	Do not set sambaHomePath for staff users. """
        return None

    def get_samba_home_drive(self) -> None:
        """	Do not set sambaHomeDrive for staff users. """
        return None

    def get_samba_netlogon_script_path(self) -> None:
        """	Do not set sambaLogonScript for staff users. """
        return None

    async def get_profile_path(self, lo) -> None:
        """	Do not set sambaProfilePath for staff users. """
        return None

    def get_school_class_objs(self) -> List[SchoolClass]:
        return []

    @classmethod
    async def get_school_classes(cls, udm_obj: UdmObject, obj: "Staff") -> Dict[str, List[str]]:
        return {}

    async def get_specific_groups(self, lo: UDM) -> List[str]:
        groups = await super(Staff, self).get_specific_groups(lo)
        groups.extend(self.get_staff_groups())
        return groups


class TeachersAndStaff(Teacher):
    type_name = _("Teacher and Staff")
    type_filter = "(&(objectClass=ucsschoolStaff)(objectClass=ucsschoolTeacher))"
    roles = [role_teacher, role_staff]
    default_roles = [role_teacher, role_staff]
    default_options = ("ucsschoolStaff",)

    @classmethod
    def get_container(cls, school) -> str:
        return cls.get_search_base(school).teachersAndStaff

    async def get_specific_groups(self, lo):
        groups = await super(TeachersAndStaff, self).get_specific_groups(lo)
        groups.extend(self.get_staff_groups())
        return groups


class ExamStudent(Student):
    type_name = _("Exam student")
    type_filter = "(&(objectClass=ucsschoolStudent)(objectClass=ucsschoolExam))"
    default_roles = [role_exam_user]
    default_options = ("ucsschoolExam",)

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).examUsers

    @classmethod
    async def from_student_dn(cls, lo: UDM, school: str, dn: str) -> "ExamStudent":
        examUserPrefix = ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-")
        dn = "uid=%s%s,%s" % (
            escape_dn_chars(examUserPrefix),
            explode_dn(dn, True)[0],
            cls.get_container(school),
        )
        return await cls.from_dn(dn, school, lo)


ConcreteUserClass = TypeVar("ConcreteUserClass", Staff, Student, Teacher, TeachersAndStaff)


class UserTypeConverter:
    roles_add = {
        "staff": (role_staff,),
        "student": (role_student,),
        "teacher": (role_teacher,),
        "teacher_and_staff": (role_staff, role_teacher),
    }
    roles_rm = {
        "staff": (role_student, role_teacher),
        "student": (role_staff, role_teacher),
        "teacher": (role_staff, role_student),
        "teacher_and_staff": (role_student,),
    }

    @classmethod
    async def convert(
        cls,
        user: ConcreteUserClass,
        new_cls: Type[ConcreteUserClass],
        udm: UDM,
        additional_classes: Dict[str, List[str]] = None,
    ) -> ConcreteUserClass:
        logger = user.logger
        if not isinstance(user, User) or user.__class__ is User:
            raise TypeError(f"Argument 'user' is not an object of a 'User' subclass: {user!r}")
        if new_cls is User or not issubclass(new_cls, User):
            raise TypeError(f"Argument 'new_cls' is not a subclass of 'User': {new_cls!r}")
        elif new_cls is ExamStudent or isinstance(user, ExamStudent):
            raise TypeError("Type conversion from or to 'ExamStudent' is not allowed.")
        elif issubclass(new_cls, Student):
            if additional_classes:
                school_classes = copy.deepcopy(user.school_classes)
                for school, classes in additional_classes.items():
                    school_classes.setdefault(school, []).extend(classes)
            else:
                school_classes = user.school_classes
            if not all(school_classes.get(school) for school in user.schools):
                raise TypeError(
                    "Type conversion to 'Student' requires at least one school class per school in old "
                    "user or passed in additionally."
                )
        if issubclass(new_cls, Staff) and additional_classes:
            logger.warning("Additional school classes will be ignored during conversion to 'Staff'.")
        new_cls_name = new_cls.__name__
        if set(user.roles) == set(new_cls.roles):
            logger.debug("No type conversion necessary, user type is already %r: %r", new_cls_name, user)
            return user
        udm_obj = await user.get_udm_object(udm)
        if issubclass(new_cls, Student) and udm_obj.options.get("ucsschoolAdministrator", False):
            raise TypeError(f"Conversion to {new_cls_name!r} is not allowed for school administrator.")
        logger.info("Converting to %r: %r...", new_cls_name, user)
        logger.debug("Data before conversion:\n%s", cls._dump_user_data(udm_obj))
        options = {"ucsschoolStaff": False, "ucsschoolStudent": False, "ucsschoolTeacher": False}
        options.update(dict((opt, True) for opt in new_cls.get_default_options()))
        position = new_cls.get_container(user.school)
        groups = cls._groups(user, udm_obj, new_cls, additional_classes)
        ucsschool_roles = cls._roles(user, new_cls)
        logger.info(
            "The following data will be changed for %r:\n"
            "  Options: %r\n"
            "  Position: %r\n"
            "  Groups: %r\n"
            "  Ucsschool_roles: %r",
            user,
            options,
            position,
            groups,
            ucsschool_roles,
        )
        udm_obj.options = options
        udm_obj.position = position
        udm_obj.props.groups = groups
        udm_obj.props.ucsschoolRole = ucsschool_roles
        await udm_obj.save()
        new_user: ConcreteUserClass = await new_cls.from_dn(udm_obj.dn, user.school, udm)
        logger.info("Conversion to %r finished.", new_cls_name)
        logger.debug(
            "Data after conversion:\n%s", cls._dump_user_data(await new_user.get_udm_object(udm))
        )
        return new_user

    @staticmethod
    def _dump_user_data(udm_user: UdmObject) -> str:
        return (
            f"DN: {udm_user.dn!r}:\n"
            f"  options: {udm_user.options!r}\n"
            f"  schools: {sorted(udm_user.props.school)!r}\n"
            f"  groups: {sorted(udm_user.props.groups)!r}\n"
            f"  ucsschool_roles: {sorted(udm_user.props.ucsschoolRole)!r}"
        )

    @staticmethod
    def _groups(
        user: User,
        udm_obj: UdmObject,
        new_cls: Type[User],
        additional_classes: Dict[str, List[str]],
    ) -> List[str]:
        if issubclass(new_cls, Staff):
            add_groups = user.get_staff_groups()
            rm_groups = user.get_students_groups() + user.get_teachers_groups()
        elif issubclass(new_cls, Student):
            add_groups = user.get_students_groups()
            rm_groups = user.get_staff_groups() + user.get_teachers_groups()
        elif issubclass(new_cls, TeachersAndStaff):
            add_groups = user.get_staff_groups() + user.get_teachers_groups()
            rm_groups = user.get_students_groups()
        else:
            if not issubclass(new_cls, Teacher):
                raise RuntimeError(
                    f"Variable 'new_cls' should be [a subclass of] Teacher, but is: {new_cls!r} "
                    f"({type(new_cls)!r})."
                )
            add_groups = user.get_teachers_groups()
            rm_groups = user.get_staff_groups() + user.get_students_groups()
        # not beautiful, but keeps lower/upper case intact:
        rm_groups = set(g.lower() for g in rm_groups)
        if issubclass(new_cls, Staff):
            # remove school classes
            school_class_objs = user.get_school_class_objs()
            rm_groups.update(sc.dn.lower() for sc in school_class_objs)
        else:
            # add additional_classes
            if additional_classes:
                for school, classes in additional_classes.items():
                    cn = SchoolClass.get_container(school)
                    add_groups.extend(f"cn={school}-{kls},{cn}" for kls in classes)
        groups = set(grp for grp in udm_obj.props.groups if grp.lower() not in rm_groups)
        groups_lower = {grp.lower() for grp in groups}
        groups.update(grp for grp in add_groups if grp.lower() not in groups_lower)
        return sorted(groups)

    @classmethod
    def _roles(cls, user: User, new_cls: Type[User]) -> List[str]:
        if issubclass(new_cls, Staff):
            _add_roles = cls.roles_add["staff"]
            _rm_roles = cls.roles_rm["staff"]
        elif issubclass(new_cls, Student):
            _add_roles = cls.roles_add["student"]
            _rm_roles = cls.roles_rm["student"]
        elif issubclass(new_cls, TeachersAndStaff):
            _add_roles = cls.roles_add["teacher_and_staff"]
            _rm_roles = cls.roles_rm["teacher_and_staff"]
        else:
            assert issubclass(new_cls, Teacher)
            _add_roles = cls.roles_add["teacher"]
            _rm_roles = cls.roles_rm["teacher"]
        ucsschool_roles = {
            role
            for role in user.ucsschool_roles
            if not any(role.startswith(f"{rm_role}:{context_type_school}:") for rm_role in _rm_roles)
        }
        ucsschool_roles.update(
            create_ucsschool_role_string(role, school) for role in _add_roles for school in user.schools
        )
        return sorted(ucsschool_roles)


async def convert_to_staff(
    user: ConcreteUserClass,
    udm: UDM,
    additional_classes: Dict[str, List[str]] = None,
) -> Staff:
    return await UserTypeConverter.convert(user, Staff, udm, additional_classes)


async def convert_to_student(
    user: ConcreteUserClass,
    udm: UDM,
    additional_classes: Dict[str, List[str]] = None,
) -> Student:
    return await UserTypeConverter.convert(user, Student, udm, additional_classes)


async def convert_to_teacher(
    user: ConcreteUserClass,
    udm: UDM,
    additional_classes: Dict[str, List[str]] = None,
) -> Teacher:
    return await UserTypeConverter.convert(user, Teacher, udm, additional_classes)


async def convert_to_teacher_and_staff(
    user: ConcreteUserClass,
    udm: UDM,
    additional_classes: Dict[str, List[str]] = None,
) -> TeachersAndStaff:
    return await UserTypeConverter.convert(user, TeachersAndStaff, udm, additional_classes)
