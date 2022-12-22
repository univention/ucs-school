#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Import computers via CLI
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import

from __future__ import print_function

import os
import random
import re
import subprocess
import tempfile
from ipaddress import IPv4Interface, IPv4Network

import univention.config_registry
import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from univention.testing.ucsschool.importou import get_school_base

HOOK_BASEDIR = "/usr/share/ucs-school-import/pyhooks"


configRegistry = univention.config_registry.ConfigRegistry()
configRegistry.load()


def random_mac():
    mac = [
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0x7F),
        random.randint(0x00, 0xFF),
        random.randint(0x00, 0xFF),
    ]

    return ":".join("%02x" % x for x in mac)


# Hot fix for bug #38191
# Generate 110 different ip addresses in the range 11.x.x.x-120.x.x.x
# so each lie in a different network prefix >= 8


class IpIter(object):
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


class Computer(object):
    def __init__(self, school, ctype, extra_attribute):  # type: (str, str, str) -> None
        self.name = uts.random_name()
        self.mac = [random_mac()]
        self.ip = [random_ip()]
        self.network = None
        self.school = school
        self.ctype = ctype
        self.inventorynumbers = []
        self.extra_attribute = extra_attribute
        self.school_base = get_school_base(self.school)
        self.dn = "cn=%s,cn=computers,%s" % (self.name, self.school_base)

    def set_network_address(self):
        self.ip = []
        self.network = [random_network()]

    def set_inventorynumbers(self):
        self.inventorynumbers.append(uts.random_name())
        self.inventorynumbers.append(uts.random_name())

    def __str__(self):
        delimiter = "\t"
        line = self.ctype
        line += delimiter
        line += self.name
        line += delimiter
        line += self.mac[0]
        line += delimiter
        line += self.school
        line += delimiter
        line += self.ip[0] if self.ip else self.network[0]
        line += delimiter
        if self.inventorynumbers:
            line += ",".join(self.inventorynumbers)
        line += delimiter
        line += self.extra_attribute
        return line

    def expected_attributes(self):
        attr = {
            "cn": [self.name],
            "macAddress": self.mac,
            "univentionObjectType": ["computers/%s" % self.ctype],
        }
        if self.ip:
            attr["aRecord"] = self.ip
        if self.inventorynumbers:
            attr["univentionInventoryNumber"] = self.inventorynumbers
        if self.extra_attribute:
            attr["macAddress"].append(self.extra_attribute)
        return attr

    def verify(self):
        print("verify computer: %s" % self.name)

        utils.verify_ldap_object(
            self.dn, expected_attr=self.expected_attributes(), should_exist=True
        )

        if self.network:
            lo = utils.get_ldap_connection()
            values = lo.get(self.dn, attr=["aRecord"])
            network = IPv4Network(self.network[0])
            assert "aRecord" in values
            aRecord = IPv4Interface(values["aRecord"][0].decode("utf-8"))
            assert aRecord in network, (self.name, aRecord, network)


class Windows(Computer):
    def __init__(self, school, extra_attribute):
        super(Windows, self).__init__(school, "windows", extra_attribute)


class MacOS(Computer):
    def __init__(self, school, extra_attribute):
        super(MacOS, self).__init__(school, "macos", extra_attribute)


class IPManagedClient(Computer):
    def __init__(self, school, extra_attribute):
        super(IPManagedClient, self).__init__(
            school, "ipmanagedclient", extra_attribute
        )


class Ubuntu(Computer):
    def __init__(self, school, extra_attribute):
        super(Ubuntu, self).__init__(school, "ubuntu", extra_attribute)


class Linux(Computer):
    def __init__(self, school, extra_attribute):
        super(Linux, self).__init__(school, "linux", extra_attribute)


class ImportFile:
    def __init__(self):
        self.import_fd, self.import_file = tempfile.mkstemp()
        os.close(self.import_fd)
        self.computer_import = None

    def write_import(self):
        self.import_fd = os.open(self.import_file, os.O_RDWR | os.O_CREAT)
        os.write(self.import_fd, str(self.computer_import).encode("utf-8"))
        os.close(self.import_fd)

    def _run_import_via_cli(self):
        cmd_block = [
            "/usr/share/ucs-school-import/scripts/import_computer",
            self.import_file,
        ]
        print("cmd_block: %r" % cmd_block)
        subprocess.check_call(cmd_block)

    def run_import(self, computer_import):  # type: (ComputerImport) -> None
        hooks = ComputerHooks()
        self.computer_import = computer_import
        try:
            self.write_import()
            self._run_import_via_cli()
            pre_result = hooks.get_pre_result()
            post_result = hooks.get_post_result()
            print("PRE  HOOK result:\n%s" % pre_result)
            print("POST HOOK result:\n%s" % post_result)
            print("SCHOOL DATA     :\n%s" % str(self.computer_import))
            assert pre_result == post_result
            for expected, pre, post in zip(
                str(self.computer_import).split("\n"),
                pre_result.split("\n"),
                post_result.split("\n"),
            ):

                expected = expected.strip()
                # remove possible subnet from ip address field
                expected = re.sub(r"\t([\d,\.]+)\/[\d,\.]+\t", r"\t\1\t", expected)
                pre, post = pre.strip(), post.strip()
                assert expected == pre, (expected, pre)
                assert expected == post, (expected, post)

        finally:
            hooks.cleanup()
            try:
                os.remove(self.import_file)
            except OSError as e:
                print("WARNING: %s not removed. %s" % (self.import_file, e))


class ComputerHooks:
    """
    Creates a simple pre + post hook, which writes the
    computer object in a result file.
    This is asserts that migrated shell hooks are still working.
    """

    def __init__(self):
        fd, self.pre_hook_result = tempfile.mkstemp()
        os.close(fd)

        fd, self.post_hook_result = tempfile.mkstemp()
        os.close(fd)

        self.pre_hook = None
        self.post_hook = None

        self.create_hooks()

    def get_pre_result(self):  # type: () -> str
        return open(self.pre_hook_result, "r").read().rstrip()

    def get_post_result(self):  # type: () -> str
        return open(self.post_hook_result, "r").read().rstrip()

    def create_hooks(self):
        self.pre_hook = os.path.join(HOOK_BASEDIR, "{}.py".format(uts.random_name()))
        self.post_hook = os.path.join(HOOK_BASEDIR, "{}.py".format(uts.random_name()))

        with open(self.pre_hook, "w") as fd:
            hook_content = """
from ucsschool.lib.models.computer import SchoolComputer
from ucsschool.lib.models.hook import Hook
from ucsschool.importer.utils.computer_pyhook import ComputerPyHook

class TestPreSchoolComputer(ComputerPyHook):
    model = SchoolComputer
    priority = {
        "pre_create": 10,
    }
""" + """
    def pre_create(self, obj, line):
        with open("{}", "a") as fout:
            assert isinstance(line, list)
            module_part = obj._meta.udm_module.split("/")[1]
            _line = "\\t".join([module_part, obj.name, obj.mac_address[0],
            obj.school, obj.ip_address[0] if obj.ip_address else "None",
            ",".join(obj.get_inventory_numbers()), line[-1]])
            _line += "\\n"
            fout.write(_line)
            obj.mac_address.append(line[-1])
""".format(
                self.pre_hook_result
            )
            print("Writing pre hook to file {}".format(self.pre_hook))
            print(hook_content)
            fd.write(hook_content)

        with open(self.post_hook, "w") as fd:
            hook_content = """
from ucsschool.lib.models.computer import SchoolComputer
from ucsschool.importer.utils.computer_pyhook import ComputerPyHook

class TestPostSchoolComputer(ComputerPyHook):
    model = SchoolComputer
    priority = {
        "post_create": 10,
    }
""" + """
    def post_create(self, obj, line):
        with open("{}", "a") as fout:
            assert isinstance(line, list)
            module_part = obj._meta.udm_module.split("/")[1]
            _line = "\t".join([module_part, obj.name, obj.mac_address[0],
            obj.school, obj.ip_address[0] if obj.ip_address else "None",
            ",".join(obj.get_inventory_numbers()), line[-1]])
            _line += "\\n"
            fout.write(_line)
        """.format(
                self.post_hook_result
            )
            print("Writing post hook to file {}".format(self.post_hook))
            print(hook_content)
            fd.write(hook_content)

    def cleanup(self):
        os.remove(self.pre_hook)
        os.remove(self.post_hook)
        os.remove(self.pre_hook_result)
        os.remove(self.post_hook_result)


class ComputerImport:
    def __init__(self, ou_name):
        nr_windows = 5
        nr_macos = 4
        nr_ip_managed_clients = 4
        nr_ubuntu = 5
        nr_linux = 5
        self.school = ou_name

        self.windows = []

        for i in range(0, nr_windows):
            self.windows.append(Windows(self.school, extra_attribute=random_mac()))
        self.windows[1].set_inventorynumbers()
        self.windows[2].set_network_address()

        self.macos = []
        for i in range(0, nr_macos):
            self.macos.append(MacOS(self.school, extra_attribute=random_mac()))
        self.macos[0].set_inventorynumbers()
        self.macos[1].set_network_address()

        self.ip_managed_clients = []
        for i in range(0, nr_ip_managed_clients):
            self.ip_managed_clients.append(
                IPManagedClient(self.school, extra_attribute=random_mac())
            )
        self.ip_managed_clients[0].set_inventorynumbers()
        self.ip_managed_clients[1].set_network_address()

        self.linux_computer = []
        for i in range(0, nr_linux):
            self.linux_computer.append(Linux(self.school, extra_attribute=random_mac()))
        self.linux_computer[0].set_inventorynumbers()
        self.linux_computer[1].set_network_address()

        self.ubuntu_computers = []
        for i in range(0, nr_ubuntu):
            self.ubuntu_computers.append(
                Ubuntu(self.school, extra_attribute=random_mac())
            )
        self.ubuntu_computers[0].set_inventorynumbers()
        self.ubuntu_computers[1].set_network_address()

    def _computers(self):
        return (
            self.windows
            + self.macos
            + self.ip_managed_clients
            + self.linux_computer
            + self.ubuntu_computers
        )

    def __str__(self):
        return "\n".join([str(computer) for computer in self._computers()])

    def verify(self):
        for computer in self._computers():
            computer.verify()


def test_create_and_verify_computers():
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
        print("********** Generate school data")
        computer_import = ComputerImport(
            ou_name,
        )
        print(computer_import)
        import_file = ImportFile()
        import_file.run_import(computer_import)
        computer_import.verify()
