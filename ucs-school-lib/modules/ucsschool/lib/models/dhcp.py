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

import ipaddress
from typing import TYPE_CHECKING, List, Optional  # noqa: F401

from ldap.dn import dn2str, str2dn
from ldap.filter import filter_format

from .attributes import (
    Attribute,
    BroadcastAddress,
    DHCPServerName,
    DHCPServiceAttribute,
    DHCPServiceName,
    DHCPSubnetMask,
    DHCPSubnetName,
)
from .base import UCSSchoolHelperAbstractClass
from .utils import _, ucr

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType  # noqa: F401

    from .base import UdmObject  # noqa: F401


class DHCPService(UCSSchoolHelperAbstractClass):
    name = DHCPServiceName(_("Service"))  # type: str
    hostname = Attribute(_("Hostname"))  # type: str
    domainname = Attribute(_("Domain"))  # type: str

    def do_create(self, udm_obj, lo):  # type: (UdmObject, LoType) -> None
        udm_obj.options.append("options")
        udm_obj["option"] = ['wpad "http://%s.%s/proxy.pac"' % (self.hostname, self.domainname)]
        super(DHCPService, self).do_create(udm_obj, lo)

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).dhcp

    def add_server(self, dc_name, lo, force_dhcp_server_move=False):
        # type: (str, LoType, Optional[bool]) -> None
        """
        Create the given DHCP server within the DHCP service. If the DHCP server
        object already exists somewhere else within the LDAP tree, it may be moved
        to the DHCP service.

        PLEASE NOTE:
        In multiserver environments an existing DHCP server object is always
        moved to the current DHCP service. In single server environments the
        DHCP server object is *ONLY* moved, if the UCR variable dhcpd/ldap/base
        matches to the current DHCP service.
        """
        from ucsschool.lib.models.school import School

        # create dhcp-server if not exsistant
        school = School.cache(self.school)
        dhcp_server = DHCPServer(name=dc_name, school=school.name, dhcp_service=self)
        existing_dhcp_server_dn = DHCPServer.find_any_dn_with_name(dc_name, lo)
        if existing_dhcp_server_dn:
            self.logger.info("DHCP server %s exists!", existing_dhcp_server_dn)
            old_dhcp_server_container = lo.parentDn(existing_dhcp_server_dn)
            dhcpd_ldap_base = ucr.get("dhcpd/ldap/base", "")
            # only move if
            # - forced via kwargs OR
            # - in multiserver environments OR
            # - desired dhcp server DN matches with UCR config
            if (
                force_dhcp_server_move
                or not ucr.is_true("ucsschool/singlemaster", False)
                or dhcp_server.dn.lower().endswith(",%s" % dhcpd_ldap_base.lower())
            ):
                # move if existing DN does not match with desired DN
                if existing_dhcp_server_dn != dhcp_server.dn:
                    # move existing dhcp server object to OU/DHCP service
                    self.logger.info(
                        "DHCP server %s not in school %r! Removing and creating new one at %s!",
                        existing_dhcp_server_dn,
                        school,
                        dhcp_server.dn,
                    )
                    old_superordinate = DHCPServer.find_udm_superordinate(existing_dhcp_server_dn, lo)
                    old_dhcp_server = DHCPServer.from_dn(
                        existing_dhcp_server_dn, None, lo, superordinate=old_superordinate
                    )
                    old_dhcp_server.remove(lo)
                    dhcp_server.create(lo)

            # copy subnets
            # find local interfaces
            interfaces = []
            for interface_name in {
                key.split("/")[1] for key in ucr.keys() if key.startswith("interfaces/eth")
            }:
                try:
                    address = ipaddress.IPv4Network(
                        u"%s/%s"
                        % (
                            ucr["interfaces/%s/address" % interface_name],
                            ucr["interfaces/%s/netmask" % interface_name],
                        ),
                        strict=False,
                    )
                    interfaces.append(address)
                except ValueError as exc:
                    self.logger.info("Skipping invalid interface %s:\n%s", interface_name, exc)
            subnet_dns = DHCPSubnet.find_all_dns_below_base(old_dhcp_server_container, lo)
            for subnet_dn in subnet_dns:
                dhcp_service = DHCPSubnet.find_udm_superordinate(subnet_dn, lo)
                dhcp_subnet = DHCPSubnet.from_dn(subnet_dn, self.school, lo, superordinate=dhcp_service)
                subnet = dhcp_subnet.get_ipv4_subnet()
                if subnet in interfaces:  # subnet matches any local subnet
                    self.logger.info("Creating new DHCPSubnet from %s", subnet_dn)
                    new_dhcp_subnet = DHCPSubnet(**dhcp_subnet.to_dict())
                    new_dhcp_subnet.dhcp_service = self
                    new_dhcp_subnet.position = new_dhcp_subnet.get_own_container()
                    new_dhcp_subnet.set_dn(new_dhcp_subnet.dn)
                    new_dhcp_subnet.create(lo)
                else:
                    self.logger.info("Skipping non-local subnet %s", subnet)
        else:
            self.logger.info("No DHCP server named %s found! Creating new one!", dc_name)
            dhcp_server.create(lo)

    def get_servers(self, lo):  # type: (LoType) -> List[DHCPServer]
        ret = []
        for dhcp_server in DHCPServer.get_all(lo, self.school, superordinate=self):
            dhcp_server.dhcp_service = self
            ret.append(dhcp_server)
        return ret

    class Meta:
        udm_module = "dhcp/service"


class AnyDHCPService(DHCPService):
    school = None

    @classmethod
    def get_container(cls, school=None):  # type: (str) -> str
        return ucr.get("ldap/base")

    def get_servers(self, lo):  # type: (LoType) -> List[DHCPServer]
        old_name = self.name
        old_position = self.position
        old_dn = str2dn(self.old_dn or self.dn)
        self.position = dn2str(old_dn[1:])
        self.name = old_dn[0][0][1]
        try:
            return super(AnyDHCPService, self).get_servers(lo)
        finally:
            self.position = old_position
            self.name = old_name


class DHCPServer(UCSSchoolHelperAbstractClass):
    name = DHCPServerName(_("Server name"))  # type: str
    dhcp_service = DHCPServiceAttribute(_("DHCP service"), required=True)  # type: DHCPService

    def get_own_container(self):  # type: () -> str
        if self.dhcp_service:
            return self.dhcp_service.dn

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).dhcp

    def get_superordinate(self, lo):  # type: (LoType) -> UdmObject
        if self.dhcp_service:
            return self.dhcp_service.get_udm_object(lo)

    @classmethod
    def find_any_dn_with_name(cls, name, lo):  # type: (str, LoType) -> str
        cls.logger.debug("Searching first dhcpServer with cn=%s", name)
        try:
            dn = lo.searchDn(
                filter=filter_format("(&(objectClass=dhcpServer)(cn=%s))", [name]),
                base=ucr.get("ldap/base"),
            )[0]
        except IndexError:
            dn = None
        cls.logger.debug("... %r found", dn)
        return dn

    class Meta:
        udm_module = "dhcp/server"
        name_is_unique = True


class DHCPSubnet(UCSSchoolHelperAbstractClass):
    name = DHCPSubnetName(_("Subnet address"))  # type: str
    subnet_mask = DHCPSubnetMask(_("Netmask"))  # type: str
    broadcast = BroadcastAddress(_("Broadcast"))  # type: str
    dhcp_service = DHCPServiceAttribute(_("DHCP service"), required=True)  # type: DHCPService

    def get_own_container(self):  # type: () -> str
        if self.dhcp_service:
            return self.dhcp_service.dn

    @classmethod
    def get_container(cls, school):  # type: (str) -> str
        return cls.get_search_base(school).dhcp

    def get_superordinate(self, lo):  # type: (LoType) -> UdmObject
        if self.dhcp_service:
            return self.dhcp_service.get_udm_object(lo)

    def get_ipv4_subnet(self):  # type: () -> ipaddress.IPv4Network
        network_str = u"%s/%s" % (self.name, self.subnet_mask)
        try:
            return ipaddress.IPv4Network(network_str, strict=False)
        except ValueError as exc:
            self.logger.info("%r is no valid IPv4Network:\n%s", network_str, exc)

    @classmethod
    def find_all_dns_below_base(cls, dn, lo):  # type: (str, LoType) -> List[str]
        cls.logger.debug("Searching all univentionDhcpSubnet in %r", dn)
        return lo.searchDn(filter="(objectClass=univentionDhcpSubnet)", base=dn)

    class Meta:
        udm_module = "dhcp/subnet"
