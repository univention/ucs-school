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

import re
from ipaddress import AddressValueError, IPv4Interface, NetmaskValueError
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type  # noqa: F401

import six
from ldap.filter import filter_format

from univention.admin.uexceptions import nextFreeIp

from ..roles import (
    create_ucsschool_role_string,
    role_dc_slave_admin,
    role_dc_slave_edu,
    role_ip_computer,
    role_linux_computer,
    role_mac_computer,
    role_teacher_computer,
    role_ubuntu_computer,
    role_win_computer,
)
from .attributes import Attribute, Groups, InventoryNumber, IPAddress, MACAddress, SubnetMask
from .base import MultipleObjectsError, RoleSupportMixin, UCSSchoolHelperAbstractClass
from .dhcp import AnyDHCPService, DHCPServer
from .group import BasicGroup
from .network import Network
from .utils import _, ucr

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType  # noqa: F401

    from .base import SuperOrdinateType, UdmObject  # noqa: F401


class AnyComputer(UCSSchoolHelperAbstractClass):
    @classmethod
    def get_container(cls, school=None):  # type: (Optional[str]) -> str
        from ucsschool.lib.models.school import School

        if school:
            return School.cache(school).dn
        return ucr.get("ldap/base")

    class Meta:
        udm_module = "computers/computer"


class SchoolDC(UCSSchoolHelperAbstractClass):
    # NOTE: evaluate filter (&(service=UCS@school)(service=UCS@school Education))
    # UCS@school Administration vs. group memberships

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return "cn=dc,cn=server,%s" % cls.get_search_base(school).computers

    @classmethod
    def get_class_for_udm_obj(cls, udm_obj, school):  # type: (UdmObject, str) -> Type[SchoolDC]
        try:
            univention_object_class = udm_obj["univentionObjectClass"]
        except KeyError:
            univention_object_class = None
        if univention_object_class == "computers/domaincontroller_slave":
            return SchoolDCSlave
        return cls


class SchoolDCSlave(RoleSupportMixin, SchoolDC):
    groups = Groups(_("Groups"))  # type: List[str]

    def do_create(self, udm_obj, lo):  # type: (UdmObject, LoType) -> None
        udm_obj["unixhome"] = "/dev/null"
        udm_obj["shell"] = "/bin/bash"
        udm_obj["primaryGroup"] = BasicGroup.cache("DC Slave Hosts").dn
        return super(SchoolDCSlave, self).do_create(udm_obj, lo)

    def _alter_udm_obj(self, udm_obj):  # type: (UdmObject) -> None
        if self.groups:
            for group in self.groups:
                if group not in udm_obj["groups"]:
                    udm_obj["groups"].append(group)
        return super(SchoolDCSlave, self)._alter_udm_obj(udm_obj)

    def get_schools_from_udm_obj(self, udm_obj):  # type: (UdmObject) -> str
        # fixme: no idea how to find out old school
        return self.school

    def move_without_hooks(self, lo, udm_obj=None, force=False):
        # type: (LoType, Optional[UdmObject], Optional[bool]) -> bool
        try:
            if udm_obj is None:
                try:
                    udm_obj = self.get_only_udm_obj(lo, filter_format("cn=%s", (self.name,)))
                except MultipleObjectsError:
                    self.logger.error(
                        'Found more than one Replica Directory Node with hostname "%s"', self.name
                    )
                    return False
                if udm_obj is None:
                    self.logger.error('Cannot find Replica Directory Node with hostname "%s"', self.name)
                    return False
            old_dn = udm_obj.dn
            school = self.get_school_obj(lo)
            group_dn = school.get_administrative_group_name("educational", ou_specific=True, as_dn=True)
            if group_dn not in udm_obj["groups"]:
                self.logger.error("%r has no LDAP access to %r", self, school)
                return False
            if old_dn == self.dn:
                self.logger.info(
                    'Replica Directory Node "%s" is already located in "%s" - stopping here',
                    self.name,
                    self.school,
                )
            self.set_dn(old_dn)
            if self.exists_outside_school(lo):
                if not force:
                    self.logger.error(
                        'Replica Directory Node "%s" is located in another OU - %s',
                        self.name,
                        udm_obj.dn,
                    )
                    self.logger.error("Use force=True to override")
                    return False
            if school is None:
                self.logger.error(
                    "Cannot move Replica Directory Node object - School does not exist: %r", school
                )
                return False
            self.modify_without_hooks(lo)
            if school.class_share_file_server == old_dn:
                school.class_share_file_server = self.dn
            if school.home_share_file_server == old_dn:
                school.home_share_file_server = self.dn
            school.modify_without_hooks(lo)

            removed = False
            # find dhcp server object by checking all dhcp service objects
            for dhcp_service in AnyDHCPService.get_all(lo, None):
                for dhcp_server in dhcp_service.get_servers(lo):
                    if (
                        dhcp_server.name.lower() == self.name.lower()
                        and not dhcp_server.dn.lower().endswith(",%s" % school.dn.lower())
                    ):
                        dhcp_server.remove(lo)
                        removed = True

            if removed:
                own_dhcp_service = school.get_dhcp_service()

                dhcp_server = DHCPServer(
                    name=self.name, school=self.school, dhcp_service=own_dhcp_service
                )
                dhcp_server.create(lo)

            self.logger.info("Move complete")
            self.logger.warning("The Replica Directory Node has to be rejoined into the domain!")
        finally:
            self.invalidate_cache()
        return True

    def update_ucsschool_roles(self, lo):  # type: (LoType) -> None
        """
        Update roles using membership in groups 'OU*-DC-Edukativnetz' and 'OU*-DC-Verwaltungsnetz'
        instead of a 'schools' attribute.
        """
        filter_s = filter_format(
            "(&(objectClass=univentionGroup)(memberUid=%s$)(cn=OU*-DC-*netz))", (self.name,)
        )
        groups = BasicGroup.get_all(lo, None, filter_s)
        # handle only dc_admin and dc_edu roles, ignore others
        self.ucsschool_roles = [
            role
            for role in self.ucsschool_roles
            if not role.startswith((role_dc_slave_admin, role_dc_slave_edu))
        ]
        for group in groups:
            matches = re.match(r"OU(?P<ou>.+)-DC-(?P<type>.+)", group.name)
            if matches:
                ou = matches.groupdict()["ou"]
                dc_type = matches.groupdict()["type"]
                role = role_dc_slave_admin if dc_type == "Verwaltungsnetz" else role_dc_slave_edu
                self.ucsschool_roles.append(create_ucsschool_role_string(role, ou))

    class Meta:
        udm_module = "computers/domaincontroller_slave"
        name_is_unique = True
        allow_school_change = True


class SchoolComputer(UCSSchoolHelperAbstractClass):
    ip_address = IPAddress(_("IP address"), required=True)  # type: List[str]
    subnet_mask = SubnetMask(_("Subnet mask"))  # type: str
    mac_address = MACAddress(_("MAC address"), required=True)  # type: List[str]
    inventory_number = InventoryNumber(_("Inventory number"))  # type: str
    zone = Attribute(_("Zone"))  # type: str

    type_name = _("Computer")

    DEFAULT_PREFIX_LEN = 24  # 255.255.255.0

    @classmethod
    def lookup(cls, lo, school, filter_s="", superordinate=None):
        # type: (LoType, str, Optional[str], Optional[SuperOrdinateType]) -> List[UdmObject]
        """
        This override limits the returned objects to actual ucsschoolComputers. Does not contain
        School Replica Directory Nodes and others anymore.
        """
        object_class_filter = "(objectClass=ucsschoolComputer)"
        if filter_s:
            school_computer_filter = "(&%s%s)" % (object_class_filter, filter_s)
        else:
            school_computer_filter = object_class_filter
        return super(SchoolComputer, cls).lookup(lo, school, school_computer_filter, superordinate)

    def get_inventory_numbers(self):  # type: () -> List[str]
        if isinstance(self.inventory_number, six.string_types):
            return [inv.strip() for inv in self.inventory_number.split(",")]
        if isinstance(self.inventory_number, (list, tuple)):
            return list(self.inventory_number)
        return []

    @property
    def teacher_computer(self):  # type: () -> bool
        """True if the computer is a teachers computer."""
        return create_ucsschool_role_string(role_teacher_computer, self.school) in self.ucsschool_roles

    @teacher_computer.setter
    def teacher_computer(self, new_value):  # type: (bool) -> None
        """Un/mark computer as a teachers computer."""
        role_str = create_ucsschool_role_string(role_teacher_computer, self.school)
        if new_value and role_str not in self.ucsschool_roles:
            self.ucsschool_roles.append(role_str)
        elif not new_value and role_str in self.ucsschool_roles:
            self.ucsschool_roles.remove(role_str)

    def _alter_udm_obj(self, udm_obj):  # type: (UdmObject) -> None
        super(SchoolComputer, self)._alter_udm_obj(udm_obj)
        inventory_numbers = self.get_inventory_numbers()
        if inventory_numbers:
            udm_obj["inventoryNumber"] = inventory_numbers
        ipv4_network = self.get_ipv4_network()
        if ipv4_network and len(udm_obj["ip"]) < 2:
            if self._ip_is_set_to_subnet(ipv4_network):
                self.logger.info(
                    "IP was set to subnet. Unsetting it on the computer so that UDM can do some magic: "
                    "Assign next free IP!"
                )
                udm_obj["ip"] = []
            else:
                udm_obj["ip"] = [str(ipv4_network.ip)]
            # set network after ip. Otherwise UDM does not do any
            #   nextIp magic...
            network = self.get_network()
            if network:
                # reset network, so that next line triggers free ip
                udm_obj.old_network = None
                try:
                    udm_obj["network"] = network.dn
                except nextFreeIp:
                    self.logger.error("Tried to set IP automatically, but failed! %r is full", network)
                    raise nextFreeIp(_("There are no free addresses left in the subnet!"))

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).computers

    def create(self, lo, validate=True):  # type: (LoType, Optional[bool]) -> bool
        if self.subnet_mask is None:
            self.subnet_mask = self.DEFAULT_PREFIX_LEN
        return super(SchoolComputer, self).create(lo, validate)

    def create_without_hooks(self, lo, validate):  # type: (LoType, bool) -> bool
        self.create_network(lo)
        return super(SchoolComputer, self).create_without_hooks(lo, validate)

    def modify_without_hooks(self, lo, validate=True, move_if_necessary=None):
        # type: (LoType, Optional[bool], Optional[bool]) -> bool
        self.create_network(lo)
        return super(SchoolComputer, self).modify_without_hooks(lo, validate, move_if_necessary)

    def get_ipv4_network(self):  # type: () -> IPv4Interface
        if self.subnet_mask is not None and len(self.ip_address) > 0:
            network_str = u"%s/%s" % (self.ip_address[0], self.subnet_mask)
        elif len(self.ip_address) > 0:
            network_str = u"%s" % (self.ip_address[0],)
        else:
            network_str = u""
        try:
            return IPv4Interface(network_str)
        except (AddressValueError, NetmaskValueError, ValueError):
            self.logger.warning("Unparsable network: %r", network_str)

    def _ip_is_set_to_subnet(self, ipv4_network=None):  # type: (IPv4Interface) -> bool
        ipv4_network = ipv4_network or self.get_ipv4_network()
        if ipv4_network:
            return ipv4_network.ip == ipv4_network.network.network_address

    def get_network(self):  # type: () -> Network
        ipv4_network = self.get_ipv4_network()
        if ipv4_network:
            network_name = "%s-%s" % (self.school.lower(), ipv4_network.network.network_address)
            network = str(ipv4_network.network.network_address)
            netmask = str(ipv4_network.netmask)
            broadcast = str(ipv4_network.network.broadcast_address)
            return Network.cache(
                network_name, self.school, network=network, netmask=netmask, broadcast=broadcast
            )

    def create_network(self, lo):  # type: (LoType) -> Network
        network = self.get_network()
        if network:
            network.create(lo)
        return network

    def validate(self, lo, validate_unlikely_changes=False):  # type: (LoType, Optional[bool]) -> None
        super(SchoolComputer, self).validate(lo, validate_unlikely_changes)
        for ip_address in self.ip_address:
            if AnyComputer.get_first_udm_obj(
                lo, filter_format("&(!(cn=%s))(ip=%s)", (self.name, ip_address))
            ):
                self.add_error(
                    "ip_address",
                    _(
                        "The ip address is already taken by another computer. Please change the ip "
                        "address."
                    ),
                )
        for mac_address in self.mac_address:
            if AnyComputer.get_first_udm_obj(
                lo, filter_format("&(!(cn=%s))(mac=%s)", (self.name, mac_address))
            ):
                self.add_error(
                    "mac_address",
                    _(
                        "The mac address is already taken by another computer. Please change the mac "
                        "address."
                    ),
                )
        own_network = self.get_network()
        own_network_ip4 = self.get_ipv4_network()
        if own_network and not own_network.exists(lo):
            self.add_warning(
                "subnet_mask",
                _(
                    "The specified IP and subnet mask will cause the creation of a new network during "
                    "the creation of the computer object."
                ),
            )
            networks = [
                (
                    network[1]["cn"][0].decode("UTF-8"),
                    IPv4Interface(
                        u"%s/%s"
                        % (
                            network[1]["univentionNetwork"][0].decode("utf-8"),
                            network[1]["univentionNetmask"][0].decode("utf-8"),
                        )
                    ),
                )
                for network in lo.search("(univentionObjectType=networks/network)")
            ]
            is_singlemaster = ucr.get("ucsschool/singlemaster", False)
            for network in networks:
                if is_singlemaster and network[0] == "default" and own_network_ip4 == network[1]:
                    # Bug #48099: jump conflict with default network in singleserver environment
                    continue
                if own_network_ip4.network.overlaps(network[1].network):
                    self.add_error(
                        "subnet_mask",
                        _("The newly created network would overlap with the existing network {}").format(
                            network[0]
                        ),
                    )

    @classmethod
    def get_class_for_udm_obj(cls, udm_obj, school):  # type: (UdmObject, str) -> Type[SchoolComputer]
        oc = udm_obj.lo.get(udm_obj.dn, ["objectClass"])
        object_classes = oc.get("objectClass", [])
        if b"univentionWindows" in object_classes:
            return WindowsComputer
        if b"univentionMacOSClient" in object_classes:
            return MacComputer
        if b"univentionClient" in object_classes:
            return IPComputer
        if b"univentionUbuntuClient" in object_classes:
            return UbuntuComputer
        if b"univentionLinuxClient" in object_classes:
            return LinuxComputer

    @classmethod
    def from_udm_obj(cls, udm_obj, school, lo):  # type: (UdmObject, str, LoType) -> SchoolComputer
        from ucsschool.lib.models.school import School

        obj = super(SchoolComputer, cls).from_udm_obj(udm_obj, school, lo)
        obj.ip_address = udm_obj["ip"]
        school_obj = School.cache(obj.school)  # type: School
        edukativnetz_group = school_obj.get_administrative_group_name(
            "educational", domain_controller=False, as_dn=True
        )
        if edukativnetz_group in udm_obj["groups"]:
            obj.zone = "edukativ"
        verwaltungsnetz_group = school_obj.get_administrative_group_name(
            "administrative", domain_controller=False, as_dn=True
        )
        if verwaltungsnetz_group in udm_obj["groups"]:
            obj.zone = "verwaltung"
        network_dn = udm_obj["network"]
        if network_dn:
            netmask = Network.get_netmask(network_dn, school, lo)
            obj.subnet_mask = netmask
        obj.inventory_number = ", ".join(udm_obj["inventoryNumber"])
        return obj

    def to_dict(self):  # type: () -> Dict[str, Any]
        ret = super(SchoolComputer, self).to_dict()
        ret["type_name"] = self.type_name
        ret["type"] = self._meta.udm_module_short
        return ret

    class Meta:
        udm_module = "computers/computer"
        name_is_unique = True


class WindowsComputer(RoleSupportMixin, SchoolComputer):
    type_name = _("Windows system")
    default_roles = [role_win_computer]

    class Meta(SchoolComputer.Meta):
        udm_module = "computers/windows"
        hook_path = "computer"


class MacComputer(RoleSupportMixin, SchoolComputer):
    type_name = _("Mac OS X")
    default_roles = [role_mac_computer]

    class Meta(SchoolComputer.Meta):
        udm_module = "computers/macos"
        hook_path = "computer"


class IPComputer(RoleSupportMixin, SchoolComputer):
    type_name = _("Device with IP address")
    default_roles = [role_ip_computer]

    class Meta(SchoolComputer.Meta):
        udm_module = "computers/ipmanagedclient"
        hook_path = "computer"


class UbuntuComputer(RoleSupportMixin, SchoolComputer):
    type_name = _("Ubuntu system")
    default_roles = [role_ubuntu_computer]

    class Meta(SchoolComputer.Meta):
        udm_module = "computers/ubuntu"
        hook_path = "computer"


class LinuxComputer(RoleSupportMixin, SchoolComputer):
    type_name = _("Linux system")
    default_roles = [role_linux_computer]

    class Meta(SchoolComputer.Meta):
        udm_module = "computers/linux"
        hook_path = "computer"
