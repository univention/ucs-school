#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: computerroom two rooms settings
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,SKIP-UCSSCHOOL,ucsschool_base1]
## timeout: 14400
## exposure: dangerous
## packages: [ucs-school-umc-computerroom]


from __future__ import print_function

import datetime
import itertools

import univention.testing.strings as uts
from univention.lib.umc import ConnectionError
from univention.testing.network import NetworkRedirector
from univention.testing.ucsschool.computer import Computers
from univention.testing.ucsschool.computerroom import Room, add_printer, clean_folder, remove_printer
from univention.testing.ucsschool.internetrule import InternetRule
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client


def print_header(
    i, room1_rule, room1_printmode, room1_sharemode, j, room2_rule, room2_printmode, room2_sharemode
):
    print(
        "\n** ROOM 1\n** (%d) (internetRule, printMode, shareMode) = (%s, %s, %s)"
        % (
            i,
            room1_rule,
            room1_printmode,
            room1_sharemode,
        )
    )
    print(
        "\n** ROOM 2\n** (%d) (internetRule, printMode, shareMode) = (%s, %s, %s)"
        % (
            j,
            room2_rule,
            room2_printmode,
            room2_sharemode,
        )
    )


def test_computerroom_two_room_settings_interference(schoolenv, ucr):
    with NetworkRedirector() as nethelper:
        school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
        tea, tea_dn = schoolenv.create_user(school, is_teacher=True)
        open_ldap_co = schoolenv.open_ldap_connection()

        # importing random 2 computers
        computers = Computers(open_ldap_co, school, 2, 0, 0)
        created_computers = computers.create()
        computers_dns = computers.get_dns(created_computers)
        computers_ips = [x.ip for x in computers]

        # setting computer rooms contains the created computers
        room1 = Room(school, host_members=computers_dns[0])
        room2 = Room(school, host_members=computers_dns[1])
        # Creating the rooms
        for room in [room1, room2]:
            schoolenv.create_computerroom(
                school,
                name=room.name,
                description=room.description,
                host_members=room.host_members,
            )

        # preparing the network loop
        nethelper.add_loop(computers_ips[0], computers_ips[1])

        client = Client(ucr.get("hostname"))
        client.authenticate(tea, "univention")

        printer_name = uts.random_string()
        try:
            # Create new workgroup and assign new internet rule to it
            group = Workgroup(school, members=[tea_dn])
            global_domains = ["download.univention.de", "google.de"]
            rule = InternetRule(typ="whitelist", domains=global_domains)
            rule.define()
            rule.assign(school, group.name, "workgroup")

            # Add new hardware printer
            add_printer(
                printer_name,
                school,
                ucr.get("hostname"),
                ucr.get("domainname"),
                ucr.get("ldap/base"),
            )

            # generate all the possible combinations for (rule, printmode, sharemode)
            white_page = "download.univention.de"
            rules = ["none", "Kein Internet", "Unbeschränkt", "custom"]
            printmodes = ["default", "all", "none"]
            sharemodes = ["all", "home"]
            room1_settings = itertools.product(rules, printmodes, sharemodes)
            # import pdb; pdb.set_trace()

            # Choosing offset times for settings
            # should be at least 3 mins after user creation
            room1_time = 2 * 15 * 60
            room2_time = room1_time + 10 * 60

            # Testing loop over room1 settings
            for i in range(24):
                room1_period = datetime.time.strftime(
                    (datetime.datetime.now() + datetime.timedelta(0, room1_time)).time(), "%H:%M"
                )

                # get room1 old settings
                room1.aquire_room(client)
                room1_old_settings = room1.get_room_settings(client)
                del room1_old_settings["customRule"]
                room1_old_settings["period"] = room1_old_settings["period"][:-3]

                room1_rule, room1_printmode, room1_sharemode = next(room1_settings)
                room1_new_settings = {
                    "customRule": white_page,
                    "printMode": room1_printmode,
                    "internetRule": room1_rule,
                    "shareMode": room1_sharemode,
                    "period": room1_period,
                }
                room1.set_room_settings(client, room1_new_settings)

                # Testing loop over room2 settings
                room2_settings = itertools.product(rules, printmodes, sharemodes)
                for j in range(24):
                    try:
                        room2_period = datetime.time.strftime(
                            (datetime.datetime.now() + datetime.timedelta(0, room2_time)).time(),
                            "%H:%M",
                        )
                        room2_rule, room2_printmode, room2_sharemode = next(room2_settings)

                        print_header(
                            i,
                            room1_rule,
                            room1_printmode,
                            room1_sharemode,
                            j,
                            room2_rule,
                            room2_printmode,
                            room2_sharemode,
                        )

                        room2_new_settings = {
                            "customRule": white_page,
                            "printMode": room2_printmode,
                            "internetRule": room2_rule,
                            "shareMode": room2_sharemode,
                            "period": room2_period,
                        }
                        room1.set_room_settings(client, room1_new_settings)

                        room2.aquire_room(client)
                        room2.set_room_settings(client, room2_new_settings)

                        # Check room1 settings
                        room1.aquire_room(client)
                        room1.check_room_settings(client, room1_new_settings)
                        room1.check_behavior(
                            room1_old_settings,
                            room1_new_settings,
                            tea,
                            computers_ips[1],
                            printer_name,
                            white_page,
                            global_domains,
                            ucr,
                        )
                        # For DEBUG purposes
                        # run_commands([
                        # ['ucr', 'search', room1.name],
                        # ['ucr','search', room2.name],
                        # ['atq']
                        # ], {})
                        clean_folder("/home/gsmitte/groups/Marktplatz/")
                        clean_folder("/home/%s/lehrer/%s/" % (school, tea))
                    # TODO Exception Errno4
                    except ConnectionError as e:
                        if "[Errno 4] Unterbrechung" in str(e):
                            print(
                                "FAILED to get or set room (%s) settings, exception"
                                "[Errno4]" % (room2.name,)
                            )
                        else:
                            print("Exception: '%s' '%s' '%r'" % (str(e), type(e), e))
                            raise
        finally:
            remove_printer(printer_name, school, ucr.get("ldap/base"))
