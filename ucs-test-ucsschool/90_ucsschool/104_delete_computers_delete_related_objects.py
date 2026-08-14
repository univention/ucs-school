#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Delete computer deletes all related objects
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1,skip_in_large_schoolenv]
## exposure: dangerous
## packages: [ucs-school-umc-computerroom]

# Skipped with Issue univention/ucsschool#1235 in large schoolenv because of flakyness

from functools import partial

from ldap import NO_SUCH_OBJECT

import univention.testing.ucr as ucr_test
from univention.testing import utils
from univention.testing.ucsschool.computerroom import UmcComputer
from univention.uldap import getMachineConnection

ucr = ucr_test.UCSTestConfigRegistry()
ucr.load()

# The related objects are not gone the instant the UMC request returns:
# the S4 connector syncs the deletion to Samba/AD, and the AD -> UCS direction
# transiently re-creates the DNS host record before a later round removes it again
# (see univention/ucsschool#850). utils.wait_for_s4connector_replication() gives up
# after 17 seconds with nothing but a warning, so poll instead of checking once.
RETRY_COUNT = 12
RETRY_DELAY = 5


def dns_forward():
    return "zoneName=%s,cn=dns,%s" % (ucr.get("domainname"), ucr.get("ldap/base"))


def dns_reverse(ip):
    return "zoneName=%s.in-addr.arpa,cn=dns,%s" % (
        ".".join(reversed(ip.split(".")[:3])),
        ucr.get("ldap/base"),
    )


def dhcp_dn(school, computer_name):
    return "cn=%s,cn=%s,cn=dhcp,ou=%s,%s" % (computer_name, school, school, ucr.get("ldap/base"))


def check_computer_ldap(lo, school, computer, should_exist):
    try:
        # Check DNS forward objects
        dns = dns_forward()
        found = lo.search(filter="(aRecord=%s)" % computer.ip_address, base=dns)
        if should_exist:
            assert found, "Object not found:(%r) aRecord=%s" % (dns, computer.ip_address)
        else:
            assert not found, "Object unexpectedly found:(%r)" % found

        computer_name = computer.name
        if computer_name[-1] == "$":
            computer_name = computer_name[:-1]
        # Check DNS reverse objects
        dns = dns_reverse(computer.ip_address)
        found = lo.search(filter="(pTRRecord=%s.%s.)" % (computer_name, ucr.get("domainname")), base=dns)
        if should_exist:
            assert found, "Object not found:(%r), pTRRecord=%s.%s." % (
                dns,
                computer_name,
                ucr.get("domainname"),
            )
        else:
            assert not found, "Object unexpectedly found:(%r)" % found

        # Check DHCP objects
        dhcp = dhcp_dn(school, computer_name)
        found = lo.search(base=dhcp)
        if should_exist:
            assert found, "Object not found:(%r)" % dhcp
        else:
            assert not found, "Object unexpectedly found:(%r)" % dhcp

    except NO_SUCH_OBJECT as ex:
        if should_exist:
            raise AssertionError(ex)


def check_ldap(school, computers, should_exist):
    lo = getMachineConnection()
    for computer in computers:
        utils.retry_on_error(
            partial(check_computer_ldap, lo, school, computer, should_exist),
            exceptions=(AssertionError,),
            retry_count=RETRY_COUNT,
            delay=RETRY_DELAY,
        )


def test_delete_computers_delete_related_objects(schoolenv):
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))

    computers = []
    for computer_type in ["windows", "macos", "ipmanagedclient"]:
        computer = UmcComputer(school, computer_type)
        computer.create()
        computers.append(computer)

    check_ldap(school, computers, should_exist=True)

    for computer in computers:
        computer.remove()
    check_ldap(school, computers, should_exist=False)
