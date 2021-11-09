#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: computerroom module settings checks
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-computerroom]

from ucsschool.lib.models.utils import ucr as lib_ucr
from univention.config_registry import handler_set
from univention.testing import utils
from univention.testing.network import NetworkRedirector
from univention.testing.ucsschool.computerroom import Computers, Room
from univention.testing.umc import Client


def test_computerroom_module_settings(schoolenv, ucr):
    with NetworkRedirector() as nethelper:
        handler_set(["ucsschool/import/generate/share/marktplatz=yes"])
        lib_ucr.load()
        ucr.load()
        school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"), use_cache=False)
        utils.wait_for_replication()
        utils.verify_ldap_object(
            "cn=Marktplatz,cn=shares,%s" % (oudn,),
            strict=True,
            should_exist=True,
        )
        teacher, teacher_dn = schoolenv.create_user(school, is_teacher=True)
        open_ldap_co = schoolenv.open_ldap_connection()

        # importing random 2 computers
        computers = Computers(open_ldap_co, school, 2, 0, 0)
        created_computers = computers.create()

        # setting computer rooms contains the created computers
        room = Room(school, host_members=created_computers[0].dn)
        # Creating the rooms
        schoolenv.create_computerroom(
            school, name=room.name, description=room.description, host_members=room.host_members
        )

        client = Client(None, teacher, "univention", automatic_reauthentication=True)

        # preparing the network loop
        nethelper.add_loop(created_computers[0].ip[0], created_computers[1].ip[0])

        # the actual test
        room.test_settings(school, teacher, teacher_dn, created_computers[1].ip[0], ucr, client)
