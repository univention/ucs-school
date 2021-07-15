#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: send wol signal to multiple broadcast-ips
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [SKIP-UCSSCHOOL,apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-computerroom, tshark]

import re
import socket
import subprocess
import time

import univention.testing.ucsschool.ucs_test_school as utu
from univention.management.console.modules import computerroom
from univention.testing.ucsschool.computerroom import UmcComputer


def test_computerroom_wakeonlan(schoolenv, ucr):
    logger = utu.get_ucsschool_logger()
    target_broadcast_ips = ["255.255.255.255", "10.200.47.254"]
    tshark_duration = 15
    max_iterations = 10
    hostname = socket.gethostname()
    server_ip = socket.gethostbyname(hostname)
    proc = subprocess.Popen(
        ["tshark", "-i", "any", "src", "host", server_ip], stdout=subprocess.PIPE, close_fds=True
    )

    school, _ = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    computer = UmcComputer(school, "windows")
    computer.create()
    mac_address = computer.mac_address
    regexes = {}
    for j, b_ip in enumerate(target_broadcast_ips):
        regexes[b_ip] = r".*{}.+?{} WOL \d+ MagicPacket for {}.*".format(
            server_ip, b_ip, mac_address
        )

    for i in range(max_iterations):
        start = time.time()
        wol_received = {b_ip: False for b_ip in target_broadcast_ips}
        logger.info(
            "Send WoL signals to {} to broadcast-ips {}".format(mac_address, target_broadcast_ips)
        )
        try:
            computerroom.wakeonlan.send_wol_packet(
                mac_address, target_broadcast_ips=target_broadcast_ips
            )
        except socket.error:
            # Non-existing ips raise errors,
            # thus they have to be put last in the list.
            # A more extensive test would have multiple machines with
            # different broadcast-ips. We decided this would produce too much overhead.
            pass
        while True:
            line = proc.stdout.readline().decode("UTF-8")
            if line == "" and proc.poll() is not None:
                break
            different_sub_net = [ele for ele in target_broadcast_ips if ele in str(line)]
            if computer.mac_address in line:
                for b_ip, regex in regexes.items():
                    successful_send = re.match(regex, str(line), re.DOTALL)
                    if successful_send:
                        logger.info("Packages were successfully sent to {}".format(b_ip))
                        wol_received[b_ip] = True
            elif different_sub_net:
                wol_received[different_sub_net[0]] = True
                logger.info("Could not send WoL signal to {}".format(different_sub_net))
                logger.info("This is the expected behaviour, since it is not reachable.")
            if all(wol_received.values()) or (time.time() - start > tshark_duration):
                break
        if all(wol_received.values()) or (time.time() - start > tshark_duration):
            break

    proc.terminate()
    assert all(wol_received.values())
