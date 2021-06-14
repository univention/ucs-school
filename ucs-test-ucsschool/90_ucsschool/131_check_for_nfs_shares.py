#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: Check if there are shares with NFS option on
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-import]
## bugs: [38641, 42504, 42514]

from ucsschool.lib.models.school import School
from ucsschool.lib.models.share import Share


def test_check_for_nfs_shares(schoolenv):
    nfs_shares = []
    for school in School.get_all(schoolenv.lo):
        for share in Share.get_all(schoolenv.lo, school.name):
            share_udm = share.get_udm_object(schoolenv.lo)
            if "nfs" in share_udm.options:
                if share.name in ["Marktplatz", "iTALC-Installation"]:
                    print("*** Ignoring //{}/{} (Bug #42514)".format(school.name, share.name))
                else:
                    nfs_shares.append((school.name, share.name))

    assert not nfs_shares
    print(
        "*** No shares found in schools {}.".format(
            ", ".join(s.name for s in School.get_all(schoolenv.lo))
        )
    )
