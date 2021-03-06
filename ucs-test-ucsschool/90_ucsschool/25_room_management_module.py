#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Schoolrooms management module
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-rooms]

from unittest import TestCase, main

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from univention.testing.ucsschool.computerroom import Computers
from univention.testing.ucsschool.schoolroom import ComputerRoom, ComputerRoomSaml


class TestRoomManagementModule(TestCase):
    def __test_room_management_module(self, ComputerRoom=ComputerRoom):
        with utu.UCSTestSchool() as schoolenv:
            with ucr_test.UCSTestConfigRegistry() as ucr:
                school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
                open_ldap_co = schoolenv.open_ldap_connection()

                # importing 2 random computers
                computers = Computers(open_ldap_co, school, 3, 0, 0)
                created_computers = computers.create()
                computers_dns = computers.get_dns(created_computers)

                room = ComputerRoom(
                    school,
                    host_members=[computers_dns[0], computers_dns[1]],
                    teacher_computers=[computers_dns[1]],
                )
                room.add()
                room.verify_ldap(must_exist=True)
                # TODO: move this test to ComputerRoom.verify_ldap() and remove here
                umc_room = room.get()
                if (
                    len(umc_room["teacher_computers"]) != 1
                    and computers_dns[1] not in umc_room["teacher_computers"]
                ):
                    utils.fail(
                        "Exactly {} should be in {}".format(
                            computers_dns[1], umc_room["teacher_computers"]
                        )
                    )

                room.check_query([room.name])

                new_attrs = {
                    "name": "new_name",
                    "description": "new_description",
                    "computers": [computers_dns[1]],
                    "teacher_computers": [computers_dns[1]],
                }
                room.check_put(new_attrs)

                # Test creating new room with the same name
                attrs = room.get()
                room2 = ComputerRoom(
                    school,
                    name=room.name,
                    host_members=[computers_dns[1]],
                    teacher_computers=[computers_dns[1]],
                )
                room2.add(should_pass=False)

                # Check if room attributes have changed after the last test
                room.check_get(attrs)

                room.remove()
                room.verify_ldap(must_exist=False)

    def test_saml_login(self):
        self.__test_room_management_module(ComputerRoom=ComputerRoomSaml)

    def test_classic_login(self):
        self.__test_room_management_module()


if __name__ == "__main__":
    main(verbosity=2)
