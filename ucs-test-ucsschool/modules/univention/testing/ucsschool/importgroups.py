# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import subprocess
import tempfile

import ucsschool.lib.models.utils
import univention.config_registry
import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.group import SchoolClass as GroupLib
from ucsschool.lib.models.school import School as SchoolLib
from ucsschool.lib.roles import create_ucsschool_role_string, role_school_class, role_school_class_share
from univention.testing import utils
from univention.testing.ucsschool.importou import get_school_base

configRegistry = univention.config_registry.ConfigRegistry()
configRegistry.load()

cn_pupils = configRegistry.get("ucsschool/ldap/default/container/pupils", "schueler")


class Group:
    def __init__(self, school):
        self.name = "{}-{}".format(school, uts.random_name())
        self.description = uts.random_name()
        self.school = school
        self.mode = "A"

        self.school_base = get_school_base(self.school)

        self.dn = "cn=%s,cn=klassen,cn=%s,cn=groups,%s" % (self.name, cn_pupils, self.school_base)
        self.share_dn = "cn=%s,cn=klassen,cn=shares,%s" % (self.name, self.school_base)

    def set_mode_to_modify(self):
        self.mode = "M"

    def set_mode_to_delete(self):
        self.mode = "D"

    def __str__(self):
        delimiter = "\t"
        line = self.mode
        line += delimiter
        line += self.school
        line += delimiter
        line += self.name
        line += delimiter
        line += self.description
        return line

    def expected_attributes(self):
        attr = {}
        attr["cn"] = [self.name]
        attr["description"] = [self.description]
        attr["ucsschoolRole"] = [create_ucsschool_role_string(role_school_class, self.school)]
        return attr

    def verify(self):
        print("verify group: %s" % self.name)

        if self.mode == "D":
            utils.verify_ldap_object(self.dn, should_exist=False)
            utils.verify_ldap_object(self.share_dn, should_exist=False)
            return

        utils.verify_ldap_object(self.dn, expected_attr=self.expected_attributes(), should_exist=True)
        utils.verify_ldap_object(
            self.share_dn,
            expected_attr={
                "ucsschoolRole": [create_ucsschool_role_string(role_school_class_share, self.school)]
            },
            should_exist=True,
        )


class ImportFile:
    def __init__(self, use_cli_api, use_python_api):
        self.use_cli_api = use_cli_api
        self.use_python_api = use_python_api
        self.import_fd, self.import_file = tempfile.mkstemp()
        os.close(self.import_fd)
        self.group_import = None

    def write_import(self):
        self.import_fd = os.open(self.import_file, os.O_RDWR | os.O_CREAT)
        os.write(self.import_fd, str(self.group_import).encode("UTF-8"))
        os.close(self.import_fd)

    def run_import(self, group_import):
        self.group_import = group_import
        try:
            if self.use_cli_api:
                self.write_import()
                self._run_import_via_cli()
            elif self.use_python_api:
                self._run_import_via_python_api()
            print("SCHOOL DATA     :\n%s" % str(self.group_import))
        finally:
            try:
                os.remove(self.import_file)
            except OSError as e:
                print("WARNING: %s not removed. %s" % (self.import_file, e))

    def _run_import_via_cli(self):
        cmd_block = ["/usr/share/ucs-school-import/scripts/import_group", self.import_file]

        print("cmd_block: %r" % cmd_block)
        subprocess.check_call(cmd_block)

    def _run_import_via_python_api(self):
        # reload UCR
        ucsschool.lib.models.utils.ucr.load()

        lo = univention.admin.uldap.getAdminConnection()[0]

        # get school from first group
        school = self.group_import.groups[0].school

        school_obj = SchoolLib.cache(school, display_name=school)
        if not school_obj.exists(lo):
            school_obj.dc_name = uts.random_name()
            school_obj.create(lo)

        for grp in self.group_import.groups:
            kwargs = {"school": grp.school, "name": grp.name, "description": grp.description}
            if grp.mode == "A":
                GroupLib(**kwargs).create(lo)
            elif grp.mode == "M":
                GroupLib(**kwargs).modify(lo)
            elif grp.mode == "D":
                GroupLib(**kwargs).remove(lo)


class GroupImport:
    def __init__(self, ou_name, nr_groups=20):
        assert nr_groups > 3

        self.school = ou_name

        self.groups = [Group(self.school) for _i in range(nr_groups)]

    def __str__(self):
        lines = [str(group) for group in self.groups]
        return "\n".join(lines)

    def verify(self):
        for group in self.groups:
            group.verify()

    def modify(self):
        for group in self.groups:
            group.set_mode_to_modify()
        self.groups[0].description = uts.random_name()
        self.groups[1].description = uts.random_name()

    def delete(self):
        for group in self.groups:
            group.set_mode_to_delete()


def create_and_verify_groups(use_cli_api=True, use_python_api=False, nr_groups=5):
    assert use_cli_api != use_python_api

    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))

        print("********** Generate school data")
        group_import = GroupImport(ou_name, nr_groups=nr_groups)
        print(group_import)
        import_file = ImportFile(use_cli_api, use_python_api)

        print("********** Create groups")
        import_file.run_import(group_import)
        group_import.verify()

        print("********** Modify groups")
        group_import.modify()
        import_file.run_import(group_import)
        group_import.verify()

        print("********** Delete groups")
        group_import.delete()
        import_file.run_import(group_import)
        group_import.verify()


def import_groups_basics(use_cli_api=True, use_python_api=False):
    create_and_verify_groups(use_cli_api, use_python_api, 10)
