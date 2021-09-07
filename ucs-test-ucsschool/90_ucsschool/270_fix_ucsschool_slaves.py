#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Fix broken Replica Directory Node objects via fix_ucsschool_slaves
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-import,ucs-school-multiserver]

from __future__ import absolute_import, print_function

import subprocess
import sys


def test_fix_ucsschool_slaves(schoolenv):
    school, oudn = schoolenv.create_ou()

    lo = schoolenv.open_ldap_connection()
    result = lo.search(base=oudn, attr=["ucsschoolHomeShareFileServer"])
    try:
        dcdn = result[0][1].get("ucsschoolHomeShareFileServer", [None])[0].decode("UTF-8")
    except IndexError:
        dcdn = None
    assert dcdn is not None, "Cannot determine DN of school server"

    result = lo.search(base=dcdn)
    attrs = result[0][1]
    if {b"univentionWindows", b"ucsschoolComputer"} & set(attrs.get("objectClass", [])):
        print("WARNING: Replica Directory Node's objectclass already broken!")
    for value in attrs.get("ucsschoolRole", []):
        if value.startswith("win_computer:school:"):
            print("WARNING: Replica Directory Node's ucschoolRole already broken! {!r}".format(value))

    lo.modify(
        dcdn,
        [
            [
                "objectClass",
                attrs.get("objectClass", []),
                list(set(attrs.get("objectClass", [])) | {b"univentionWindows", b"ucsschoolComputer"}),
            ],
            [
                "ucsschoolRole",
                attrs.get("ucsschoolRole", []),
                list(
                    set(attrs.get("ucsschoolRole", []))
                    | {"win_computer:school:{}".format(school).encode()}
                ),
            ],
        ],
    )

    print("Starting to fix UCS@school Replica Directory Node...")
    sys.stdout.flush()
    sys.stderr.flush()
    subprocess.check_call(["/usr/share/ucs-school-import/scripts/fix_ucsschool_slaves", "--verbose"])

    result = lo.search(base=dcdn)
    assert not {b"univentionWindows", b"ucsschoolComputer"} & set(result[0][1].get("objectClass", []))
    for value in result[0][1].get("ucsschoolRole", []):
        assert not value.startswith(b"win_computer:school:")
