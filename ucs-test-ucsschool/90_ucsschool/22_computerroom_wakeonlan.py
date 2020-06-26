#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: send wol signal to multiple broadcast-ips
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-computerroom, tshark]

import re
import socket
import subprocess
import time

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from univention.management.console.modules import computerroom
from univention.testing.ucsschool.computerroom import UmcComputer


def main():
    logger = utu.get_ucsschool_logger()
    target_broadcast_ips = ["255.255.255.255", "10.200.47.254"]
    t_shark_timeout = 10
    t_shark_duration = t_shark_timeout * 5
    with utu.UCSTestSchool() as schoolenv, ucr_test.UCSTestConfigRegistry() as ucr:
        school, _ = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
        computer = UmcComputer(school, "windows")
        computer.create()
        mac_address = computer.mac_address
        hostname = socket.gethostname()
        server_ip = socket.gethostbyname(hostname)

        proc = subprocess.Popen(
            [
                "tshark",
                "-i",
                "any",
                "-a",
                "duration:{}".format(t_shark_duration),
                "src",
                "host",
                server_ip,
            ],
            stdout=subprocess.PIPE,
            close_fds=True,
        )
        logger.info("Wait {}s for tshark to get ready (...)".format(t_shark_timeout))
        time.sleep(t_shark_timeout)
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
        stdout, stderr = proc.communicate()

        # I simply check if a WoL signal was sent. Alternatively, we
        # can search for the expected payload. tshark must then have the argument -x.
        # addr = re.sub(r'[.:-]', '', mac_address)
        # payload_hex = 'FFFFFFFFFFFF' + (addr * 16).encode()
        # payload = bytes(bytearray.fromhex(payload_hex))
        assert computer.mac_address in stdout
        for b_ip in target_broadcast_ips:
            regex = r".*{}.+?{} WOL \d+ MagicPacket for {}.*".format(server_ip, b_ip, mac_address)
            successful_send = re.match(regex, str(stdout), re.DOTALL)
            if successful_send:
                logger.info("Packages were successfully sent to {}".format(b_ip))
            elif b_ip in str(stdout):
                logger.info("Could not send WoL signal to {}".format(b_ip))
                logger.info("This is the expected behaviour, since it is not reachable.")
            else:
                logger.info("tshark output was\n{}".format(stdout))
                utils.fail("Did not succeed to send WoL to {}".format(b_ip))


if __name__ == "__main__":
    main()
