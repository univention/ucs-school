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

from typing import Dict, Iterable, List, Optional, Set, Union

import ldap
from ldap.dn import escape_dn_chars
from ldap.filter import escape_filter_chars, filter_format

from udm_rest_client import UDM, CreateError, NoObject as UdmNoObject, UdmObject
from univention.admin.filter import conjunction
from univention.admin.uexceptions import noObject
from univention.config_registry import handler_set
from univention.config_registry.interfaces import Interfaces

from ..roles import (
    create_ucsschool_role_string,
    role_dc_slave_admin,
    role_dc_slave_edu,
    role_school,
    role_school_admin_group,
    role_school_domain_group,
    role_school_staff_group,
    role_school_student_group,
    role_school_teacher_group,
    role_single_master,
    role_staff,
    role_student,
    role_teacher,
)
from .attributes import Attribute, DCName, DisplayName, SchoolName, ShareFileServer
from .base import RoleSupportMixin, UCSSchoolHelperAbstractClass
from .computer import AnyComputer, SchoolDC, SchoolDCSlave
from .dhcp import DHCPService
from .group import BasicGroup, BasicSchoolGroup, Group
from .misc import OU, Container
from .policy import DHCPDNSPolicy
from .share import MarketplaceShare
from .utils import _, flatten, ucr


class School(RoleSupportMixin, UCSSchoolHelperAbstractClass):
    name: str = SchoolName(_("School name"))
    dc_name: str = DCName(_("DC Name"))
    dc_name_administrative: str = DCName(_("DC Name administrative server"))
    class_share_file_server: str = ShareFileServer(
        _("Server for class shares"), udm_name="ucsschoolClassShareFileServer"
    )
    home_share_file_server: str = ShareFileServer(
        _("Server for Windows home directories"), udm_name="ucsschoolHomeShareFileServer"
    )
    display_name: str = DisplayName(_("Display name"))
    school: str = None
    educational_servers: List[str] = Attribute(_("Educational servers"), unlikely_to_change=True)
    administrative_servers: List[str] = Attribute(_("Administrative servers"), unlikely_to_change=True)

    default_roles = [role_school]
    _school_in_name = True
    _school_obj_cache: Dict[str, "School"] = {}

    def __init__(self, name: str = None, school: str = None, alter_dhcpd_base: bool = None, **kwargs):
        super(School, self).__init__(name=name, **kwargs)
        self.display_name = self.display_name or self.name
        self.alter_dhcpd_base = (
            alter_dhcpd_base
            if alter_dhcpd_base is not None
            else not bool(ucr.get("dhcpd/ldap/base", ""))
        )

    async def validate(self, lo: UDM, validate_unlikely_changes: bool = False) -> None:
        await super(School, self).validate(lo, validate_unlikely_changes)
        if self.dc_name and self.dc_name == self.dc_name_administrative:
            self.add_error(
                "dc_name", _("Hostname of educational DC and administrative DC must not be equal")
            )
            self.add_error(
                "dc_name_administrative",
                _("Hostname of educational DC and administrative DC must not be equal"),
            )
        if self.dc_name:
            ldap_filter_str = ""
            if ucr.is_true("ucsschool/singlemaster"):
                ldap_filter_str = filter_format(
                    "(&(objectClass=univentionDomainController)(cn=%s)(univentionServerRole=backup))",
                    [self.dc_name.lower()],
                )
            else:
                ldap_filter_str = filter_format(
                    "(&"
                    "(objectClass=univentionDomainController)"
                    "(cn=%s)"
                    "(|"
                    "(univentionServerRole=backup)"
                    "(univentionServerRole=master)"
                    ")"
                    ")",
                    [self.dc_name.lower()],
                )
            dcs = [obj async for obj in lo.get("computers/computer").search(ldap_filter_str)]
            if len(dcs) and ucr.is_true("ucsschool/singlemaster"):
                self.add_error(
                    "dc_name", "The educational DC for the school must not be a backup server"
                )
            elif len(dcs):
                self.add_error(
                    "dc_name", "The educational DC for the school must not be a backup or master server"
                )

    def get_district(self) -> str:
        if ucr.is_true("ucsschool/ldap/district/enable"):
            return self.name[:2]

    def get_own_container(self) -> str:
        district = self.get_district()
        if district:
            return "ou=%s,%s" % (escape_dn_chars(district), self.get_container())
        return self.get_container()

    @classmethod
    def get_container(cls, school: str = None) -> str:
        return ucr.get("ldap/base")

    @classmethod
    def cn_name(cls, name: str, default: str) -> str:
        ucr_var = "ucsschool/ldap/default/container/%s" % name
        return ucr.get(ucr_var, default)

    async def create_default_containers(self, lo: UDM) -> None:
        cn_pupils = self.cn_name("pupils", "schueler")
        cn_teachers = self.cn_name("teachers", "lehrer")
        cn_admins = self.cn_name("admins", "admins")
        cn_classes = self.cn_name("class", "klassen")
        cn_rooms = self.cn_name("rooms", "raeume")
        user_containers = [cn_pupils, cn_teachers, cn_admins]
        group_containers = [cn_pupils, [cn_classes], cn_teachers, cn_rooms]
        if self.shall_create_administrative_objects():
            cn_staff = self.cn_name("staff", "mitarbeiter")
            cn_teachers_staff = self.cn_name("teachers-and-staff", "lehrer und mitarbeiter")
            user_containers.extend([cn_staff, cn_teachers_staff])
            group_containers.append(cn_staff)
        containers_with_path = {
            "printer_path": ["printers"],
            "user_path": ["users", user_containers],
            "computer_path": ["computers", ["server", ["dc"]]],
            "network_path": ["networks"],
            "group_path": ["groups", group_containers],
            "dhcp_path": ["dhcp"],
            "policy_path": ["policies"],
            "share_path": ["shares", [cn_classes]],
        }

        async def _add_container(name: str, last_dn: str, base_dn: str, path: str, lo: UDM) -> str:
            if isinstance(name, (list, tuple)):
                base_dn = last_dn
                for cn in name:
                    last_dn = await _add_container(cn, last_dn, base_dn, path, lo)
            else:
                container = Container(name=name, school=self.name)
                setattr(container, path, True)
                container.position = base_dn
                last_dn = container.dn
                if not await container.exists(lo):
                    last_dn = await container.create(lo, False)
            return last_dn

        last_dn = self.dn
        path = None
        for path, containers in containers_with_path.items():
            for cn in containers:
                last_dn = await _add_container(cn, last_dn, self.dn, path, lo)

    def group_name(self, prefix_var: str, default_prefix: str) -> str:
        ucr_var = "ucsschool/ldap/default/groupprefix/%s" % prefix_var
        name_part = ucr.get(ucr_var, default_prefix)
        school_part = self.name.lower()
        return "%s%s" % (name_part, school_part)

    def get_umc_policy_dn(self, name: str) -> str:
        # at least the default ones should exist due to the join script
        return ucr.get(
            "ucsschool/ldap/default/policy/umc/%s" % name,
            "cn=ucsschool-umc-%s-default,cn=UMC,cn=policies,%s" % (name, ucr.get("ldap/base")),
        )

    async def create_default_groups(self, lo: UDM) -> None:
        # DC groups
        administrative_group_container = "cn=ucsschool,cn=groups,%s" % ucr.get("ldap/base")

        # DC-Edukativnetz
        # OU%s-DC-Edukativnetz
        # Member-Edukativnetz
        # OU%s-Member-Edukativnetz
        administrative_group_names = self.get_administrative_group_name(
            "educational", domain_controller="both", ou_specific="both"
        )
        if self.shall_create_administrative_objects():
            administrative_group_names.extend(
                self.get_administrative_group_name(
                    "administrative", domain_controller="both", ou_specific="both"
                )
            )  # same with Verwaltungsnetz
        for administrative_group_name in administrative_group_names:
            group = BasicGroup.cache(
                name=administrative_group_name, container=administrative_group_container
            )
            await group.create(lo)

        # cn=ouadmins
        admin_group_container = Container(name="ouadmins", school="")
        admin_group_container.position = "cn=groups,{}".format(ucr["ldap/base"])
        if not await admin_group_container.exists(lo):
            await admin_group_container.create(lo, False)

        # admins-%s
        group = BasicSchoolGroup.cache(
            self.group_name("admins", "admins-"), self.name, container=admin_group_container.dn
        )
        group.ucsschool_roles = [create_ucsschool_role_string(role_school_admin_group, self.name)]
        await group.create(lo)
        await group.add_umc_policy(self.get_umc_policy_dn("admins"), lo)
        try:
            udm_obj = await group.get_udm_object(lo)
        except noObject:
            self.logger.error('Could not load OU admin group %r for adding "school" value', group.dn)
        else:
            admin_option = "ucsschoolAdministratorGroup"
            if udm_obj.options.get(admin_option) is not True:
                udm_obj.options[admin_option] = True
            udm_obj.props.school = [self.name]
            await udm_obj.save()

        # cn=schueler
        group = Group.cache(self.group_name("pupils", "schueler-"), self.name)
        group.ucsschool_roles = [create_ucsschool_role_string(role_school_student_group, self.name)]
        await group.create(lo)
        await group.add_umc_policy(self.get_umc_policy_dn("pupils"), lo)

        # cn=lehrer
        group = Group.cache(self.group_name("teachers", "lehrer-"), self.name)
        group.ucsschool_roles = [create_ucsschool_role_string(role_school_teacher_group, self.name)]
        await group.create(lo)
        await group.add_umc_policy(self.get_umc_policy_dn("teachers"), lo)

        # cn=mitarbeiter
        if self.shall_create_administrative_objects():
            group = Group.cache(self.group_name("staff", "mitarbeiter-"), self.name)
            group.ucsschool_roles = [create_ucsschool_role_string(role_school_staff_group, self.name)]
            await group.create(lo)
            await group.add_umc_policy(self.get_umc_policy_dn("staff"), lo)

        # cn=Domain Users %s
        group = Group.cache("Domain Users %s" % (self.name,), self.name)
        group.ucsschool_roles = [create_ucsschool_role_string(role_school_domain_group, self.name)]
        await group.create(lo)
        if ucr.is_true("ucsschool/import/attach/policy/default-umc-users", True):
            await group.add_umc_policy(
                "cn=default-umc-users,cn=UMC,cn=policies,%s" % (ucr.get("ldap/base"),), lo
            )

    def get_dc_name_fallback(self, administrative: bool = False) -> str:
        if administrative:
            # this is the naming convention, a trailing v for Verwaltungsnetz DC
            # convention changed with Bug #51274
            return "dcv%s" % self.name.lower()
        else:
            return "dc%s" % self.name.lower()

    def get_dc_name(self, administrative: bool = False) -> str:
        if ucr.is_true("ucsschool/singlemaster", False):
            return ucr.get("hostname")
        elif self.dc_name:
            if administrative:
                return "%sv" % self.dc_name
            else:
                return self.dc_name
        else:
            return self.get_dc_name_fallback(administrative=administrative)

    async def get_share_fileserver_dn(self, set_by_self: str, lo: UDM) -> str:
        if set_by_self:
            set_by_self = self.get_name_from_dn(set_by_self) or set_by_self
        hostname = set_by_self or self.get_dc_name()
        if hostname == self.get_dc_name_fallback():
            # does not matter if exists or not - dc object will be created later
            host = SchoolDC(name=hostname, school=self.name)
            return host.dn

        host = await AnyComputer.get_first_udm_obj(lo, "cn=%s" % escape_filter_chars(hostname))
        if host:
            return host.dn
        else:
            self.logger.warning(
                'Could not find %s. Using this host as ShareFileServer ("%s").',
                hostname,
                ucr.get("hostname"),
            )
            return ucr.get("ldap/hostdn")

    async def get_class_share_file_server(self, lo: UDM) -> str:
        return await self.get_share_fileserver_dn(self.class_share_file_server, lo)

    async def get_home_share_file_server(self, lo: UDM) -> str:
        return await self.get_share_fileserver_dn(self.home_share_file_server, lo)

    def get_administrative_group_name(
        self, group_type: str, domain_controller: bool = True, ou_specific: bool = False, as_dn: bool = False
    ) -> Union[str, List[str]]:
        if domain_controller == "both":
            return flatten(
                [
                    self.get_administrative_group_name(group_type, True, ou_specific, as_dn),
                    self.get_administrative_group_name(group_type, False, ou_specific, as_dn),
                ]
            )
        if ou_specific == "both":
            return flatten(
                [
                    self.get_administrative_group_name(group_type, domain_controller, False, as_dn),
                    self.get_administrative_group_name(group_type, domain_controller, True, as_dn),
                ]
            )
        if group_type == "administrative":
            name = "Verwaltungsnetz"
        else:
            name = "Edukativnetz"
        if domain_controller:
            name = "DC-%s" % name
        else:
            name = "Member-%s" % name
        if ou_specific:
            name = "OU%s-%s" % (self.name.lower(), name)
        if as_dn:
            return "cn=%s,cn=ucsschool,cn=groups,%s" % (name, ucr.get("ldap/base"))
        else:
            return name

    async def get_administrative_server_names(self, lo: UDM) -> List[str]:
        dn = self.get_administrative_group_name("administrative", ou_specific=True, as_dn=True)
        mod = lo.get("groups/group")
        udm_obj = await mod.get(dn)
        return udm_obj.props.hosts

    async def get_educational_server_names(self, lo: UDM) -> List[str]:
        dn = self.get_administrative_group_name("educational", ou_specific=True, as_dn=True)
        mod = lo.get("groups/group")
        udm_obj = await mod.get(dn)
        return udm_obj.props.hosts

    async def add_host_to_dc_group(self, lo: UDM) -> None:
        self.logger.info(
            "School.add_host_to_dc_group(): ou_name=%r  dc_name=%r", self.name, self.dc_name
        )
        if self.dc_name:
            dc_name_l = self.dc_name.lower()
            dc_udm_obj = None
            mb_dcs = [
                obj
                async for obj in lo.get("computers/computer").search(
                    filter_format(
                        "(&"
                        "(objectClass=univentionDomainController)"
                        "(cn=%s)"
                        "(|(univentionServerRole=backup)(univentionServerRole=master))"
                        ")",
                        [self.dc_name.lower()],
                    )
                )
            ]
            if len(mb_dcs):
                return  # We do not modify the groups of master or backup servers.
                # Should be validated, but stays here as well in case validation was deactivated
            # Sadly we need this here to access non school specific computers.
            slave_dcs = [
                obj
                async for obj in lo.get("computers/domaincontroller_slave").search(
                    filter_format("(cn=%s)", [dc_name_l])
                )
            ]
            if len(slave_dcs):
                dn, attr = slave_dcs[0]
                try:
                    dc_udm_obj = await lo.get("computers/domaincontroller_slave").get(dn)
                except UdmNoObject:
                    pass
            if not dc_udm_obj:
                roles = [create_ucsschool_role_string(role_dc_slave_edu, self.name)]
                dc = SchoolDCSlave(name=self.dc_name, school=self.name, ucsschool_roles=roles)
                await dc.create(lo)
                dc_udm_obj = await dc.get_udm_object(lo)
            else:
                dc = await SchoolDCSlave.from_udm_obj(
                    await SchoolDCSlave.get_first_udm_obj(lo, filter_format("cn=%s", [self.dc_name])),
                    self.name,
                    lo,
                )
                if dc:
                    dc.ucsschool_roles = [create_ucsschool_role_string(role_dc_slave_edu, self.name)]
                    await dc.modify(lo)
            groups = self.get_administrative_group_name("educational", ou_specific="both", as_dn=True)
            for grp in groups:
                if grp not in dc_udm_obj.props.groups:
                    dc_udm_obj.props.groups.append(grp)
            await dc_udm_obj.save()

    def shall_create_administrative_objects(self) -> bool:
        return ucr.is_true("ucsschool/ldap/noneducational/create/objects", True)

    async def create_dc_slave(self, lo: UDM, name: str, administrative: bool = False) -> bool:
        if administrative and not self.shall_create_administrative_objects():
            self.logger.warning(
                "Not creating %s: An administrative DC shall not be created as by UCR variable %r",
                name,
                "ucsschool/ldap/noneducational/create/objects",
            )
            return False
        if not await self.exists(lo):
            self.logger.error("%r does not exist. Cannot create %s", self, name)
            return False
        if administrative:
            groups = self.get_administrative_group_name("administrative", ou_specific="both", as_dn=True)
        else:
            groups = self.get_administrative_group_name("educational", ou_specific="both", as_dn=True)
        self.logger.debug("DC shall become member of %r", groups)

        roles = [
            create_ucsschool_role_string(
                role_dc_slave_admin if administrative else role_dc_slave_edu, self.name
            )
        ]
        dc = SchoolDCSlave(name=name, school=self.name, groups=groups, ucsschool_roles=roles)
        if await dc.exists(lo):
            self.logger.info("%r exists. Setting groups, do not move to %r!", dc, self)
            # call dc.move() if really necessary to move
            return await dc.modify(lo, move_if_necessary=False)
        else:
            existing_host = await AnyComputer.get_first_udm_obj(lo, "cn=%s" % escape_filter_chars(name))
            if existing_host:
                self.logger.error(
                    'Given host name "%s" is already in use and no domaincontroller slave system. '
                    "Please choose another name.",
                    name,
                )
                return False
            return await dc.create(lo)

    async def add_domain_controllers(self, lo: UDM) -> Optional[bool]:
        self.logger.info("School.add_domain_controllers(): ou_name=%r", self.name)
        school_dcs = ucr.get("ucsschool/ldap/default/dcs", "edukativ").split()
        for dc in school_dcs:
            administrative = dc == "verwaltung"
            dc_name = self.get_dc_name(administrative=administrative)
            server = await AnyComputer.get_first_udm_obj(lo, "cn=%s" % escape_filter_chars(dc_name))
            self.logger.info(
                "School.add_domain_controllers(): administrative=%r  dc_name=%s  self.dc_name=%r  "
                "server=%r",
                administrative,
                dc_name,
                self.dc_name,
                server,
            )
            if not server and not self.dc_name:
                if administrative:
                    administrative_type = "administrative"
                else:
                    administrative_type = "educational"
                group_dn = self.get_administrative_group_name(
                    administrative_type, ou_specific=True, as_dn=True
                )
                try:
                    group = await lo.get("groups/group").get(group_dn)
                    hostlist = group.props.hosts
                except UdmNoObject:
                    hostlist = []
                except Exception as exc:
                    self.logger.error("cannot read %s: %s", group_dn, exc)
                    return

                if hostlist:
                    # if at least one DC has control over this OU then jump to next 'school_dcs'
                    # item ==> do not create default slave objects
                    continue

                await self.create_dc_slave(lo, dc_name, administrative=administrative)

            dhcp_service = self.get_dhcp_service(dc_name)
            await dhcp_service.create(lo)
            await dhcp_service.add_server(dc_name, lo)
            return True

    def get_dhcp_service(self, hostname: str = None) -> DHCPService:
        return DHCPService.cache(
            self.name.lower(), self.name, hostname=hostname, domainname=ucr.get("domainname")
        )

    async def create_without_hooks(self, lo: UDM, validate: bool) -> bool:
        district = self.get_district()
        if district:
            ou = OU(name=district)
            ou.position = ucr.get("ldap/base")
            await ou.create(lo, False)

        # setting class_share_file_server and home_share_file_server:
        # 1. set to None
        # 2. create school
        # 3. (maybe) create file_servers <- that is why this is necessary
        # 4. set file_servers
        # 5. modify school
        saved_class_share_file_server = self.class_share_file_server
        saved_home_share_file_server = self.home_share_file_server
        self.class_share_file_server = None
        self.home_share_file_server = None

        try:
            success = await super(School, self).create_without_hooks(lo, validate)
            if not success:
                self.logger.warning(
                    "Creating %r failed (maybe it already exists?)! Trying to set it up nonetheless",
                    self,
                )
                await self.modify_without_hooks(lo)

            if self.alter_dhcpd_base and ucr.is_true("ucsschool/singlemaster", False):
                handler_set(["dhcpd/ldap/base=cn=dhcp,%s" % (self.dn)])
                ucr.load()

            await self.create_default_containers(lo)
            await self.create_default_groups(lo)
            await self.add_host_to_dc_group(lo)
            if not await self.add_domain_controllers(lo):
                return False
            if self.dc_name_administrative:
                await self.create_dc_slave(lo, self.dc_name_administrative, administrative=True)
                dhcp_service = self.get_dhcp_service(self.dc_name_administrative)
                await dhcp_service.create(lo)
                await dhcp_service.add_server(self.dc_name_administrative, lo)
        finally:
            self.logger.debug(
                "Resetting share file servers from None to %r and %r",
                saved_home_share_file_server,
                saved_class_share_file_server,
            )
            self.class_share_file_server = saved_class_share_file_server
            self.home_share_file_server = saved_home_share_file_server
        self.class_share_file_server = await self.get_class_share_file_server(lo)
        self.home_share_file_server = await self.get_home_share_file_server(lo)
        self.logger.debug(
            "Now it is %r and %r - %r should be modified accordingly",
            self.home_share_file_server,
            self.class_share_file_server,
            self,
        )
        await self.modify_without_hooks(lo)

        # if requested, then create dhcp_dns policy that clears univentionDhcpDomainNameServers at OU
        # level to prevent problems with "wrong" DHCP DNS policy connected to ldap base
        if ucr.is_true("ucsschool/import/generate/policy/dhcp/dns/clearou", False):
            policy = DHCPDNSPolicy(
                name="dhcp-dns-clear",
                school=self.name,
                empty_attributes=["univentionDhcpDomainNameServers"],
            )
            await policy.create(lo)
            await policy.attach(self, lo)

        return success

    async def remove_without_hooks(self, lo: UDM) -> bool:
        from ucsschool.lib.models.user import User

        success = super(School, self).remove_without_hooks(lo)
        for grpdn in (
            "cn=OU%(ou)s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%(basedn)s",
            "cn=OU%(ou)s-Member-Edukativnetz,cn=ucsschool,cn=groups,%(basedn)s",
            "cn=OU%(ou)s-Klassenarbeit,cn=ucsschool,cn=groups,%(basedn)s",
            "cn=OU%(ou)s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%(basedn)s",
            "cn=OU%(ou)s-DC-Edukativnetz,cn=ucsschool,cn=groups,%(basedn)s",
            "cn=admins-%(ou)s,cn=ouadmins,cn=groups,%(basedn)s",
        ):
            grpdn = grpdn % {"ou": self.name, "basedn": ucr.get("ldap/base")}
            self._remove_udm_object("groups/group", grpdn, lo)

        for user in await User.get_all(lo, self.name):
            user.remove_from_school(self.name, lo)
        return success

    def get_schools(self) -> Set[str]:
        return {self.name}

    def _remove_udm_object(self, module: str, dn: str, lo: UDM, raise_exceptions: bool = False) -> str:
        """
        Tries to remove UDM object specified by given dn.
        Return None on success or error message.
        """
        raise NotImplementedError("Deletion of schools not yet implemented.")
        try:
            # TODO: use UDM instead of LDAP
            dn = lo.searchDn(base=dn)[0]
        except (ldap.NO_SUCH_OBJECT, IndexError, noObject):
            if raise_exceptions:
                raise
            return "missing object"

        msg = None
        cmd = ["udm", module, "remove", "--dn", dn]
        self.logger.info("*** Calling following command: %r", cmd)
        # TODO: OMG!!
        retval = subprocess.call(cmd)  # nosec
        if retval:
            msg = "*** ERROR: failed to remove UCS@school %s object: %s" % (module, dn)
            self.logger.error(msg)
        return msg

    async def _alter_udm_obj(self, udm_obj: UdmObject) -> None:
        udm_obj.options["UCSschool-School-OU"] = True
        return await super(School, self)._alter_udm_obj(udm_obj)

    @classmethod
    async def from_binddn(cls, lo):
        raise NotImplementedError("Not available in Kelvin API.")
        cls.logger.debug("All local schools: Showing all OUs which DN %s can read.", lo.binddn)
        # get all schools of the user which are present on this server
        user_schools = lo.search(base=lo.binddn, scope="base", attr=["ucsschoolSchool"])[0][1].get(
            "ucsschoolSchool", []
        )
        if user_schools:
            schools = []
            for ou in user_schools:
                try:
                    schools.append(await cls.from_dn(cls(name=ou).dn, None, lo))
                except noObject:
                    pass
            return await cls._filter_local_schools(schools, lo)

        if "ou=" in lo.binddn:
            # user has no ucsschoolSchool attribute (not migrated yet)
            # we got an OU in the user DN -> school teacher or assistent
            # restrict the visibility to current school
            # (note that there can be schools with a DN such as ou=25g18,ou=25,dc=...)
            school_dn = lo.binddn[lo.binddn.find("ou=") :]
            cls.logger.debug(
                "Schools from binddn: Found an OU in the LDAP binddn. Restricting schools to only show "
                "%s",
                school_dn,
            )
            school = await cls.from_dn(school_dn, None, lo)
            cls.logger.debug("Schools from binddn: Found school: %r", school)
            return await cls._filter_local_schools([school], lo)

        cls.logger.warning(
            "Schools from binddn: Unable to identify OU of this account - showing all local OUs!"
        )
        return await School.get_all(lo)

    @classmethod
    async def from_udm_obj(cls, udm_obj: UdmObject, school: str, lo: UDM) -> "School":
        obj = await super(School, cls).from_udm_obj(udm_obj, school, lo)
        obj.educational_servers = await obj.get_educational_server_names(lo)
        obj.administrative_servers = await obj.get_administrative_server_names(lo)
        return obj

    @classmethod
    async def get_all(
        cls, lo: UDM, filter_str: str = None, easy_filter: str = False, respect_local_oulist=True
    ) -> Iterable["School"]:
        # When no easy_filter is used:
        # A direct LDAP request (for speed) is done always to check for new or
        # OUs. The ucsschool.lib School objects are cached.
        if easy_filter:
            schools = await super(School, cls).get_all(
                lo, school=None, filter_str=filter_str, easy_filter=easy_filter
            )
        else:
            complete_filter = f"({cls.Meta.udm_filter})"
            if filter_str and not filter_str.startswith("("):
                filter_str = f"({filter_str})"
            if filter_str:
                complete_filter = conjunction("&", [complete_filter, filter_str])
            schools = []
            async for obj in lo.get(cls.Meta.udm_module).search(str(complete_filter)):
                ou = obj.props.name
                if ou.lower() not in cls._school_obj_cache:
                    cls._school_obj_cache[ou.lower()] = await School.from_dn(obj.dn, None, lo)
                schools.append(cls._school_obj_cache[ou.lower()])
        oulist = ucr.get("ucsschool/local/oulist")
        if oulist and respect_local_oulist:
            cls.logger.debug("All Schools: Schools overridden by UCR variable ucsschool/local/oulist")
            ous = [x.strip() for x in oulist.split(",")]
            schools = [school for school in schools if school.name in ous]
        return schools

    @classmethod
    async def _filter_local_schools(cls, schools: List["School"], lo: UDM):
        if ucr.get("server/role") in ("domaincontroller_master", "domaincontroller_backup"):
            return schools
        return [
            school
            for school in schools
            if any(
                ucr.get("ldap/hostdn", "").lower() == x.lower()
                for x in await school.get_administrative_server_names(lo)
                + school.get_educational_server_names(lo)
            )
        ]

    @classmethod
    def _attrs_for_easy_filter(cls):
        # TODO: BASE._attrs_for_easy_filter() not implemented!
        return super(cls, School)._attrs_for_easy_filter() + ["displayName"]

    @classmethod
    def invalidate_cache(cls):
        from ucsschool.lib.models.user import User

        super(School, cls).invalidate_cache()
        User._samba_home_path_cache.clear()

    async def call_hooks(self, udm: UDM, hook_time: str, func_name: str) -> bool:
        """
        Runs PyHooks, then ucs-school-libs fork hooks.

        :param str hook_time: `pre` or `post`
        :param str func_name: `create`, `modify`, `move` or `remove`
        :param UDM udm:
        :return: return code of lib hooks
        :rtype: bool: result of a legacy hook or None if no legacy hook ran
        """
        if hook_time == "post":
            await self.set_ucsschool_role_for_dc(udm)
            await self.create_market_place_share(udm)
            await self.create_dhcp_search_base(udm)
            await self.create_dhcp_dns_policy(udm)
            await self.create_import_group(udm)
            await self.create_exam_group(udm)

        return await super(School, self).call_hooks(udm, hook_time, func_name)

    async def set_ucsschool_role_for_dc(self, udm: UDM) -> None:
        """
        Set the ucsschool role for the computer on which the school is replicated.
        formerly in shell hook 40dhcp_dns_marktplatz_ucsschoolrole
        """
        ou_lower = self.name.lower()
        ldap_hostdn = ucr["ldap/hostdn"]
        if ucr.is_true("ucsschool/singlemaster", True):
            mod = udm.get("computers/domaincontroller_master")
            obj = await mod.get(ldap_hostdn)
            role = create_ucsschool_role_string(role_single_master, self.name)
            if role not in obj.props.ucsschoolRole:
                obj.props.ucsschoolRole.append(role)
                await obj.save()
                self.logger.info("Append ucsschoolRole {} to {}".format(role, ldap_hostdn))
            else:
                self.logger.warning(
                    "ucsschoolRole {} is already appended to {}".format(role, ldap_hostdn)
                )
        else:
            adm_net_filter = "cn=OU{}-DC-Verwaltungsnetz".format(ou_lower)
            edu_net_filter = "cn=OU{}-DC-Edukativnetz".format(ou_lower)
            base = "cn=ucsschool,cn=groups,{}".format(ucr["ldap/base"])

            for ldap_filter, role in [
                (adm_net_filter, "dc_slave_admin"),
                (edu_net_filter, "dc_slave_edu"),
            ]:
                groups = [grp async for grp in udm.get("groups/group").search(ldap_filter, base=base)]
                if groups:
                    server_dn: str = groups[0].props.hosts[0]
                    try:
                        await udm.get("computers/domaincontroller_slave").get(server_dn)
                    except UdmNoObject:
                        self.logger.info(
                            "A DC slave was expected at {}. Not setting ucsscchoolRole property.".format(
                                server_dn
                            )
                        )
                        continue

                    obj = await SchoolDCSlave.from_dn(server_dn, self.name, udm)
                    ucsschool_role = create_ucsschool_role_string(role, self.name)
                    if ucsschool_role not in obj.ucsschool_roles:
                        obj.props.ucsschool_roles.append(ucsschool_role)
                        await obj.modify(udm)
                        self.logger.info("Append ucsschoolRole {} to {}".format(role, server_dn))

    async def create_market_place_share(self, lo: UDM) -> None:
        """
        Create a share object with the name `Marktplatz` for the school.
        formerly in shell hook 40dhcp_dns_marktplatz_ucsschoolrole
        """
        if not ucr.is_true("ucsschool/import/generate/share/marktplatz", False):
            self.logger.info(
                "Creation of share 'Marktplatz' has been disabled"
                "by ucsschool/import/generate/share/marktplatz"
            )
            return
        objs = MarketplaceShare.get_all(lo=lo, school=self.name)
        if not objs:
            obj = MarketplaceShare(name="Marktplatz", school=self.name)
            if await obj.exists(lo):
                self.logger.warning(
                    "Object of type MarketplaceShare with school={} and name=Marktplatz exists.".format(
                        self.name
                    ),
                )
            else:
                success = await obj.create(lo)
                if not success:
                    self.logger.error(
                        "Failed to create MarketplaceShare for school={}.".format(self.name),
                    )
                    return
            self.logger.info("Created {!r}".format(obj))
        else:
            self.logger.warning("MarketplaceShare for {} exists already.".format(self.name))

    async def create_dhcp_search_base(self, lo: UDM) -> None:
        """
        Create the policies/registry ou-default-ucr-policy for the school,
        add the dhcp-ou-dn to it an link to the school.

        formerly in shell hook 40dhcp_dns_marktplatz_ucsschoolrole
        """
        if not ucr.is_true("ucsschool/import/generate/policy/dhcp/searchbase", False):
            self.logger.info(
                "Creation of UCR policy for DHCP searchbase has been disabled by"
                "ucsschool/import/generate/policy/dhcp/searchbase"
            )
            return
        ou_dn = self.dn
        registry_mod = lo.get("policies/registry")
        try:
            policy = await registry_mod.new()
            policy.position = "cn=policies,{}".format(ou_dn)
            policy.props.name = "ou-default-ucr-policy"
            await policy.save()
        except CreateError:
            # object exists already.
            self.logger.error("Error while creating ou-default-ucr-policy for {}".format(self.name))
            pass

        # add value to policy
        policy_dn = "cn=ou-default-ucr-policy,cn=policies,{}".format(ou_dn)
        policy = await registry_mod.get(policy_dn)
        if policy.props.registry:
            policy.props.registry["dhcpd/ldap/base"] = "cn=dhcp,{}".format(ou_dn)
        else:
            # empty registry is a list and not a dict.
            policy.props.registry = {"dhcpd/ldap/base": "cn=dhcp,{}".format(ou_dn)}
        await policy.save()
        # link to OU
        obj = await self.get_udm_object(lo)
        obj.policies.append(policy_dn)
        await obj.save()
        self.logger.info("Linked ou-default-ucr-policy to {}.".format(ou_dn))

    async def create_dhcp_dns_policy(self, udm: UDM) -> None:
        """
        Add a DHCPDNSPolicy for the school, append it to the respective
        container/cn object and add domain_name and domain_name_servers
        in single server environments.
        formerly in shell hook 40dhcp_dns_marktplatz_ucsschoolrole
        """
        if not ucr.is_true("ucsschool/import/generate/policy/dhcp/dns/set_per_ou", False):
            self.logger.info(
                "Creation of DHCP DNS policy has been disabled by"
                "ucsschool/import/generate/policy/dhcp/dns/set_per_ou"
            )
            return
        ou = self.name
        ou_lower = ou.lower()
        #  Determine list of available OUs.
        filter_s = filter_format("(&(objectClass=ucsschoolOrganizationalUnit)(ou=%s))", [ou_lower])
        ou_dns = [obj.dn async for obj in udm.get(self.Meta.udm_module).search(filter_s)]
        dhcp_dns_mod = udm.get("policies/dhcp_dns")
        for ou_dn in ou_dns:
            policy = DHCPDNSPolicy(
                name="dhcp-dns-{}".format(ou_lower),
                school=ou,
                empty_attributes=["univentionDhcpDomainNameServers"],
            )
            if not await policy.exists(udm):
                policy.position = "cn=policies,{}".format(ou_dn)
                await policy.create(udm)
            else:
                self.logger.warning("DHCPDNSPolicy for {} exists already.".format(self.name))

            dhcp_dns_policy_dn = "cn=dhcp-dns-{},cn=policies,{}".format(ou_lower, ou_dn)
            # In a single server environment, the master is the DNS server.
            if (
                ucr.is_true("ucsschool/singlemaster", False)
                and ucr.get("server/role") == "domaincontroller_master"
            ):
                policy = await dhcp_dns_mod.get(dhcp_dns_policy_dn)
                policy.props.domain_name_servers = str(Interfaces().get_default_ip_address().ip)
                policy.props.domain_name = ucr["domainname"]
                await policy.save()

            container_mod = udm.get("container/cn")
            container = await container_mod.get("cn=dhcp,{}".format(ou_dn))
            container.policies.append(dhcp_dns_policy_dn)
            await container.save()

    async def create_import_group(self, lo: UDM) -> None:
        """
        Create the OU-import-all group, which enables user to run
        an import, add the UMC policy schoolimport-all to it
        and set roles and options which are used in the import.
        formerly in shell hook 53importgroup_create
        """
        if not ucr.is_true("ucsschool/import/generate/import/group", False):
            self.logger.info(
                "creation of the Import Group has been disabled by"
                "ucsschool/import/generate/import/group"
            )
            return
        ou = self.name
        ou_dn = self.dn
        ou_import_group = "cn={}-import-all,cn=groups,{}".format(ou, ou_dn)
        group = Group.cache("{}-import-all".format(ou), ou)
        group.position = "cn=groups,{}".format(ou_dn)
        group.name = "{}-import-all".format(ou)
        group.description = "Default group for UCS@school user imports"
        await group.create(lo)
        await group.add_umc_policy(
            policy_dn="cn=schoolimport-all,cn=UMC,cn=policies,{}".format(ucr["ldap/base"]), lo=lo
        )

        group_mod = lo.get("groups/group")
        group = await group_mod.get(ou_import_group)
        group.options.append("ucsschoolImportGroup")
        group.props.ucsschoolImportSchool = ou
        # comment: teacher_and_staff is a proper role and only used in the import context.
        group.props.ucsschoolImportRole.extend(
            [role_student, role_staff, "teacher_and_staff", role_teacher]
        )
        await group.save()

    async def create_exam_group(self, lo: UDM) -> None:
        """
        Creates the exam users container cn=examusers and the
        OU-specific group, e.g. DEMOSCHOOL-Klassenarbeit for the school.
        formerly in shell hook 60schoolexam-master.
        """
        ldap_base = ucr["ldap/base"]

        # create exam container
        examusers = ucr.get("ucsschool/ldap/default/container/exam", "examusers")
        district = self.get_district()
        if not district:
            district = ""
        exam_container = Container(name=examusers, school=self.school)
        exam_container.position = "ou={}{},{}".format(self.name, district, ldap_base)
        exam_container.name = examusers
        await exam_container.create(lo)
        self.logger.debug("Exam container {} created.".format(exam_container.name))

        # create exam group
        examgroupname_template = ucr.get(
            "ucsschool/ldap/default/groupname/exam", "OU%(ou)s-Klassenarbeit"
        )
        ucr_value_keywords = {"ou": self.name}
        examgroupname = examgroupname_template % ucr_value_keywords
        group = Group.cache(examgroupname, self.name)
        group.position = "cn=ucsschool,cn=groups,{}".format(ldap_base)
        group.name = examgroupname
        group.description = "Default group for UCS@school user imports"
        await group.create(lo)
        self.logger.debug("Exam group {} created.".format(group.name))

    def __str__(self):
        return self.name

    class Meta:
        udm_module = "container/ou"
        udm_filter = "objectClass=ucsschoolOrganizationalUnit"
        ldap_name_part = "ou"
