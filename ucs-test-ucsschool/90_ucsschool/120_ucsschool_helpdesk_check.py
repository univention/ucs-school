#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-helpdesk - send mail via helpdesk module
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-helpdesk]

from __future__ import print_function

import tempfile
import time

from univention.testing import utils
from univention.config_registry import handler_set
from univention.testing.mail import MailSink
from univention.testing.network import NetworkRedirector
from univention.testing.umc import Client


def test_ucsschool_helpdesk(schoolenv, ucr):
    # initializing mail data
    message = time.time() * 1000
    message = "%.30f" % message
    with NetworkRedirector() as nethelper, tempfile.NamedTemporaryFile(suffix=".eml", dir="/tmp") as fd:
        # creating ou & a teacher
        school, _ = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
        tea, _ = schoolenv.create_user(school, is_teacher=True)
        utils.wait_for_replication_and_postrun()
        handler_set(["ucsschool/helpdesk/recipient=ucstest@univention.de"])
        host = ucr.get("hostname")
        connection = Client(host)
        connection.authenticate(tea, "univention")
        print("Creating temp mail file %s" % (fd.name))
        nethelper.add_redirection("0.0.0.0/0", 25, 60025)
        ms = MailSink("127.0.0.1", 60025, filename=fd.name)
        ms.start()
        params = {"username": tea, "school": school, "category": "Sonstige", "message": message}
        # Sending the mail message with the unique id
        print("Sending message...")
        result = connection.umc_command("helpdesk/send", params).result
        assert result, "Message was not sent successfully"
        print("Message sent.")
        # time out for waiting for the message to be delivered    in seconds
        timeOut = 60
        print("Waiting %ds for incoming mail..." % (timeOut,))
        # periodically checking the receipt of the same sent mail
        for i in range(timeOut, 0, -1):
            print(i, end=" ")
            if message in open(fd.name).read():
                print("\nUnique id was found in target file %r" % (fd.name,))
                ms.stop()
                return
            time.sleep(1)
        print()
        ms.stop()
        raise AssertionError("Unique id was not found in target file")
