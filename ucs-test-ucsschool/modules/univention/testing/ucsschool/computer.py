import random
from enum import Enum
from ipaddress import IPv4Interface, IPv4Network
from typing import TYPE_CHECKING, Optional

import univention.testing.strings as uts
import univention.testing.utils as utils
from ucsschool.importer.utils.constants import get_sep_char
from ucsschool.lib.models.computer import (
    IPComputer as IPComputerLib,
    LinuxComputer as LinuxComputerLib,
    MacComputer as MacComputerLib,
    UbuntuComputer as UbuntuComputerLib,
    WindowsComputer as WindowsComputerLib,
)
from univention.testing.ucsschool.importou import get_school_base

if TYPE_CHECKING:
    from univention.admin.uldap import access as LoType


class SupportedComputer(Enum):
    windows = 1
    macos = 2
    ipmanagedclient = 3
    linux = 4
    ubuntu = 5


class IpIter(object):
    # Hot fix for bug #38191
    # Generate 110 different ip addresses in the range 11.x.x.x-120.x.x.x
    # so each lie in a different network prefix >= 8
    netmasks = ["/255.255.255.0", "/255.255.248.0", "/255.255.0.0"]

    def __init__(self):
        self.max_range = 120
        self.index = 11
        self.network_index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < self.max_range:
            ip_list = [
                self.index,
                random.randint(1, 254),
                random.randint(1, 254),
                random.randint(1, 254),
            ]
            ip = ".".join(map(str, ip_list))
            self.index += 1
            return ip
        raise StopIteration()

    def next_network(self):  # type: () -> str
        # get network address from random IP address and next netmask
        temp_address = self.next()
        netmask = self.netmasks[self.network_index % len(self.netmasks)]
        self.network_index += 1
        address = IPv4Interface("{}{}".format(temp_address, netmask))
        return "{}/{}".format(address.network.network_address, address.netmask)

    next = __next__


def random_ip(ip_iter=IpIter()):  # type: (IpIter) -> str
    return next(ip_iter)


def random_network(ip_iter=IpIter()):  # type: (IpIter) -> str
    return ip_iter.next_network()


def random_mac():  # type: () -> str
    mac = [
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
    ]
    return ":".join("%02x" % x for x in mac)


class Computer(object):
    def __init__(self, school, ctype):  # type: (str, str) -> None
        self.name = uts.random_name()
        self.mac = [random_mac()]
        self.ip = [random_ip()]
        self.network = None
        self.school = school
        self.ctype = ctype
        self.inventory_numbers = []
        self.custom_secondary_mac_address = random_mac()
        self.school_base = get_school_base(self.school)
        self.dn = "cn=%s,cn=computers,%s" % (self.name, self.school_base)

    def get_args(self):
        return {
            "school": self.school,
            "name": self.name,
            "ip_address": self.ip,
            "mac_address": self.mac,
            "type_name": self.ctype,
            "inventory_number": self.inventory_numbers,
        }

    def set_network_address(self):
        self.ip = []
        self.network = [random_network()]

    def set_inventory_numbers(self):
        self.inventory_numbers.append(uts.random_name())
        self.inventory_numbers.append(uts.random_name())

    def __str__(self):
        _ip = self.ip[0] if self.ip else self.network[0]
        _inventory_numbers = ",".join(self.inventory_numbers)
        return get_sep_char().join(
            el
            for el in (
                self.ctype,
                self.name,
                self.mac[0],
                self.school,
                _ip,
                _inventory_numbers,
                self.custom_secondary_mac_address,
            )
        )

    def expected_attributes(self):
        attr = {
            "cn": [self.name],
            "macAddress": self.mac,
            "univentionObjectType": ["computers/%s" % self.ctype],
        }
        if self.ip:
            attr["aRecord"] = self.ip
        if self.inventory_numbers:
            attr["univentionInventoryNumber"] = self.inventory_numbers
        if self.custom_secondary_mac_address:
            attr["macAddress"].append(self.custom_secondary_mac_address)
        return attr

    def verify(self):
        print("verify computer: %s" % self.name)
        utils.verify_ldap_object(self.dn, expected_attr=self.expected_attributes(), should_exist=True)
        if self.network:
            lo = utils.get_ldap_connection()
            values = lo.get(self.dn, attr=["aRecord"])
            network = IPv4Network(self.network[0])
            assert "aRecord" in values
            aRecord = IPv4Interface(values["aRecord"][0].decode("utf-8"))
            assert aRecord in network, (self.name, aRecord, network)


def create_test_computers(
    lo,
    school=None,
    nr_windows=1,
    nr_macos=0,
    nr_ip_managed_clients=0,
    nr_linux=0,
    nr_ubuntu=0,
):  # type: (LoType, Optional[str], int, int, int, int, int) -> list[Computer]
    """Utility function to create test computers (~ python import)"""
    created_computers = []
    school = school if school else uts.random_name()
    for i in range(nr_windows):
        computer = Computer(school=school, ctype="windows")
        WindowsComputerLib(**computer.get_args()).create(lo)
        created_computers.append(computer)
    for i in range(nr_macos):
        computer = Computer(school=school, ctype="macos")
        MacComputerLib(**computer.get_args()).create(lo)
        created_computers.append(computer)
    for i in range(nr_ip_managed_clients):
        computer = Computer(school=school, ctype="ipmanagedclient")
        IPComputerLib(**computer.get_args()).create(lo)
        created_computers.append(computer)
    for i in range(nr_linux):
        computer = Computer(school=school, ctype="linux")
        LinuxComputerLib(**computer.get_args()).create(lo)
        created_computers.append(computer)
    for i in range(nr_ubuntu):
        computer = Computer(school=school, ctype="ubuntu")
        UbuntuComputerLib(**computer.get_args()).create(lo)
        created_computers.append(computer)

    return sorted(created_computers, key=lambda x: x.name)


class Computers(object):
    # Utility class to create test computers (~ python import)
    def __init__(
        self,
        lo,
        school,
        nr_windows=1,
        nr_macos=0,
        nr_ipmanagedclient=0,
        nr_linux=0,
        nr_ubuntu=0,
    ):  # type: (LoType, str, int, int, int, int, int) -> None
        self.lo = lo
        self.school = school
        self.nr_windows = nr_windows
        self.nr_macos = nr_macos
        self.nr_ip_managed_clients = nr_ipmanagedclient
        self.nr_linux = nr_linux
        self.nr_ubuntu = nr_ubuntu

    def create(self):  # type: () -> list[Computer]
        print("********** Create computers")
        created_computers = []
        school = self.school if self.school else uts.random_name()
        for i in range(self.nr_windows):
            computer = Computer(school=school, ctype="windows")
            WindowsComputerLib(**computer.get_args()).create(self.lo)
            created_computers.append(computer)
        for i in range(self.nr_macos):
            computer = Computer(school=school, ctype="macos")
            MacComputerLib(**computer.get_args()).create(self.lo)
            created_computers.append(computer)
        for i in range(self.nr_ip_managed_clients):
            computer = Computer(school=school, ctype="ipmanagedclient")
            IPComputerLib(**computer.get_args()).create(self.lo)
            created_computers.append(computer)
        for i in range(self.nr_linux):
            computer = Computer(school=school, ctype="linux")
            LinuxComputerLib(**computer.get_args()).create(self.lo)
            created_computers.append(computer)
        for i in range(self.nr_ubuntu):
            computer = Computer(school=school, ctype="ubuntu")
            UbuntuComputerLib(**computer.get_args()).create(self.lo)
            created_computers.append(computer)

        return sorted(created_computers, key=lambda x: x.name)

    @staticmethod
    def get_dns(computers):  # type: (list[Computer]) -> list[str]
        return [x.dn for x in computers]

    @staticmethod
    def get_hostnames(computers):  # type: (list[Computer]) -> list[str]
        return ["%s$" % x.name for x in computers]
