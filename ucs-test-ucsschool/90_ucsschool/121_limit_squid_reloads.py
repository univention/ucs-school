#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: check number of squid reloads
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master,domaincontroller_slave]
## bugs: [41361]
## exposure: dangerous
## packages:
##   - ucs-school-webproxy

import datetime
import os
import re
import time

from univention.config_registry import handler_set, handler_unset

LOGFILE = "/var/log/squid/cache.log"
RELOAD_PATTERN = r"(..../../.. ..:..:.. \w+\| Reconfiguring Squid Cache?)"
TEST_UCR = ("proxy/filter/domain/whitelisted/2000", "www.univention.com")


def test_limit_squid_reloads(ucr):
    # wait for reload triggered by previous installation/test
    time.sleep(20)
    # find end of logfile
    with open(LOGFILE, "rb") as log:
        log.seek(0, os.SEEK_END)
        logfile_pos = log.tell()
    # every handler_set and handler_unset of proxy/filter/.*
    # (ucs-school-webproxy/debian/ucs-school-webproxy.univention-config-registry)
    # triggers the UCR module, which triggers a squid reload
    start = datetime.datetime.now()
    while datetime.datetime.now() - start < datetime.timedelta(seconds=20):
        # this must take between 16 and 29s!
        # it will trigger:
        # * the 1st time
        # * again after 15s
        # * a 3rd time for all UCR[un]sets between 16s and 29s
        print("*** time: {}".format(time.strftime("%H:%M:%S")))
        handler_set(["{}={}".format(*TEST_UCR)])
        time.sleep(1)
        handler_unset([TEST_UCR[0]])
        time.sleep(1)
    # let time for another reload pass
    print("*** time: {}, sleeping 20s...".format(time.strftime("%H:%M:%S")))
    time.sleep(20)
    with open(LOGFILE, "rb") as log:
        log.seek(logfile_pos)
        reloads = re.findall(RELOAD_PATTERN, log.read().decode("utf-8"))
    print("*** reloads:\n{}\n***".format("\n".join(reloads)))
    reload_count = len(reloads)
    assert reload_count in (2, 3), "Wrong number of reloads ({}) were triggered.".format(reload_count)
    print("*** OK: Squid was reloaded {} times.".format(reload_count))
