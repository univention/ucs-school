#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## bugs: [40470]
## desc: Check values of school-servers (except Primary Directory Nodes and Backup Directory Nodes) DNS related ucr variables  # noqa: E501
## exposure: safe
## roles:
##  - domaincontroller_slave
## tags: [apptest, ucsschool]
## package: [ucs-school-replica]


def test_check_dns_ucr_variables(ucr):
    ucrv_forward = ucr.get("dns/nameserver/registration/forward_zone")
    assert ucr.is_false(value=ucrv_forward), (
        "The ucr variable 'dns/nameserver/registration/forward_zone' is set to '%s', but must be set"
        " to 'no'." % (ucrv_forward,)
    )
    ucrv_reverse = ucr.get("dns/nameserver/registration/reverse_zone")
    assert ucr.is_false(value=ucrv_reverse), (
        "The ucr variable 'dns/nameserver/registration/reverse_zone' is set to '%s', but must be set"
        " to 'no'." % (ucrv_reverse,)
    )
