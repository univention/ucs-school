#!/usr/share/ucs-test/runner python
## desc: Check if there are shares with NFS option on
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-import]
## bugs: [38641, 42504, 42514]

import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models import School, Share


def main():
    with utu.UCSTestSchool() as schoolenv:
        nfs_shares = list()
        for school in School.get_all(schoolenv.lo):
            for share in Share.get_all(schoolenv.lo, school.name):
                share_udm = share.get_udm_object(schoolenv.lo)
                if "nfs" in share_udm.options:
                    if share.name in ["Marktplatz", "iTALC-Installation"]:
                        print("*** Ignoring //{}/{} (Bug #42514)".format(school.name, share.name))
                    else:
                        nfs_shares.append((school.name, share.name))

        if nfs_shares:
            utils.fail(
                "Found NFS shares:\n* {}".format(
                    "\n* ".join(["school: %r share: %r" % nfs_share for nfs_share in nfs_shares])
                )
            )
        else:
            print(
                "*** No shares found in schools {}.".format(
                    ", ".join(s.name for s in School.get_all(schoolenv.lo))
                )
            )


if __name__ == "__main__":
    main()
