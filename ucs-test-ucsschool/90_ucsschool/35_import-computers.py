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
from collections import defaultdict
from typing import List

import pytest

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.importer.exceptions import ComputerImportError
from ucsschool.importer.utils.computer_import import get_ip_iface, mac_address_is_used
from ucsschool.lib.models.computer import WindowsComputer
from univention.testing.ucsschool.computer import Computer, SupportedComputer, random_ip, random_mac

HOOK_BASEDIR = "/usr/share/ucs-school-import/pyhooks"


class ComputerImport:
    def __init__(self, ou_name):  # type: (str) -> None
        self._school = ou_name
        self._test_computers = defaultdict(list)  # type: dict[str, List[Computer]]
        for ctype in SupportedComputer:
            self._create_computer(ctype=ctype.name)

    def _create_computer(self, ctype):  # type: (str) -> None
        amount = 5
        for i in range(amount):
            self._test_computers[ctype].append(Computer(school=self._school, ctype=ctype))
        i, j = random.sample(range(amount), 2)
        self._test_computers[ctype][i].set_inventory_numbers()
        self._test_computers[ctype][j].set_network_address()

    def _computers(self):  # type: () -> List[Computer]
        return sum(self._test_computers.values(), [])

    def verify(self):
        for computer in self._computers():
            computer.verify()

    def __str__(self):
        return "\n".join([str(computer) for computer in self._computers()])


class ImportComputerHooks:
    """
    Creates a simple pre + post hook, which writes the
    computer object in a result file.
    This is asserts that the computer import hooks are working.
    """

    def __init__(self):
        fd, self.pre_hook_result = tempfile.mkstemp()
        os.close(fd)
        fd, self.post_hook_result = tempfile.mkstemp()
        os.close(fd)
        self.pre_hook = os.path.join(HOOK_BASEDIR, "{}.py".format(uts.random_name()))
        self.post_hook = os.path.join(HOOK_BASEDIR, "{}.py".format(uts.random_name()))
        self.create_hooks()

    def get_pre_result(self):  # type: () -> str
        return open(self.pre_hook_result, "r").read().rstrip()

    def get_post_result(self):  # type: () -> str
        return open(self.post_hook_result, "r").read().rstrip()

    def create_hooks(self):
        with open(self.pre_hook, "w") as fd:
            hook_content = (
                """
from ucsschool.lib.models.computer import SchoolComputer
from ucsschool.lib.models.hook import Hook
from ucsschool.importer.utils.computer_pyhook import ComputerPyHook

class TestPreSchoolComputer(ComputerPyHook):
    model = SchoolComputer
    priority = {
        "pre_create": 10,
    }
    def pre_create(self, obj, line):
        with open("%s", "a") as fout:
            assert isinstance(line, list)
            module_part = obj._meta.udm_module.split("/")[1]
            _line = "\\t".join([module_part, obj.name, obj.mac_address[0],
            obj.school, obj.ip_address[0] if obj.ip_address else "None",
            ",".join(obj.get_inventory_numbers()), line[-1]])
            _line += "\\n"
            fout.write(_line)
            obj.mac_address.append(line[-1])
"""
                % self.pre_hook_result
            )
            print("Writing pre hook to file {}".format(self.pre_hook))
            print(hook_content)
            fd.write(hook_content)

        with open(self.post_hook, "w") as fd:
            hook_content = (
                """
from ucsschool.lib.models.computer import SchoolComputer
from ucsschool.importer.utils.computer_pyhook import ComputerPyHook

class TestPostSchoolComputer(ComputerPyHook):
    model = SchoolComputer
    priority = {
        "post_create": 10,
    }
    def post_create(self, obj, line):
        with open("%s", "a") as fout:
            assert isinstance(line, list)
            module_part = obj._meta.udm_module.split("/")[1]
            _line = "\t".join([module_part, obj.name, obj.mac_address[0],
            obj.school, obj.ip_address[0] if obj.ip_address else "None",
            ",".join(obj.get_inventory_numbers()), line[-1]])
            _line += "\\n"
            fout.write(_line)
"""
                % self.post_hook_result
            )
            print("Writing post hook to file {}".format(self.post_hook))
            print(hook_content)
            fd.write(hook_content)

    def cleanup(self):
        for file in (
            self.pre_hook,
            self.post_hook,
            self.pre_hook_result,
            self.post_hook_result,
        ):
            os.remove(file)


class ImportFile:
    def __init__(self):
        self.import_fd, self.import_file = tempfile.mkstemp()
        os.close(self.import_fd)
        self.computer_import = None

    def write_import(self):
        self.import_fd = os.open(self.import_file, os.O_RDWR | os.O_CREAT)
        os.write(self.import_fd, str(self.computer_import).encode("utf-8"))
        os.close(self.import_fd)

    def run_import(self, computer_import):  # type: (ComputerImport) -> None
        hooks = ImportComputerHooks()
        self.computer_import = computer_import
        try:
            self.write_import()
            cmd_block = [
                "/usr/share/ucs-school-import/scripts/import_computer",
                self.import_file,
            ]
            print("cmd_block: %r" % cmd_block)
            subprocess.check_call(cmd_block)
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


def test_import_computer():
    with utu.UCSTestSchool() as schoolenv:
        ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
        print("********** Generate school data")
        computer_import = ComputerImport(
            ou_name,
        )
        print(computer_import)
        import_file = ImportFile()
        import_file.run_import(computer_import)
        computer_import.verify()


@pytest.mark.parametrize(
    "ip_address,message",
    [
        ("10.200.0", r"'10.200.0' is not a valid ip address"),
        ("10.200.47.11/99", "'99' is not a valid netmask"),
        ("10.200.47.11", ""),
        ("10.200.47.11/255.255.255.0", ""),
    ],
)
def test_get_ip_iface(ip_address, message):
    if message:
        with pytest.raises(ComputerImportError, match=message):
            get_ip_iface(ip_address)
    else:
        get_ip_iface(ip_address)


def test_mac_address_is_used():
    with utu.UCSTestSchool() as schoolenv:
        ou_name, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
        mac = random_mac().lower()
        assert mac_address_is_used(lo=schoolenv.lo, mac_address=mac) is False
        assert mac_address_is_used(lo=schoolenv.lo, mac_address=mac.upper()) is False
        computer = WindowsComputer(
            school=ou_name,
            name=uts.random_name(),
            ip_address=[random_ip()],
            mac_address=[mac],
        )
        computer.create(schoolenv.lo)
        assert mac_address_is_used(lo=schoolenv.lo, mac_address=mac) is True
        assert mac_address_is_used(lo=schoolenv.lo, mac_address=mac.upper()) is True
