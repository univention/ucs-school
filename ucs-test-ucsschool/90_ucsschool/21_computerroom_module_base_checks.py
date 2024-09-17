#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: computerroom module base checks
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-computerroom]
from __future__ import print_function

import subprocess

import pytest

from ucsschool.lib.models.computer import (
    IPComputer,
    LinuxComputer,
    MacComputer,
    UbuntuComputer,
    WindowsComputer,
)
from univention.testing.ucsschool.computer import Computer, Computers
from univention.testing.ucsschool.computerroom import Room
from univention.testing.umc import Client


@pytest.mark.parametrize(
    "computer_class,computer_type",
    [
        (WindowsComputer, "windows"),
        (UbuntuComputer, "ubuntu"),
        (LinuxComputer, "linux"),
        (MacComputer, "mac"),
        (IPComputer, "ipmanagedclient"),
    ],
)
def test_computer_without_ip_and_mac_is_ignored(schoolenv, computer_class, computer_type):
    school, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
    tea, _ = schoolenv.create_user(school, is_teacher=True)
    lo = schoolenv.open_ldap_connection()

    computer = Computer(school=school, ctype=computer_type)
    computer.ip = []
    computer.mac = []
    computer_class(**computer.get_args()).create(lo)

    room = Room(school, host_members=[computer.dn])
    schoolenv.create_computerroom(
        school, name=room.name, description=room.description, host_members=room.host_members
    )
    client = Client(None, tea, "univention")
    room.checK_room_aquire(client, "OK")
    room.check_room_computers(client, [computer.dn])


def test_computerroom_module_base_checks(schoolenv, ucr):
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    tea1, tea1_dn = schoolenv.create_user(school, is_teacher=True)
    tea2, tea2_dn = schoolenv.create_user(school, is_teacher=True)
    open_ldap_co = schoolenv.open_ldap_connection()

    print("importing random 9 computers")
    computers = Computers(open_ldap_co, school, 3, 3, 3)
    created_computers = computers.create()
    created_computers_dn = computers.get_dns(created_computers)

    print("setting an empty computer room")
    room1 = Room(school)
    print("setting 2 computer rooms contain the created computers")
    room2 = Room(school, host_members=created_computers_dn[0:4])
    room3 = Room(school, host_members=created_computers_dn[4:9])

    print("Creating the rooms")
    for room in [room1, room2, room3]:
        schoolenv.create_computerroom(
            school, name=room.name, description=room.description, host_members=room.host_members
        )

    print("Checking empty room properties")
    client1 = Client(None, tea1, "univention")
    room1.checK_room_aquire(client1, "EMPTY_ROOM")
    room1.check_room_user(client1, None)

    print("Checking non-empty room properties")
    client2 = Client(None, tea2, "univention")
    room2.checK_room_aquire(client2, "OK")
    room2.check_room_user(client1, tea2)
    room2.check_room_computers(client2, created_computers_dn[0:4])

    print("switching room for tea2")
    room3.checK_room_aquire(client2, "OK")
    room3.check_room_user(client1, tea2)
    room3.check_room_computers(client2, created_computers_dn[4:9])


def test_veyon_down(schoolenv):
    subprocess.check_call(["univention-app", "stop", "ucsschool-veyon-proxy"])
    try:
        school, _ = schoolenv.create_ou(name_edudc=schoolenv.ucr.get("hostname"))
        tea, _ = schoolenv.create_user(school, is_teacher=True)
        lo = schoolenv.open_ldap_connection()

        computer = Computer(school=school, ctype="windows")
        lo = schoolenv.open_ldap_connection()
        WindowsComputer(**computer.get_args()).create(lo)

        room = Room(school, host_members=[computer.dn])
        schoolenv.create_computerroom(
            school, name=room.name, description=room.description, host_members=room.host_members
        )
        client = Client(None, tea, "univention")
        room.checK_room_aquire(client, "OK")
        room.check_room_computers(client, [computer.dn])
    finally:
        subprocess.check_call(["univention-app", "start", "ucsschool-veyon-proxy"])
