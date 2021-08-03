from __future__ import print_function

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.roles import (
    context_type_school,
    create_ucsschool_role_string,
    role_computer_room,
    role_computer_room_backend_veyon,
)
from univention.testing.umc import Client, ClientSaml


class ComputerRoom(object):
    def __init__(
        self,
        school,
        name=None,
        description=None,
        host_members=[],
        teacher_computers=[],
        connection=None,
    ):
        self.school = school
        self.name = name if name else uts.random_name()
        self.description = description if description else uts.random_name()
        self.host_members = host_members if host_members else []
        self.teacher_computers = teacher_computers
        self.ucr = ucr_test.UCSTestConfigRegistry()
        self.ucr.load()
        self.client = connection if connection else Client.get_test_connection()

    def dn(self):
        return "cn=%s-%s,cn=raeume,cn=groups,%s" % (
            self.school,
            self.name,
            utu.UCSTestSchool().get_ou_base_dn(self.school),
        )

    def add(self, should_pass=True):
        param = [
            {
                "object": {
                    "school": self.school,
                    "name": self.name,
                    "description": self.description,
                    "computers": self.host_members,
                    "teacher_computers": self.teacher_computers,
                },
                "options": None,
            }
        ]
        print("Adding school room %s with UMCP:%s" % (self.name, "schoolrooms/add"))
        print("param = %r" % (param,))
        reqResult = self.client.umc_command("schoolrooms/add", param).result
        utils.wait_for_replication()
        assert bool(reqResult[0]) == should_pass
        if should_pass:
            print("School room created successfully: %s" % (self.name,))
        else:
            print("School room (%r) addition failed as expected." % (self.name,))

    def assert_backend_role(self):  # type: () -> None
        """
        Checks for the presence/absence of the veyon backend role in the rooms ldap object.

        :raises AssertionError: If the assertion is not fulfilled.
        """
        lo = utils.get_ldap_connection()
        roles = lo.getAttr(self.dn(), "ucsschoolRole")
        veyon_role = create_ucsschool_role_string(
            role_computer_room_backend_veyon, "-", context_type_school
        )
        assert veyon_role.encode("UTF-8") in roles

    def verify_ldap(self, must_exist=True):
        # TODO: verify all attributes of object
        utils.verify_ldap_object(self.dn(), should_exist=must_exist)

    def get(self, should_exist=True):
        """gets school room via UMCP\n
        :param should_exist: True if the school room is expected to be found
        :type should_exist: bool"""
        print("Calling %s for %s" % ("schoolrooms/get", self.dn()))
        reqResult = self.client.umc_command("schoolrooms/get", [self.dn()]).result
        assert (
            bool(reqResult[0]["name"]) == should_exist
        ), "Unexpected fetching result for school room (%r)" % (self.dn())
        return reqResult[0]

    def check_get(self, expected_attrs):
        """checks if the result of get command matches the
        expected attributes.
        """
        current_attrs = self.get()
        assert (
            current_attrs == expected_attrs
        ), "The current attrbutes (%r) do not match the expected ones (%r)" % (
            current_attrs,
            expected_attrs,
        )

    def query(self):
        """Get all school rooms via UMCP\n
        :returns: [str] list of school rooms names
        """
        print("Calling %s = get all school rooms" % ("schoolrooms/query"))
        rooms = self.client.umc_command(
            "schoolrooms/query", {"school": self.school, "pattern": ""}
        ).result
        return [x["name"] for x in rooms]

    def check_query(self, rooms):
        current_rooms = self.query()
        assert set(rooms).issubset(
            set(current_rooms)
        ), "Rooms query result: %r, expected to contain at least:%r" % (current_rooms, rooms)

    def put(self, new_attributes):
        """Modify school room via UMCP\n
        with no args passed this only reset the school room properties\n
        :param new_attributes:
        :type new_attributes: dict
        """
        new_name = new_attributes.get("name") if new_attributes.get("name") else self.name
        new_description = (
            new_attributes.get("description") if new_attributes.get("description") else self.description
        )
        new_host_members = (
            new_attributes.get("computers") if new_attributes.get("computers") else self.host_members
        )

        param = [
            {
                "object": {
                    "school": self.school,
                    "name": new_name,
                    "description": new_description,
                    "computers": new_host_members,
                    "teacher_computers": new_attributes.get("teacher_computers", self.teacher_computers),
                    "$dn$": self.dn(),
                },
                "options": None,
            }
        ]
        print("Modifying school room %s with UMCP:%s" % (self.dn(), "schoolrooms/put"))
        print("param = %r" % (param,))
        reqResult = self.client.umc_command("schoolrooms/put", param).result
        assert reqResult, "Unable to modify school room (%r)" % (param,)
        self.name = new_name
        self.description = new_description
        self.host_members = new_host_members
        utils.wait_for_replication()

    def check_put(self, new_attributes):
        new_attributes.update(
            {
                "school": self.school,
                "$dn$": self.dn(),
                "objectType": "groups/group",
                "hosts": new_attributes.get("computers"),
            }
        )
        self.put(new_attributes)
        current_attributes = self.get(True)
        new_attributes.update(
            {
                "name": self.name,
                "$dn$": self.dn(),
                "ucsschool_roles": [
                    create_ucsschool_role_string(
                        role_computer_room_backend_veyon, "-", context_type_school
                    ),
                    create_ucsschool_role_string(role_computer_room, self.school),
                ],
            }
        )
        diff = "\n".join(
            "%s (got=%r; expected=%r)" % (key, current_attributes.get(key), new_attributes.get(key))
            for key in set(current_attributes.keys()) | set(new_attributes.keys())
            if current_attributes.get(key) != new_attributes.get(key)
        )
        assert current_attributes == new_attributes, (
            "Modifying room %s was not successful\ncurrent attributes= %r\nexpected attributes= %r\ndiff: %s"
            % (self.name, current_attributes, new_attributes, diff)
        )

    def remove(self):
        """removes school room via UMCP"""
        print("Calling %s for %s" % ("schoolrooms/remove", self.dn()))
        options = [{"object": [self.dn()], "options": None}]
        reqResult = self.client.umc_command("schoolrooms/remove", options).result
        utils.wait_for_replication()
        assert reqResult[0]["success"], "Unable to remove school room (%r)" % (self.dn(),)


class ComputerRoomSaml(ComputerRoom):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("connection", ClientSaml.get_test_connection())
        super(ComputerRoomSaml, self).__init__(*args, **kwargs)
