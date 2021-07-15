#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-singlemaster-check
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: safe
## packages:
##    - ucs-school-master | ucs-school-singlemaster

from __future__ import print_function

import subprocess

import univention.testing.ucr as ucr_test


def test_ucs_school_singlemaster_check():
    dpkg_query = (
        subprocess.Popen(
            ["dpkg-query", "-W", "-f", "${Status}\n", "ucs-school-singlemaster"], stdout=subprocess.PIPE
        )
        .communicate()[0]
        .decode("UTF-8")
    )
    ucr = ucr_test.UCSTestConfigRegistry()
    ucr.load()
    if ucr.is_true("ucsschool/singlemaster"):
        assert dpkg_query == "install ok installed\n", (
            "ucs-school-singlemaster is not installed ",
            ucr.get("ucsschool/singlemaster"),
        )
        print("ucs-school-singlemaster is installed")
        print("ucsschool/singlemaster =", ucr.get("ucsschool/singlemaster"), " (Correct Value)")
    else:
        assert dpkg_query != "install ok installed\n", (
            "ucs-school-singlemaster is installed ",
            ucr.get("ucsschool/singlemaster"),
        )
        print("ucs-school-singlemaster is not installed ")
        print("ucsschool/singlemaster = false", " (Correct Value)")
