#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-singleserver-check
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: safe
## packages:
##    - ucs-school-multiserver | ucs-school-singleserver

from __future__ import print_function

import subprocess

import univention.testing.ucr as ucr_test


def test_ucs_school_singlemaster_check():
    dpkg_query = (
        subprocess.Popen(
            ["dpkg-query", "-W", "-f", "${Status}\n", "ucs-school-singleserver"], stdout=subprocess.PIPE
        )
        .communicate()[0]
        .decode("UTF-8")
    )
    ucr = ucr_test.UCSTestConfigRegistry()
    ucr.load()
    if ucr.is_true("ucsschool/singlemaster"):
        assert dpkg_query == "install ok installed\n", (
            "ucs-school-singleserver is not installed ",
            ucr.get("ucsschool/singlemaster"),
        )
        print("ucs-school-singleserver is installed")
        print("ucsschool/singlemaster =", ucr.get("ucsschool/singlemaster"), " (Correct Value)")
    else:
        assert dpkg_query != "install ok installed\n", (
            "ucs-school-singleserver is installed ",
            ucr.get("ucsschool/singlemaster"),
        )
        print("ucs-school-singleserver is not installed ")
        print("ucsschool/singlemaster = false", " (Correct Value)")
