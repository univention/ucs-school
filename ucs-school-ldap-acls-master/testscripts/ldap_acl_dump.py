#!/usr/bin/python3
#
# UCS@school
#
# SPDX-FileCopyrightText: 2016-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import print_function

import argparse
import subprocess
import sys

import ldif

import univention.admin.uldap


def normalize_permission(perms):
    level_to_priv = {
        "none": "0",
        "disclose": "d",
        "auth": "xd",
        "compare": "cxd",
        "search": "scxd",
        "read": "rscxd",
        "write": "wrscxd",
        "add": "arscxd",
        "delete": "zrscxd",
        "manage": "mwrscxd",
    }
    if not perms.startswith("="):
        perms = "=%s" % level_to_priv[perms.split("(", 1)[0]]
    return perms


def parse_acls(args, lo):
    writer = ldif.LDIFWriter(args.output)
    code = 0
    for dn, attrs in lo.search(base=args.base):
        entry = {}
        for attr in attrs:
            # TODO: replace subprocess with some C calls to improove speed
            process = subprocess.Popen(  # nosec
                ["/usr/sbin/slapacl", "-d0", "-D", args.binddn, "-b", dn, attr], stderr=subprocess.PIPE
            )
            _, stderr = process.communicate()
            for line in stderr.decode("UTf-8").splitlines():
                if line.startswith("%s: " % (attr,)):
                    entry.setdefault(attr, []).append(
                        normalize_permission(line.split(": ", 1)[-1].strip()).encode("UTF-8")
                    )
            try:
                entry[attr]
            except KeyError as exc:
                print(dn, exc, file=sys.stderr)
                code = 1
        writer.unparse(dn, entry)
    return code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", "--base")
    parser.add_argument("-o", "--output", type=argparse.FileType("w"), default="-")
    parser.add_argument("binddn")
    args = parser.parse_args()
    lo, po = univention.admin.uldap.getAdminConnection()
    sys.exit(parse_acls(args, lo))


if __name__ == "__main__":
    main()
