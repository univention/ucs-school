# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import random
import subprocess
import tempfile

import ucsschool.lib.models.utils
import univention.config_registry
import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models.computer import (
    IPComputer as IPComputerLib,
    MacComputer as MacComputerLib,
    WindowsComputer as WindowsComputerLib,
)
from ucsschool.lib.models.school import School as SchoolLib
from univention.testing.ucsschool.importou import get_school_base

HOOK_BASEDIR = "/var/lib/ucs-school-lib/hooks"


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


class IP_Iter(object):
    def __init__(self):
        self.max_range = 120
        self.index = 11

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
        else:
            raise StopIteration()

    next = __next__


def random_ip(ip_iter=IP_Iter()):
    return next(ip_iter)


class Computer(object):
    def __init__(self, school, ctype):
        self.name = uts.random_name()
        self.mac = [random_mac()]
        self.ip = [random_ip()]
        self.school = school
        self.ctype = ctype

        self.inventorynumbers = []
        self.zone = None

        self.school_base = get_school_base(self.school)

        self.dn = "cn=%s,cn=computers,%s" % (self.name, self.school_base)

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
        line += self.ip[0]
        line += delimiter
        if self.inventorynumbers:
            line += ",".join(self.inventorynumbers)
        if self.zone:
            line += delimiter
            line += self.zone

        return line

    def expected_attributes(self):
        attr = {
            "cn": [self.name],
            "macAddress": self.mac,
            "aRecord": self.ip,
            "univentionObjectType": ["computers/%s" % self.ctype],
        }
        if self.inventorynumbers:
            attr["univentionInventoryNumber"] = self.inventorynumbers
        return attr

    def verify(self):
        print("verify computer: %s" % self.name)

        utils.verify_ldap_object(self.dn, expected_attr=self.expected_attributes(), should_exist=True)


class Windows(Computer):
    def __init__(self, school):
        super(Windows, self).__init__(school, "windows")


class MacOS(Computer):
    def __init__(self, school):
        super(MacOS, self).__init__(school, "macos")


class IPManagedClient(Computer):
    def __init__(self, school):
        super(IPManagedClient, self).__init__(school, "ipmanagedclient")


class ImportFile:
    def __init__(self, use_cli_api, use_python_api):
        self.use_cli_api = use_cli_api
        self.use_python_api = use_python_api
        self.import_fd, self.import_file = tempfile.mkstemp()
        os.close(self.import_fd)
        self.computer_import = None

    def write_import(self):
        self.import_fd = os.open(self.import_file, os.O_RDWR | os.O_CREAT)
        os.write(self.import_fd, str(self.computer_import).encode("utf-8"))
        os.close(self.import_fd)

    def run_import(self, computer_import):
        hooks = ComputerHooks()
        self.computer_import = computer_import
        try:
            if self.use_cli_api:
                self.write_import()
                self._run_import_via_cli()
            elif self.use_python_api:
                self._run_import_via_python_api()
            pre_result = hooks.get_pre_result()
            post_result = hooks.get_post_result()
            print("PRE  HOOK result:\n%s" % pre_result)
            print("POST HOOK result:\n%s" % post_result)
            print("SCHOOL DATA     :\n%s" % str(self.computer_import))
            assert pre_result == post_result
            for expected, pre, post in zip(
                str(self.computer_import).split("\n"), pre_result.split("\n"), post_result.split("\n")
            ):
                expected = expected.strip()
                pre, post = pre.strip(), post.strip()
                assert expected == pre, (expected, pre)
                assert expected == post, (expected, post)

        finally:
            hooks.cleanup()
            try:
                os.remove(self.import_file)
            except OSError as e:
                print("WARNING: %s not removed. %s" % (self.import_file, e))

    def _run_import_via_cli(self):
        cmd_block = ["/usr/share/ucs-school-import/scripts/import_computer", self.import_file]

        print("cmd_block: %r" % cmd_block)
        subprocess.check_call(cmd_block)

    def _run_import_via_python_api(self):
        # reload UCR
        ucsschool.lib.models.utils.ucr.load()

        lo = univention.admin.uldap.getAdminConnection()[0]

        # get school from first computer
        school = self.computer_import.windows[0].school

        school_obj = SchoolLib.cache(school, display_name=school)
        if not school_obj.exists(lo):
            school_obj.dc_name = uts.random_name()
            school_obj.create(lo)

        def _set_kwargs(computer):
            kwargs = {
                "school": computer.school,
                "name": computer.name,
                "ip_address": computer.ip,
                "mac_address": computer.mac,
                "type_name": computer.ctype,
                "inventory_number": computer.inventorynumbers,
                "zone": computer.zone,
            }
            return kwargs

        for computer in self.computer_import.windows:
            kwargs = _set_kwargs(computer)
            WindowsComputerLib(**kwargs).create(lo)
        for computer in self.computer_import.macos:
            kwargs = _set_kwargs(computer)
            MacComputerLib(**kwargs).create(lo)
        for computer in self.computer_import.ip_managed_clients:
            kwargs = _set_kwargs(computer)
            IPComputerLib(**kwargs).create(lo)


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

    def get_pre_result(self):
        return open(self.pre_hook_result, "r").read().rstrip()

    def get_post_result(self):
        return open(self.post_hook_result, "r").read().rstrip()

    def create_hooks(self):
        self.pre_hook = os.path.join(HOOK_BASEDIR, "{}.py".format(uts.random_name()))
        self.post_hook = os.path.join(HOOK_BASEDIR, "{}.py".format(uts.random_name()))

        with open(self.pre_hook, "w") as fd:
            hook_content = """
from ucsschool.lib.models.computer import SchoolComputer
from ucsschool.lib.models.hook import Hook

class TestPreSchoolComputer(Hook):
    model = SchoolComputer
    priority = {
        "pre_create": 10,
    }
""" + """
    def pre_create(self, obj):
        with open("{}", "a") as fout:
            module_part = obj._meta.udm_module.split("/")[1]
            line = "\\t".join([module_part, obj.name, obj.mac_address[0],
            obj.school, obj.ip_address[0], ",".join(obj.get_inventory_numbers())])
            if obj.zone:
                line += "\\tobj.zone"
            line += "\\n"
            fout.write(line)
""".format(
                self.pre_hook_result
            )
            print("Writing pre hook to file {}".format(self.pre_hook))
            print(hook_content)
            fd.write(hook_content)

        with open(self.post_hook, "w") as fd:
            hook_content = """
from ucsschool.lib.models.computer import SchoolComputer
from ucsschool.lib.models.hook import Hook

class TestPostSchoolComputer(Hook):
    model = SchoolComputer
    priority = {
        "post_create": 10,
    }
""" + """
    def post_create(self, obj):
        with open("{}", "a") as fout:
            module_part = obj._meta.udm_module.split("/")[1]
            line = "\t".join([module_part, obj.name, obj.mac_address[0],
            obj.school, obj.ip_address[0], ",".join(obj.get_inventory_numbers())])
            if obj.zone:
                line += "\\tobj.zone"
            line += "\\n"
            fout.write(line)
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
    def __init__(self, ou_name, nr_windows=20, nr_macos=5, nr_ipmanagedclient=3):
        assert nr_windows > 2
        assert nr_macos > 2
        assert nr_ipmanagedclient > 2

        self.school = ou_name

        self.windows = []
        for i in range(0, nr_windows):
            self.windows.append(Windows(self.school))
        self.windows[1].set_inventorynumbers()

        self.macos = []
        for i in range(0, nr_macos):
            self.macos.append(MacOS(self.school))
        self.macos[0].set_inventorynumbers()

        self.ip_managed_clients = []
        for i in range(0, nr_ipmanagedclient):
            self.ip_managed_clients.append(IPManagedClient(self.school))
        self.ip_managed_clients[0].set_inventorynumbers()

    def __str__(self):
        lines = []

        for windows in self.windows:
            lines.append(str(windows))

        for macos in self.macos:
            lines.append(str(macos))

        for ipmanagedclient in self.ip_managed_clients:
            lines.append(str(ipmanagedclient))

        return "\n".join(lines)

    def verify(self):
        for windows in self.windows:
            windows.verify()

        for macos in self.macos:
            macos.verify()

        for ipmanagedclient in self.ip_managed_clients:
            ipmanagedclient.verify()


def create_and_verify_computers(
    use_cli_api=True,
    use_python_api=False,
    nr_windows=20,
    nr_macos=5,
    nr_ipmanagedclient=3,
):
    assert use_cli_api != use_python_api

    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))

        print("********** Generate school data")
        computer_import = ComputerImport(
            ou_name,
            nr_windows=nr_windows,
            nr_macos=nr_macos,
            nr_ipmanagedclient=nr_ipmanagedclient,
        )
        print(computer_import)
        import_file = ImportFile(use_cli_api, use_python_api)

        print("********** Create computers")
        import_file.run_import(computer_import)
        computer_import.verify()


def import_computers_basics(use_cli_api=True, use_python_api=False):
    create_and_verify_computers(use_cli_api, use_python_api, 5, 3, 3)
