# -*- coding: utf-8 -*-

from __future__ import print_function

import ipaddress
import os
import random
import subprocess
import tempfile

import univention.config_registry
import univention.testing.ucsschool.ucs_test_school as utu
from univention.testing import utils
from univention.testing.ucsschool.computer import random_ip
from univention.testing.ucsschool.importou import get_school_base

configRegistry = univention.config_registry.ConfigRegistry()
configRegistry.load()


def get_reverse_net(network, netmask):
    p = subprocess.Popen(
        [
            "/usr/bin/univention-ipcalc6",
            "--ip",
            network,
            "--netmask",
            netmask,
            "--output",
            "reverse",
            "--calcdns",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    (stdout, stderr) = p.communicate()

    output = stdout.decode("UTF-8").strip().split(".")
    output.reverse()

    return ".".join(output)


class Network:
    def __init__(self, school, prefixlen):
        assert prefixlen > 7
        assert prefixlen < 25

        self._net = ipaddress.IPv4Interface("%s/%s" % (random_ip(), prefixlen))
        self.network = str(self._net.network)
        self.iprange = "%s-%s" % (
            self._net.network.network_address + 1,
            self._net.network.network_address + 10,
        )
        self.defaultrouter = self._net.network.network_address + 1
        self.nameserver = self._net.network.network_address + 2
        self.netbiosserver = self._net.network.network_address + 8

        self.router_mode = False
        self.school = school
        self.name = "%s-%s" % (self.school, self._net.network.network_address)

        self.school_base = get_school_base(self.school)

        self.dn = "cn=%s,cn=networks,%s" % (self.name, self.school_base)

        self.dhcp_zone = "cn=%s,cn=dhcp,%s" % (self.school, self.school_base)
        self.dns_forward_zone = "zoneName=%s,cn=dns,%s" % (
            configRegistry.get("domainname"),
            configRegistry.get("ldap/base"),
        )
        reverse_subnet = get_reverse_net(
            str(self._net.network.network_address), str(self._net.network.netmask)
        )
        self.dns_reverse_zone = "zoneName=%s.in-addr.arpa,cn=dns,%s" % (
            reverse_subnet,
            configRegistry.get("ldap/base"),
        )

    def __str__(self):
        delimiter = "\t"
        line = self.school
        line += delimiter
        line += self.network
        line += delimiter
        if self.iprange:
            line += self.iprange
        line += delimiter
        line += str(self.defaultrouter)
        line += delimiter
        line += str(self.nameserver)
        line += delimiter
        line += str(self.netbiosserver)
        return line

    def expected_attributes(self):
        attr = {
            "cn": [self.name],
            "univentionNetmask": [str(self._net.network.prefixlen)],
            "univentionNetwork": [str(self._net.network.network_address)],
            "univentionDnsForwardZone": [self.dns_forward_zone],
            "univentionDnsReverseZone": [self.dns_reverse_zone],
        }
        if self.iprange:
            attr["univentionIpRange"] = [self.iprange.replace("-", " ")]
        return attr

    def verify(self):
        print("verify network: %s" % self.network)

        utils.verify_ldap_object(self.dn, expected_attr=self.expected_attributes(), should_exist=True)
        utils.verify_ldap_object(self.dns_forward_zone, should_exist=True)
        utils.verify_ldap_object(self.dns_reverse_zone, should_exist=True)
        utils.verify_ldap_object(self.dhcp_zone, should_exist=True)

        lo = univention.uldap.getMachineConnection()
        search_filter = (
            "(&(cn=%s)(objectClass=univentionDhcpSubnet))" % self._net.network.network_address
        )
        subnet_dn = lo.searchDn(
            base=self.dhcp_zone,
            filter=search_filter,
            unique=True,
            required=True,
        )[0]

        if self.defaultrouter:
            defaultrouter_policy_dn = "cn=%s,cn=routing,cn=dhcp,cn=policies,%s" % (
                self.name,
                self.school_base,
            )
            utils.verify_ldap_object(
                defaultrouter_policy_dn,
                expected_attr={"univentionDhcpRouters": [str(self.defaultrouter)]},
                should_exist=True,
            )
            utils.verify_ldap_object(
                subnet_dn,
                expected_attr={"univentionPolicyReference": [defaultrouter_policy_dn]},
                strict=False,
                should_exist=True,
            )
        if self.nameserver and not self.router_mode:
            nameserver_policy_dn = "cn=%s,cn=dns,cn=dhcp,cn=policies,%s" % (self.name, self.school_base)
            utils.verify_ldap_object(
                nameserver_policy_dn,
                expected_attr={
                    "univentionDhcpDomainName": [configRegistry.get("domainname")],
                    "univentionDhcpDomainNameServers": [str(self.nameserver)],
                },
                should_exist=True,
            )
            utils.verify_ldap_object(
                subnet_dn,
                expected_attr={"univentionPolicyReference": [nameserver_policy_dn]},
                strict=False,
                should_exist=True,
            )
        if self.netbiosserver and not self.router_mode:
            netbios_policy_dn = "cn=%s,cn=netbios,cn=dhcp,cn=policies,%s" % (self.name, self.school_base)
            utils.verify_ldap_object(
                netbios_policy_dn,
                expected_attr={
                    "univentionDhcpNetbiosNodeType": ["8"],
                    "univentionDhcpNetbiosNameServers": [str(self.netbiosserver)],
                },
                should_exist=True,
            )
            utils.verify_ldap_object(
                subnet_dn,
                expected_attr={"univentionPolicyReference": [netbios_policy_dn]},
                strict=False,
                should_exist=True,
            )

    def set_mode_to_router(self):
        self.router_mode = True


class ImportFile:
    def __init__(self, use_cli_api, use_python_api):
        self.router_mode = False
        self.use_cli_api = use_cli_api
        self.use_python_api = use_python_api
        self.import_fd, self.import_file = tempfile.mkstemp()
        os.close(self.import_fd)

    def write_import(self, data):
        self.import_fd = os.open(self.import_file, os.O_RDWR | os.O_CREAT)
        os.write(self.import_fd, data.encode("utf-8"))
        os.close(self.import_fd)

    def run_import(self, data):
        try:
            self.write_import(data)
            if self.use_cli_api:
                self._run_import_via_cli()
            elif self.use_python_api:
                self._run_import_via_python_api()
            print("SCHOOL DATA     : %s" % data)
        finally:
            os.remove(self.import_file)

    def _run_import_via_cli(self):
        if self.router_mode:
            cmd_block = ["/usr/share/ucs-school-import/scripts/import_router", self.import_file]
        else:
            cmd_block = ["/usr/share/ucs-school-import/scripts/import_networks", self.import_file]

        print("cmd_block: %r" % cmd_block)
        subprocess.check_call(cmd_block)

    def _run_import_via_python_api(self):
        raise NotImplementedError()

    def set_mode_to_router(self):
        self.router_mode = True


class NetworkImport:
    def __init__(self, ou_name, nr_networks=5):
        assert nr_networks > 3

        self.school = ou_name

        self.networks = [
            Network(self.school, prefixlen=random.randint(8, 24)) for _i in range(nr_networks)
        ]
        self.networks[1].iprange = None

    def __str__(self):
        lines = [str(network) for network in self.networks]
        return "\n".join(lines)

    def verify(self):
        for network in self.networks:
            network.verify()

    def set_mode_to_router(self):
        for network in self.networks:
            network.set_mode_to_router()

    def modify(self):
        self.networks[0].defaultrouter += 2
        # self.networks[1].defaultrouter = ''
        self.networks[2].nameserver += 3
        self.networks[3].defaultrouter += 3
        self.networks[3].netbiosserver += 3


def create_and_verify_networks(use_cli_api=True, use_python_api=False, nr_networks=5):
    assert use_cli_api != use_python_api

    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))

        print("********** Generate school data")
        network_import = NetworkImport(ou_name, nr_networks=nr_networks)
        print(network_import)
        import_file = ImportFile(use_cli_api, use_python_api)

        print("********** Create networks")
        import_file.run_import(str(network_import))
        network_import.verify()

        print("********** Create routers")
        network_import.set_mode_to_router()
        import_file.set_mode_to_router()
        network_import.modify()
        import_file.run_import(str(network_import))
        network_import.verify()


def import_networks_basics(use_cli_api=True, use_python_api=False):
    create_and_verify_networks(use_cli_api, use_python_api, 10)
