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

from typing import List, Optional

import ipaddr
from ldap.dn import dn2str, str2dn
from ldap.filter import filter_format

from udm_rest_client import UDM, UdmObject
from univention.admin.uldap_docker import parentDn

from .attributes import (
    Attribute,
    BroadcastAddress,
    DHCPServerName,
    DHCPServiceAttribute,
    DHCPServiceName,
    DHCPSubnetMask,
    DHCPSubnetName,
)
from .base import SuperOrdinateType, UCSSchoolHelperAbstractClass
from .utils import _, ucr


class DHCPService(UCSSchoolHelperAbstractClass):
    name: str = DHCPServiceName(_("Service"))
    hostname: str = Attribute(_("Hostname"))
    domainname: str = Attribute(_("Domain"))

    async def do_create(self, udm_obj: UdmObject, lo: UDM) -> None:
        udm_obj.options["options"] = True
        udm_obj.props.option = ['wpad "http://%s.%s/proxy.pac"' % (self.hostname, self.domainname)]
        await super(DHCPService, self).do_create(udm_obj, lo)

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).dhcp

    async def add_server(self, dc_name: str, lo: UDM, force_dhcp_server_move: bool = False) -> None:
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
        existing_dhcp_server_dn = await DHCPServer.find_any_dn_with_name(dc_name, lo)
        if existing_dhcp_server_dn:
            self.logger.info("DHCP server %s exists!", existing_dhcp_server_dn)
            old_dhcp_server_container = parentDn(existing_dhcp_server_dn)
            dhcpd_ldap_base = ucr.get("dhcpd/ldap/base", "")
            # only move if
            # - forced via kwargs OR
            # - in multiserver environments OR
            # - desired dhcp server DN matches with UCR config
            if (
                force_dhcp_server_move
                or not ucr.is_true("ucsschool/singlemaster", False)
                or dhcp_server.dn.endswith(",%s" % dhcpd_ldap_base)
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
                    old_superordinate = await DHCPServer.find_udm_superordinate(
                        existing_dhcp_server_dn, lo
                    )
                    old_dhcp_server = await DHCPServer.from_dn(
                        existing_dhcp_server_dn, None, lo, superordinate=old_superordinate
                    )
                    await old_dhcp_server.remove(lo)
                    await dhcp_server.create(lo)

            # copy subnets
            # find local interfaces
            interfaces = []
            for interface_name in set(
                [key.split("/")[1] for key in ucr.keys() if key.startswith("interfaces/eth")]
            ):
                try:
                    address = ipaddr.IPv4Network(
                        "%s/%s"
                        % (
                            ucr["interfaces/%s/address" % interface_name],
                            ucr["interfaces/%s/netmask" % interface_name],
                        )
                    )
                    interfaces.append(address)
                except ValueError as exc:
                    self.logger.info("Skipping invalid interface %s:\n%s", interface_name, exc)
            subnet_dns = await DHCPSubnet.find_all_dns_below_base(old_dhcp_server_container, lo)
            for subnet_dn in subnet_dns:
                dhcp_service = await DHCPSubnet.find_udm_superordinate(subnet_dn, lo)
                dhcp_subnet = await DHCPSubnet.from_dn(
                    subnet_dn, self.school, lo, superordinate=dhcp_service
                )
                subnet = dhcp_subnet.get_ipv4_subnet()
                if subnet in interfaces:  # subnet matches any local subnet
                    self.logger.info("Creating new DHCPSubnet from %s", subnet_dn)
                    new_dhcp_subnet = DHCPSubnet(**dhcp_subnet.to_dict())
                    new_dhcp_subnet.dhcp_service = self
                    new_dhcp_subnet.position = new_dhcp_subnet.get_own_container()
                    new_dhcp_subnet.set_dn(new_dhcp_subnet.dn)
                    await new_dhcp_subnet.create(lo)
                else:
                    self.logger.info("Skipping non-local subnet %s", subnet)
        else:
            self.logger.info("No DHCP server named %s found! Creating new one!", dc_name)
            await dhcp_server.create(lo)

    async def get_servers(self, lo: UDM) -> List["DHCPServer"]:
        ret = []
        for dhcp_server in await DHCPServer.get_all(lo, self.school, superordinate=self):
            dhcp_server.dhcp_service = self
            ret.append(dhcp_server)
        return ret

    class Meta:
        udm_module = "dhcp/service"


class AnyDHCPService(DHCPService):
    school = None

    @classmethod
    def get_container(cls, school: str = None) -> str:
        return ucr.get("ldap/base")

    async def get_servers(self, lo: UDM) -> List["DHCPServer"]:
        old_name = self.name
        old_position = self.position
        old_dn = str2dn(self.old_dn or self.dn)
        self.position = dn2str(old_dn[1:])
        self.name = old_dn[0][0][1]
        try:
            return await super(AnyDHCPService, self).get_servers(lo)
        finally:
            self.position = old_position
            self.name = old_name


class DHCPServer(UCSSchoolHelperAbstractClass):
    name: str = DHCPServerName(_("Server name"))
    dhcp_service: DHCPService = DHCPServiceAttribute(_("DHCP service"), required=True)

    async def do_create(self, udm_obj: UdmObject, lo: UDM) -> None:
        if udm_obj.dn:
            # Setting udm_obj.superordinate leads to udm_obj.dn being set. That makes the UDM REST API
            # client believe the object exists and should be moved. For creation it must be None.
            udm_obj.dn = None
        await super(DHCPServer, self).do_create(udm_obj, lo)

    def get_own_container(self) -> str:
        if self.dhcp_service:
            return self.dhcp_service.dn

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).dhcp

    async def get_superordinate(self, lo: UDM) -> Optional[SuperOrdinateType]:
        if self.dhcp_service:
            return await self.dhcp_service.get_udm_object(lo)

    @classmethod
    async def find_any_dn_with_name(cls, name: str, lo: UDM) -> str:
        cls.logger.debug("Searching first dhcpServer with cn=%s", name)
        mod = lo.get(cls.Meta.udm_module)
        objs = [obj async for obj in mod.search(filter_format("cn=%s", (name,)))]
        if objs:
            dn = objs[0].dn
        else:
            dn = None
        cls.logger.debug("... %r found", dn)
        return dn

    class Meta:
        udm_module = "dhcp/server"
        name_is_unique = True


class DHCPSubnet(UCSSchoolHelperAbstractClass):
    name: str = DHCPSubnetName(_("Subnet address"))
    subnet_mask: str = DHCPSubnetMask(_("Netmask"))
    broadcast: str = BroadcastAddress(_("Broadcast"))
    dhcp_service: DHCPService = DHCPServiceAttribute(_("DHCP service"), required=True)

    def get_own_container(self) -> str:
        if self.dhcp_service:
            return self.dhcp_service.dn

    @classmethod
    def get_container(cls, school: str) -> str:
        return cls.get_search_base(school).dhcp

    async def get_superordinate(self, lo: UDM) -> Optional[SuperOrdinateType]:
        if self.dhcp_service:
            return await self.dhcp_service.get_udm_object(lo)

    def get_ipv4_subnet(self) -> ipaddr.IPv4Network:
        network_str = "%s/%s" % (self.name, self.subnet_mask)
        try:
            return ipaddr.IPv4Network(network_str)
        except ValueError as exc:
            self.logger.info("%r is no valid IPv4Network:\n%s", network_str, exc)

    @classmethod
    async def find_all_dns_below_base(cls, dn: str, lo: UDM) -> List[str]:
        cls.logger.debug("Searching all univentionDhcpSubnet in %r", dn)
        mod = lo.get(cls.Meta.udm_module)
        return [obj.dn async for obj in mod.search(base=dn)]

    class Meta:
        udm_module = "dhcp/subnet"
