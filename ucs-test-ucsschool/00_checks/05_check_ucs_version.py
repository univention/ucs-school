#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Check if UCS 5.0 is installed
## tags: [apptest,ucsschool]
## exposure: safe
## bugs: [40475]

import subprocess
import univention.config_registry

EXPECTED_VERSION = "5.0"


def test_ucs_version():
    ucr = univention.config_registry.ConfigRegistry()
    ucr.load()

    subprocess.call(['univention-app', 'info'])
    current_version = ucr.get("version/version", "")
    assert (
        current_version == EXPECTED_VERSION
    ), "Expected UCS version (%s) does not match with installed UCS version (%s)!" % (
        EXPECTED_VERSION,
        current_version,
    )
