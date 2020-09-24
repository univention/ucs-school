# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# Copyright 2014-2020 Univention GmbH
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

from ldap.dn import str2dn

from univention.admin.uexceptions import noObject

from ..roles import role_computer_room, role_school_class, role_workgroup
from .attributes import (
    Attribute,
    Description,
    Email,
    GroupName,
    Groups,
    Hosts,
    Roles,
    SchoolClassName,
    Users,
)
from .base import RoleSupportMixin, UCSSchoolHelperAbstractClass
from .misc import OU, Container
from .policy import UMCPolicy
from .share import ClassShare, WorkGroupShare
from .utils import _, ucr

try:
    from typing import Any, Dict, Generator, List, Optional, Type
    from .base import UdmObject, LoType
except ImportError:
    pass


class _MayHaveSchoolPrefix(object):
    def get_relative_name(self):  # type: () -> str
        # schoolname-1a => 1a
        if self.school and self.name.lower().startswith("%s-" % self.school.lower()):
            return self.name[len(self.school) + 1 :]
        return self.name

    def get_replaced_name(self, school):  # type: (str) -> str
        if self.name != self.get_relative_name():
            return "%s-%s" % (school, self.get_relative_name())
        return self.name


class _MayHaveSchoolSuffix(object):
    def get_relative_name(self):  # type: () -> str
        # schoolname-1a => 1a
        if (
            self.school
            and self.name.lower().endswith("-%s" % self.school.lower())
            or self.name.lower().endswith(" %s" % self.school.lower())
        ):
            return self.name[: -(len(self.school) + 1)]
        return self.name

    def get_replaced_name(self, school):  # type: (str) -> str
        if self.name != self.get_relative_name():
            delim = self.name[len(self.get_relative_name())]
            return "%s%s%s" % (self.get_relative_name(), delim, school)
        return self.name


class Group(RoleSupportMixin, UCSSchoolHelperAbstractClass):
    name = GroupName(_("Name"))  # type: str
    description = Description(_("Description"))  # type: str
    users = Users(_("Users"))  # type: List[str]
    ucsschool_roles = Roles(_("Roles"), aka=["Roles"])  # type: List[str]

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).groups

    @classmethod
    def is_school_group(cls, school, group_dn):  # type: (str, str) -> bool
        return cls.get_search_base(school).isGroup(group_dn)

    @classmethod
    def is_school_workgroup(cls, school, group_dn):  # type: (str, str) -> bool
        return cls.get_search_base(school).isWorkgroup(group_dn)

    @classmethod
    def is_school_class(cls, school, group_dn):  # type: (str, str) -> bool
        return cls.get_search_base(school).isClass(group_dn)

    @classmethod
    def is_computer_room(cls, school, group_dn):  # type: (str, str) -> bool
        return cls.get_search_base(school).isRoom(group_dn)

    def self_is_workgroup(self):  # type: () -> bool
        return self.is_school_workgroup(self.school, self.dn)

    def self_is_class(self):  # type: () -> bool
        return self.is_school_class(self.school, self.dn)

    def self_is_computerroom(self):  # type: () -> bool
        return self.is_computer_room(self.school, self.dn)

    @classmethod
    def get_class_for_udm_obj(cls, udm_obj, school):  # type: (UdmObject, str) -> Type["Group"]
        if cls.is_school_class(school, udm_obj.dn):
            return SchoolClass
        elif cls.is_computer_room(school, udm_obj.dn):
            return ComputerRoom
        elif cls.is_school_workgroup(school, udm_obj.dn):
            return WorkGroup
        elif cls.is_school_group(school, udm_obj.dn):
            return SchoolGroup
        return cls

    def add_umc_policy(self, policy_dn, lo):  # type: (str, LoType) -> None
        if not policy_dn or policy_dn.lower() == "none":
            self.logger.warning("No policy added to %r", self)
            return
        try:
            policy = UMCPolicy.from_dn(policy_dn, self.school, lo)
        except noObject:
            self.logger.warning(
                "Object to be referenced does not exist (or is no UMC-Policy): %s", policy_dn
            )
        else:
            policy.attach(self, lo)

    def build_hook_line(self, hook_time, func_name):  # type: (str, str) -> Optional[str]
        code = self._map_func_name_to_code(func_name)
        if code != "M":
            return self._build_hook_line(code, self.school, self.name, self.description,)
        else:
            # This is probably a bug. See ucs-school-import and Bug #34736
            old_name = self.get_name_from_dn(self.old_dn)
            new_name = self.name
            if old_name != new_name:
                return self._build_hook_line(code, old_name, new_name,)

    class Meta:
        udm_module = "groups/group"
        name_is_unique = True


class BasicGroup(Group):
    school = None
    container = Attribute(_("Container"), required=True)  # type: str

    def __init__(self, name=None, school=None, **kwargs):  # type: (str, str, **Any) -> None
        if "container" not in kwargs:
            kwargs["container"] = "cn=groups,%s" % ucr.get("ldap/base")
        super(BasicGroup, self).__init__(name=name, school=school, **kwargs)

    def create_without_hooks(self, lo, validate):  # type: (LoType, bool) -> bool
        # prepare LDAP: create containers where this basic group lives if necessary
        container_dn = self.get_own_container()[: -len(ucr.get("ldap/base")) - 1]
        containers = str2dn(container_dn)
        super_container_dn = ucr.get("ldap/base")
        for container_info in reversed(containers):
            dn_part, cn = container_info[0][0:2]
            if dn_part.lower() == "ou":
                container = OU(name=cn)
            else:
                container = Container(name=cn, school="", group_path="1")
            container.position = super_container_dn
            super_container_dn = container.create(lo, False)
        return super(BasicGroup, self).create_without_hooks(lo, validate)

    def get_own_container(self):  # type: () -> str
        return self.container

    def build_hook_line(self, hook_time, func_name):  # type: (str, str) -> Optional[str]
        return None

    @classmethod
    def get_container(cls, school=None):  # type: (Optional[str]) -> str
        return ucr.get("ldap/base")


class BasicSchoolGroup(BasicGroup):
    school = Group.school  # type: str


class SchoolGroup(Group, _MayHaveSchoolSuffix):
    pass


class SchoolClass(Group, _MayHaveSchoolPrefix):
    name = SchoolClassName(_("Name"))  # type: str

    default_roles = [role_school_class]  # type: List[str]
    _school_in_name_prefix = True
    ShareClass = ClassShare

    def __init__(
        self, name=None, school=None, create_share=True, **kwargs
    ):  # type: (Optional[str], Optional[str], Optional[bool], **Any) -> None
        super(SchoolClass, self).__init__(name, school, **kwargs)
        self._create_share = create_share

    def create_without_hooks(self, lo, validate):  # type: (LoType, bool) -> bool
        success = super(SchoolClass, self).create_without_hooks(lo, validate)
        if self._create_share and self.exists(lo):
            success = success and self.create_share(self.get_machine_connection())
        return success

    def create_share(self, lo):  # type: (LoType) -> bool
        share = self.ShareClass.from_school_group(self)
        return share.exists(lo) or share.create(lo)

    def modify_without_hooks(self, lo, validate=True, move_if_necessary=None):
        # type: (LoType, Optional[bool], Optional[bool]) -> bool
        share = self.ShareClass.from_school_group(self)
        if self.old_dn:
            old_name = self.get_name_from_dn(self.old_dn)
            if old_name != self.name:
                # recreate the share.
                # if the name changed
                # from_school_group will have initialized
                # share.old_dn incorrectly
                share = self.ShareClass(name=old_name, school=self.school, school_group=self)
                share.name = self.name
        success = super(SchoolClass, self).modify_without_hooks(lo, validate, move_if_necessary)
        if success:
            lo_machine = self.get_machine_connection()
            if share.exists(lo_machine):
                success = share.modify(lo_machine)
        return success

    def remove_without_hooks(self, lo):  # type: (LoType) -> bool
        success = super(SchoolClass, self).remove_without_hooks(lo)
        if success:
            share = self.ShareClass.from_school_group(self)
            lo_machine = self.get_machine_connection()
            if share.exists(lo_machine):
                success = success and share.remove(lo_machine)
        return success

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).classes

    def to_dict(self):  # type: () -> Dict[str, Any]
        ret = super(SchoolClass, self).to_dict()
        ret["name"] = self.get_relative_name()
        return ret

    @classmethod
    def get_class_for_udm_obj(cls, udm_obj, school):
        # type: (UdmObject, str) -> Optional[Type[SchoolClass]]
        if not cls.is_school_class(school, udm_obj.dn):
            return  # is a workgroup
        return cls

    def validate(self, lo, validate_unlikely_changes=False):  # type: (LoType, Optional[bool]) -> None
        super(SchoolClass, self).validate(lo, validate_unlikely_changes)
        if not self.name.startswith("{}-".format(self.school)):
            raise ValueError("Missing school prefix in name: {!r}.".format(self))


class WorkGroup(SchoolClass, _MayHaveSchoolPrefix):
    default_roles = [role_workgroup]
    ShareClass = WorkGroupShare
    email = Email(
        _("Email"), udm_name="mailAddress", aka=["Email", "E-Mail"], unlikely_to_change=True
    )  # type: str
    allowed_email_senders_users = Users(
        _("Users that are allowed to send e-mails to the group"), udm_name="allowedEmailUsers",
    )  # type: List[str]
    allowed_email_senders_groups = Groups(
        _("Groups that are allowed to send e-mails to the group"), udm_name="allowedEmailGroups",
    )  # type: List[str]

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).workgroups

    def build_hook_line(self, hook_time, func_name):  # type: (str, str) -> Optional[str]
        return None

    @classmethod
    def get_class_for_udm_obj(cls, udm_obj, school):
        # type: (UdmObject, str) -> Optional[Type[WorkGroup]]
        if not cls.is_school_workgroup(school, udm_obj.dn):
            return
        return cls


class ComputerRoom(Group, _MayHaveSchoolPrefix):
    hosts = Hosts(_("Hosts"))  # type: List[str]

    users = None
    default_roles = [role_computer_room]

    def to_dict(self):  # type: () -> Dict[str, Any]
        ret = super(ComputerRoom, self).to_dict()
        ret["name"] = self.get_relative_name()
        return ret

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).rooms

    def get_computers(self, ldap_connection):  # type: (LoType) -> Generator["SchoolComputer"]
        from ucsschool.lib.models.computer import SchoolComputer

        for host in self.hosts:
            try:
                yield SchoolComputer.from_dn(host, self.school, ldap_connection)
            except noObject:
                continue

    def get_schools_from_udm_obj(self, udm_obj):  # type: (UdmObject) -> str
        # fixme: no idea how to find out old school
        return self.school