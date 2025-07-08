#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school python lib: models
#
# SPDX-FileCopyrightText: 2014-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from ipaddress import AddressValueError, IPv4Interface, NetmaskValueError

from ldap.dn import escape_dn_chars

from univention.admin.uexceptions import noObject

from .attributes import Netmask, NetworkAttribute, NetworkBroadcastAddress, SubnetName
from .base import UCSSchoolHelperAbstractClass
from .dhcp import DHCPSubnet
from .utils import _, ucr


class Network(UCSSchoolHelperAbstractClass):
    netmask = Netmask(_("Netmask"))
    network = NetworkAttribute(_("Network"))
    broadcast = NetworkBroadcastAddress(_("Broadcast"))

    _netmask_cache = {}

    @classmethod
    def get_container(cls, school):
        return cls.get_search_base(school).networks

    def get_subnet(self):
        # WORKAROUND for Bug #14795
        subnetbytes = 0
        netmask_parts = self.netmask.split(".")
        for part in netmask_parts:
            if part == "255":
                subnetbytes += 1
            else:
                break
        return ".".join(self.network.split(".")[:subnetbytes])

    def create_without_hooks(self, lo, validate):
        dns_reverse_zone = DNSReverseZone.cache(self.get_subnet())
        dns_reverse_zone.create(lo)

        dhcp_service = self.get_school_obj(lo).get_dhcp_service()
        dhcp_subnet = DHCPSubnet(
            name=self.network,
            school=self.school,
            subnet_mask=self.netmask,
            broadcast=self.broadcast,
            dhcp_service=dhcp_service,
        )
        dhcp_subnet.create(lo)

        # TODO:
        # set netbios and router for dhcp subnet
        # if defaultrouter:
        # 	print 'setting default router'
        # 	set_router_for_subnet (network, defaultrouter, schoolNr)

        # if netbiosserver:
        # 	print 'setting netbios server'
        # 	set_netbiosserver_for_subnet (network, netbiosserver, schoolNr)

        # set default value for nameserver
        # if nameserver:
        # 	print 'setting nameserver'
        # 	set_nameserver_for_subnet (network, nameserver, schoolNr)

        return super(Network, self).create_without_hooks(lo, validate)

    def do_create(self, udm_obj, lo):
        from ucsschool.lib.models.school import School

        # TODO:
        # if iprange:
        # 	object['ipRange']=[[str(iprange[0]), str(iprange[1])]]
        # TODO: this is a DHCPServer created when school is created (not implemented yet)
        udm_obj["dhcpEntryZone"] = "cn=%s,cn=dhcp,%s" % (
            escape_dn_chars(self.school),
            School.cache(self.school).dn,
        )
        udm_obj["dnsEntryZoneForward"] = "zoneName=%s,cn=dns,%s" % (
            escape_dn_chars(ucr.get("domainname")),
            ucr.get("ldap/base"),
        )
        reversed_subnet = ".".join(reversed(self.get_subnet().split(".")))
        udm_obj["dnsEntryZoneReverse"] = "zoneName=%s.in-addr.arpa,cn=dns,%s" % (
            escape_dn_chars(reversed_subnet),
            ucr.get("ldap/base"),
        )
        return super(Network, self).do_create(udm_obj, lo)

    @classmethod
    def invalidate_cache(cls):
        super(Network, cls).invalidate_cache()
        cls._netmask_cache.clear()

    @classmethod
    def get_netmask(cls, dn, school, lo):
        if dn not in cls._netmask_cache:
            try:
                network = cls.from_dn(dn, school, lo)
            except noObject:
                return
            netmask = network.netmask  # e.g. '24'
            network_str = "0.0.0.0/%s" % netmask
            try:
                ipv4_network = IPv4Interface(network_str)
            except (AddressValueError, NetmaskValueError, ValueError):
                cls.logger.warning("Unparsable network: %r", network_str)
            else:
                netmask = str(ipv4_network.netmask)  # e.g. '255.255.255.0'
            cls.logger.debug("Network mask: %r is %r", dn, netmask)
            cls._netmask_cache[dn] = netmask
        return cls._netmask_cache[dn]

    class Meta:
        udm_module = "networks/network"


class DNSReverseZone(UCSSchoolHelperAbstractClass):
    name = SubnetName(_("Subnet"))
    school = None

    @classmethod
    def get_container(cls, school=None):
        return "cn=dns,%s" % ucr.get("ldap/base")

    def do_create(self, udm_obj, lo):
        udm_obj["nameserver"] = ucr.get("ldap/master")
        udm_obj["contact"] = "root@%s" % ucr.get("domainname")
        return super(DNSReverseZone, self).do_create(udm_obj, lo)

    class Meta:
        udm_module = "dns/reverse_zone"
