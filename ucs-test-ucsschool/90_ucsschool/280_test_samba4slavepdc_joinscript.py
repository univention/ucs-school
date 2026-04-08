#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Testing if joinscript can handle non-default names correctly
## tags: [apptest,ucsschool,ucsschool_import1]
## roles: [domaincontroller_slave]
## exposure: dangerous
## packages:
##   - ucs-school-replica
## bugs: [55911]

import subprocess

import pytest

import univention.admin.modules as udm_modules
from univention.admin.uldap import access, getMachineConnection
from univention.lib.s4 import well_known_domain_rids, well_known_sids
from univention.testing.utils import (
    wait_for_listener_replication_and_postrun,
    wait_for_s4connector_replication,
)

ADMIN_PWD_FILE = "/tmp/adminpw"
ADMIN_RID = "500"

# All RIDs used in the metpackage joinscript
group_rids_to_rename = {
    "556",
    "521",
    "555",
    "562",
    "554",
    "553",
    "519",
    "548",
    "561",
    "516",
    "549",
    "517",
    "558",
    "546",
    "514",
    "574",
    "518",
    "498",
    "552",
    "515",
    "560",
    "557",
    "573",
    "520",
    "559",
    "544",
    "512",
    "571",
    "545",
    "513",
    "551",
    "568",
    "572",
    "569",
}


@pytest.fixture
def write_admin_pwdfile():
    with open(ADMIN_PWD_FILE, "w") as admin_pw_file:
        admin_pw_file.write("univention")
        admin_pw_file.flush()
        yield


@pytest.fixture
def get_administrator_connection(ucr, write_admin_pwdfile):
    """Get an admin connection on the primary"""

    def _get_administrator_connection():
        machine_connection, _ = getMachineConnection()
        admin_dn, _ = machine_connection.search(filter="sambaSID=S-*-%s" % ADMIN_RID)[0]

        ldap_master = ucr.get("ldap/master")
        ldap_master_port = ucr.get("ldap/master/port")
        ldap_base = ucr.get("ldap/base")

        # try to use UDM instead of univention-ldap

        admin_connection = access(
            host=ldap_master,
            port=ldap_master_port,
            base=ldap_base,
            start_tls=2,
            binddn=admin_dn,
            bindpw="univention",
        )
        return admin_connection

    return _get_administrator_connection


@pytest.fixture
def setup_joinscript_test(ucr, get_administrator_connection):
    """
    This fixture expects that the joinscript of the ucs-school-metapackage
    has already run. This means that all relevant well-known objects are already
    created and only have to be modified.
    """
    admin_connection = get_administrator_connection()

    groups_module = udm_modules.get("groups/group")
    settings_module = udm_modules.get("settings/default")

    def set_group_names(name_template):
        defaults_objects = settings_module.lookup(
            None, admin_connection, filter_s="(objectClass=univentionDefault)"
        )
        assert len(defaults_objects) == 1
        default_object = defaults_objects[0]

        for rid in group_rids_to_rename:
            default_name = well_known_domain_rids.get(rid, well_known_sids.get("S-1-5-32-%s" % rid))

            objects = groups_module.lookup(None, admin_connection, filter_s="sambaSID=S-*-%s" % rid)

            assert len(objects) == 1
            well_known_udm_object = objects[0]
            old_dn = well_known_udm_object.dn

            new_name = name_template.format(default_name)
            well_known_udm_object["name"] = new_name

            well_known_udm_object.modify()
            for attr, value in default_object.items():
                if old_dn == value:
                    default_object[attr] = well_known_udm_object.dn

            default_object.modify()

    # set object names to something non-default
    set_group_names("{}-55911")

    wait_for_listener_replication_and_postrun()
    wait_for_s4connector_replication()

    yield

    admin_connection = get_administrator_connection()

    # set object names back to the default
    set_group_names("{}")

    wait_for_listener_replication_and_postrun()
    wait_for_s4connector_replication()


def test_samba4slavepdc_joinscript_with_renamed_objects(setup_joinscript_test):
    """
    Set the name of objects with well known SIDs to something non-default and
    check if the joinscript of the meta package still works
    """
    # A join-script should be re-runnable without failure
    for _ in range(2):
        cmd = [
            "/usr/sbin/univention-run-join-scripts",
            "--run-scripts",
            "96univention-samba4slavepdc",
            "--force",
            "-dcpwd",
            "{}".format(ADMIN_PWD_FILE),
            "-dcaccount",
            "Administrator",
        ]

        joinscript_process = subprocess.run(cmd, check=False)
        assert joinscript_process.returncode == 0, joinscript_process.stderr


def test_samba4slavepdc_joinscript(write_admin_pwdfile):
    """
    Test the joinscript with the default system state

    (no renamed objects like in test_samba4slavepdc_joinscript_with_renamed_objects)
    """
    # A join-script should be re-runnable without failure
    for _ in range(2):
        cmd = [
            "/usr/sbin/univention-run-join-scripts",
            "--run-scripts",
            "96univention-samba4slavepdc",
            "--force",
            "-dcpwd",
            "{}".format(ADMIN_PWD_FILE),
            "-dcaccount",
            "Administrator",
        ]

        joinscript_process = subprocess.run(cmd, check=False)
        assert joinscript_process.returncode == 0, joinscript_process.stderr
