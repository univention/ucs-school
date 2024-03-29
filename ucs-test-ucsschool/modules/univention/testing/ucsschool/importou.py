# -*- coding: utf-8 -*-

from __future__ import print_function

import base64
import random
import subprocess

from six import string_types

import ucsschool.lib.models.utils
import univention.admin.filter
import univention.admin.modules
import univention.admin.uldap
import univention.config_registry
import univention.testing.strings as uts
import univention.testing.ucr
import univention.testing.udm
import univention.uldap
from ucsschool.lib.models.dhcp import DHCPServer
from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import User
from ucsschool.lib.models.utils import add_stream_logger_to_schoollib
from ucsschool.lib.roles import create_ucsschool_role_string, role_school_admin_group
from univention.config_registry.interfaces import Interfaces
from univention.testing import utils
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

univention.admin.modules.update()
add_stream_logger_to_schoollib()


TYPE_DC_ADMINISTRATIVE = "administrative"
TYPE_DC_EDUCATIONAL = "educational"


class DCNotFound(Exception):
    pass


class DCMembership(Exception):
    pass


class DCisMemberOfGroup(Exception):
    pass


class DhcpdLDAPBase(Exception):
    pass


class DhcpServerLocation(Exception):
    pass


def create_mail_domain(ucr, udm):
    if not ucr.get("mail/hosteddomains"):
        try:
            maildomain = ucr["mail/hosteddomains"].split()[0]
        except (AttributeError, IndexError):
            maildomain = ucr["domainname"]

        print("\n\n*** Creating mail domain {!r}...\n".format(maildomain))
        try:
            udm.create_object(
                "mail/domain", position="cn=domain,cn=mail,{}".format(ucr["ldap/base"]), name=maildomain
            )
        except univention.testing.udm.UCSTestUDM_CreateUDMObjectFailed as exc:
            if "Object exists" in str(exc):
                print("\n\n*** Mail domain {!r} exists.\n".format(maildomain))


def remove_ou(ou_name):
    schoolenv = UCSTestSchool()
    # the reload is necessary, otherwise the UCR variables are not up-to-date
    schoolenv.ucr.load()
    schoolenv.cleanup_ou(ou_name)


def get_school_base(ou):
    configRegistry = univention.config_registry.ConfigRegistry()
    configRegistry.load()

    if configRegistry.is_true("ucsschool/ldap/district/enable"):
        return "ou=%(ou)s,ou=%(district)s,%(basedn)s" % {
            "ou": ou,
            "district": ou[0:2],
            "basedn": configRegistry.get("ldap/base"),
        }
    else:
        return "ou=%(ou)s,%(basedn)s" % {"ou": ou, "basedn": configRegistry.get("ldap/base")}


def get_school_ou_from_dn(dn, ucr=None):
    if not ucr:
        ucr = univention.config_registry.ConfigRegistry()
        ucr.load()
    oulist = [x[3:] for x in univention.admin.uldap.explodeDn(dn) if x.startswith("ou=")]
    if ucr.is_true("ucsschool/ldap/district/enable"):
        return oulist[-2]
    return oulist[-1]


def create_ou_cli(
    ou, dc=None, dc_administrative=None, sharefileserver=None, ou_displayname=None, alter_dhcpd_base=None
):
    cmd_block = ["/usr/share/ucs-school-import/scripts/create_ou", "--verbose", ou]
    if dc:
        cmd_block.append(dc)
    if dc_administrative:
        cmd_block.append(dc_administrative)
    if ou_displayname:
        cmd_block.append("--displayName=%s" % ou_displayname)
    if sharefileserver:
        cmd_block.append("--sharefileserver=%s" % sharefileserver)
    if alter_dhcpd_base is None:
        cmd_block.append("--alter-dhcpd-base=%s" % "auto")
    elif alter_dhcpd_base:
        cmd_block.append("--alter-dhcpd-base=%s" % "true")
    elif not alter_dhcpd_base:
        cmd_block.append("--alter-dhcpd-base=%s" % "false")

    print("cmd_block: %r" % cmd_block)
    subprocess.check_call(cmd_block)


def create_ou_python_api(
    ou, dc, dc_administrative, sharefileserver, ou_displayname, alter_dhcpd_base=None
):
    kwargs = {"name": ou, "dc_name": dc}
    if dc_administrative:
        kwargs["dc_name_administrative"] = dc_administrative
    if sharefileserver:
        kwargs["class_share_file_server"] = sharefileserver
        kwargs["home_share_file_server"] = sharefileserver
    if ou_displayname:
        kwargs["display_name"] = ou_displayname
    if alter_dhcpd_base is not None:
        kwargs[alter_dhcpd_base] = alter_dhcpd_base

    # invalidate caches and reload UCR
    ucsschool.lib.models.utils.ucr.load()
    ucsschool.lib.models.utils._pw_length_cache.clear()
    # UCSSchoolHelperAbstractClass._search_base_cache.clear()
    User._profile_path_cache.clear()
    User._samba_home_path_cache.clear()

    lo = univention.admin.uldap.getAdminConnection()[0]
    # TODO FIXME has to be fixed in ucs-school-lib - should be done automatically:
    School.init_udm_module(lo)
    School(**kwargs).create(lo)


def move_domaincontroller_to_ou_cli(dc_name, ou):
    cmd_block = [
        "/usr/share/ucs-school-import/scripts/move_domaincontroller_to_ou",
        "--ou",
        ou,
        "--dcname",
        dc_name,
    ]
    print("cmd_block: %r" % cmd_block)

    subprocess.check_call(cmd_block)


def get_ou_base(ou, district_enable):
    ucr = univention.testing.ucr.UCSTestConfigRegistry()
    ucr.load()

    base_dn = ucr.get("ldap/base")

    if district_enable:
        ou_base = "ou=%s,ou=%s,%s" % (ou, ou[0:2], base_dn)
    else:
        ou_base = "ou=%s,%s" % (ou, base_dn)

    return ou_base


def create_and_verify_ou(
    ucr,
    ou,
    dc,
    sharefileserver,
    dc_administrative=None,
    ou_displayname=None,
    singlemaster=False,
    noneducational_create_objects=False,
    district_enable=False,
    default_dcs=None,
    dhcp_dns_clearou=False,
    do_cleanup=True,
    unset_dhcpd_base=True,
    alter_dhcpd_base_option=None,
    use_cli_api=True,
    use_python_api=False,
):
    assert use_cli_api != use_python_api

    print("******************************************************")
    print("**** create_and_verify_ou test run")
    print("****	ou=%s" % ou)
    print("****	ou_displayname=%r" % ou_displayname)
    print("****	dc=%s" % dc)
    print("****	dc_administrative=%s" % dc_administrative)
    print("****	sharefileserver=%s" % sharefileserver)
    print("****	singlemaster=%s" % singlemaster)
    print("****	noneducational_create_objects=%s" % noneducational_create_objects)
    print("****	district_enable=%s" % district_enable)
    print("****	default_dcs=%s" % default_dcs)
    print("****	dhcp_dns_clearou=%s" % dhcp_dns_clearou)
    print("******************************************************")

    ucr.load()

    lo = univention.uldap.getMachineConnection()

    # set UCR
    univention.config_registry.handler_set(
        [
            "ucsschool/singlemaster=%s" % ("true" if singlemaster else "false"),
            "ucsschool/ldap/noneducational/create/objects=%s"
            % ("true" if noneducational_create_objects else "false"),
            "ucsschool/ldap/district/enable=%s" % ("true" if district_enable else "false"),
            "ucsschool/ldap/default/dcs=%s" % default_dcs,
            "ucsschool/import/generate/policy/dhcp/dns/clearou=%s"
            % ("true" if dhcp_dns_clearou else "false"),
        ]
    )
    if unset_dhcpd_base:
        univention.config_registry.handler_unset(["dhcpd/ldap/base"])
    ucr.load()

    base_dn = ucr.get("ldap/base")

    move_dc_after_create_ou = False

    # does dc exist?
    if singlemaster:
        dc_name = ucr.get("hostname")
    elif dc:
        result = lo.search(
            filter="(&(objectClass=univentionDomainController)(cn=%s))" % dc, base=base_dn, attr=["cn"]
        )
        if result:
            move_dc_after_create_ou = True
        dc_name = dc
    else:
        dc_name = "dc%s" % ou

    if use_cli_api:
        create_ou_cli(
            ou, dc, dc_administrative, sharefileserver, ou_displayname, alter_dhcpd_base_option
        )
    if use_python_api:
        create_ou_python_api(
            ou, dc, dc_administrative, sharefileserver, ou_displayname, alter_dhcpd_base_option
        )

    if move_dc_after_create_ou:
        move_domaincontroller_to_ou_cli(dc_name, ou)

    verify_ou(ou, dc, ucr, sharefileserver, dc_administrative, must_exist=True)

    if do_cleanup:
        remove_ou(ou)


def verify_ou(ou, dc, ucr, sharefileserver, dc_administrative, must_exist):
    print("*** Verifying OU (%s) ... " % ou)
    ucr.load()

    lo = univention.uldap.getMachineConnection()
    base_dn = ucr.get("ldap/base")

    cn_pupils = ucr.get("ucsschool/ldap/default/container/pupils", "schueler")
    cn_teachers = ucr.get("ucsschool/ldap/default/container/teachers", "lehrer")
    cn_teachers_staff = ucr.get(
        "ucsschool/ldap/default/container/teachers-and-staff", "lehrer und mitarbeiter"
    )
    cn_admins = ucr.get("ucsschool/ldap/default/container/admins", "admins")
    cn_staff = ucr.get("ucsschool/ldap/default/container/staff", "mitarbeiter")

    singlemaster = ucr.is_true("ucsschool/singlemaster")
    noneducational_create_objects = ucr.is_true("ucsschool/ldap/noneducational/create/objects")
    district_enable = ucr.is_true("ucsschool/ldap/district/enable")
    # default_dcs = ucr.get('ucsschool/ldap/default/dcs')
    dhcp_dns_clearou = ucr.is_true("ucsschool/import/generate/policy/dhcp/dns/clearou")
    ou_base = get_ou_base(ou, district_enable)

    # does dc exist?
    if singlemaster:
        dc_dn = ucr.get("ldap/hostdn")
        dc_name = ucr.get("hostname")
    elif dc:
        dc_dn = "cn=%s,cn=dc,cn=server,cn=computers,%s" % (dc, ou_base)
        dc_name = dc
    else:
        dc_dn = "cn=dc%s,cn=dc,cn=server,cn=computers,%s" % (ou, ou_base)
        dc_name = "dc%s" % ou

    sharefileserver_dn = dc_dn
    if sharefileserver:
        result = lo.searchDn(
            filter="(&(objectClass=univentionDomainController)(cn=%s))" % sharefileserver,
            base=base_dn,
        )
        if result:
            sharefileserver_dn = result[0]

    utils.verify_ldap_object(
        ou_base,
        expected_attr={
            "ou": [ou],
            "ucsschoolClassShareFileServer": [sharefileserver_dn],
            "ucsschoolHomeShareFileServer": [sharefileserver_dn],
        },
        should_exist=must_exist,
    )

    utils.verify_ldap_object(
        "cn=printers,%s" % ou_base, expected_attr={"cn": ["printers"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=users,%s" % ou_base, expected_attr={"cn": ["users"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=%s,cn=users,%s" % (cn_pupils, ou_base),
        expected_attr={"cn": [cn_pupils]},
        should_exist=must_exist,
    )
    utils.verify_ldap_object(
        "cn=%s,cn=users,%s" % (cn_teachers, ou_base),
        expected_attr={"cn": [cn_teachers]},
        should_exist=must_exist,
    )
    utils.verify_ldap_object(
        "cn=%s,cn=users,%s" % (cn_admins, ou_base),
        expected_attr={"cn": [cn_admins]},
        should_exist=must_exist,
    )
    utils.verify_ldap_object(
        "cn=%s,cn=users,%s" % (cn_admins, ou_base),
        expected_attr={"cn": [cn_admins]},
        should_exist=must_exist,
    )

    utils.verify_ldap_object(
        "cn=computers,%s" % ou_base, expected_attr={"cn": ["computers"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=server,cn=computers,%s" % ou_base, expected_attr={"cn": ["server"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=dc,cn=server,cn=computers,%s" % ou_base,
        expected_attr={"cn": ["dc"]},
        should_exist=must_exist,
    )
    utils.verify_ldap_object(
        "cn=networks,%s" % ou_base, expected_attr={"cn": ["networks"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=groups,%s" % ou_base, expected_attr={"cn": ["groups"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=%s,cn=groups,%s" % (cn_pupils, ou_base),
        expected_attr={"cn": [cn_pupils]},
        should_exist=must_exist,
    )
    utils.verify_ldap_object(
        "cn=%s,cn=groups,%s" % (cn_teachers, ou_base),
        expected_attr={"cn": [cn_teachers]},
        should_exist=must_exist,
    )
    utils.verify_ldap_object(
        "cn=klassen,cn=%s,cn=groups,%s" % (cn_pupils, ou_base),
        expected_attr={"cn": ["klassen"]},
        should_exist=must_exist,
    )
    utils.verify_ldap_object(
        "cn=raeume,cn=groups,%s" % ou_base, expected_attr={"cn": ["raeume"]}, should_exist=must_exist
    )

    utils.verify_ldap_object(
        "cn=dhcp,%s" % ou_base, expected_attr={"cn": ["dhcp"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=policies,%s" % ou_base, expected_attr={"cn": ["policies"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=shares,%s" % ou_base, expected_attr={"cn": ["shares"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=klassen,cn=shares,%s" % ou_base, expected_attr={"cn": ["klassen"]}, should_exist=must_exist
    )
    utils.verify_ldap_object(
        "cn=dc,cn=server,cn=computers,%s" % ou_base,
        expected_attr={"cn": ["dc"]},
        should_exist=must_exist,
    )

    if noneducational_create_objects:
        utils.verify_ldap_object("cn=%s,cn=users,%s" % (cn_staff, ou_base), should_exist=must_exist)
        utils.verify_ldap_object(
            "cn=%s,cn=users,%s" % (cn_teachers_staff, ou_base), should_exist=must_exist
        )
        utils.verify_ldap_object("cn=%s,cn=groups,%s" % (cn_staff, ou_base), should_exist=must_exist)
    else:
        utils.verify_ldap_object("cn=%s,cn=users,%s" % (cn_staff, ou_base), should_exist=False)
        utils.verify_ldap_object("cn=%s,cn=users,%s" % (cn_teachers_staff, ou_base), should_exist=False)
        utils.verify_ldap_object("cn=%s,cn=groups,%s" % (cn_staff, ou_base), should_exist=False)

    if noneducational_create_objects:
        utils.verify_ldap_object(
            "cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % base_dn, should_exist=True
        )
        utils.verify_ldap_object(
            "cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % base_dn, should_exist=True
        )
        utils.verify_ldap_object(
            "cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (ou, base_dn), should_exist=True
        )
        utils.verify_ldap_object(
            "cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (ou, base_dn), should_exist=True
        )
    # This will fail because we don't cleanup these groups in cleanup_ou
    # else:
    # 	utils.verify_ldap_object("cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % base_dn,
    # 	should_exist=False)
    # 	utils.verify_ldap_object("cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % base_dn,
    # 	should_exist=False)
    # 	utils.verify_ldap_object('cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % (ou, base_dn),
    # 	should_exist=False)
    # 	utils.verify_ldap_object('cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s' % (ou,
    # 	base_dn), should_exist=False)

    if not singlemaster:
        verify_dc(ou, dc_name, TYPE_DC_EDUCATIONAL, base_dn, must_exist)

    if dc_administrative:
        verify_dc(ou, dc_administrative, TYPE_DC_ADMINISTRATIVE, base_dn, must_exist)

    grp_prefix_pupils = ucr.get("ucsschool/ldap/default/groupprefix/pupils", "schueler-")
    grp_prefix_teachers = ucr.get("ucsschool/ldap/default/groupprefix/teachers", "lehrer-")
    grp_prefix_admins = ucr.get("ucsschool/ldap/default/groupprefix/admins", "admins-")
    grp_prefix_staff = ucr.get("ucsschool/ldap/default/groupprefix/staff", "mitarbeiter-")

    grp_policy_pupils = ucr.get(
        "ucsschool/ldap/default/policy/umc/pupils",
        "cn=ucsschool-umc-pupils-default,cn=UMC,cn=policies,%s" % base_dn,
    )
    grp_policy_teachers = ucr.get(
        "ucsschool/ldap/default/policy/umc/teachers",
        "cn=ucsschool-umc-teachers-default,cn=UMC,cn=policies,%s" % base_dn,
    )
    grp_policy_admins = ucr.get(
        "ucsschool/ldap/default/policy/umc/admins",
        "cn=ucsschool-umc-admins-default,cn=UMC,cn=policies,%s" % base_dn,
    )
    grp_policy_staff = ucr.get(
        "ucsschool/ldap/default/policy/umc/staff",
        "cn=ucsschool-umc-staff-default,cn=UMC,cn=policies,%s" % base_dn,
    )

    utils.verify_ldap_object(
        "cn=%s%s,cn=ouadmins,cn=groups,%s" % (grp_prefix_admins, ou, base_dn),
        expected_attr={
            "univentionPolicyReference": [grp_policy_admins],
            "ucsschoolRole": [create_ucsschool_role_string(role_school_admin_group, ou)],
        },
        should_exist=True,
    )
    utils.verify_ldap_object(
        "cn=%s%s,cn=groups,%s" % (grp_prefix_pupils, ou, ou_base),
        expected_attr={"univentionPolicyReference": [grp_policy_pupils]},
        should_exist=must_exist,
    )
    utils.verify_ldap_object(
        "cn=%s%s,cn=groups,%s" % (grp_prefix_teachers, ou, ou_base),
        expected_attr={"univentionPolicyReference": [grp_policy_teachers]},
        should_exist=must_exist,
    )

    if noneducational_create_objects:
        utils.verify_ldap_object(
            "cn=%s%s,cn=groups,%s" % (grp_prefix_staff, ou, ou_base),
            expected_attr={"univentionPolicyReference": [grp_policy_staff]},
            should_exist=must_exist,
        )

    check_group_membership(ou, dc_name, base_dn, lo, must_exist)
    check_dhcp(ou_base, dc_name, singlemaster, dhcp_dns_clearou, ucr, must_exist)


def check_group_membership(ou, dc_name, base_dn, lo, must_exist):
    dcmaster_module = univention.admin.modules.get("computers/domaincontroller_master")
    dcbackup_module = univention.admin.modules.get("computers/domaincontroller_backup")
    dcslave_module = univention.admin.modules.get("computers/domaincontroller_slave")

    masterobjs = univention.admin.modules.lookup(
        dcmaster_module,
        None,
        lo,
        scope="sub",
        superordinate=None,
        base=base_dn,
        filter=univention.admin.filter.expression("cn", dc_name),
    )
    backupobjs = univention.admin.modules.lookup(
        dcbackup_module,
        None,
        lo,
        scope="sub",
        superordinate=None,
        base=base_dn,
        filter=univention.admin.filter.expression("cn", dc_name),
    )
    slaveobjs = univention.admin.modules.lookup(
        dcslave_module,
        None,
        lo,
        scope="sub",
        superordinate=None,
        base=base_dn,
        filter=univention.admin.filter.expression("cn", dc_name),
    )

    # check group membership
    #  Replica Directory Node should be member
    #  Primary Directory Node and Backup Directory NOde should not be member
    dcgroups = [
        "cn=OU%s-DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (ou, base_dn),
        "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (base_dn),
    ]

    if must_exist:
        if masterobjs:
            is_master_or_backup = True
            dcobject = masterobjs[0]
        elif backupobjs:
            is_master_or_backup = True
            dcobject = backupobjs[0]
        elif slaveobjs:
            is_master_or_backup = False
            dcobject = slaveobjs[0]
        else:
            raise DCNotFound()

        dcobject.open()
        groups = []
        membership = False
        for group in dcobject.get("groups"):
            groups.append(group.lower())
        for dcgroup in dcgroups:
            if dcgroup.lower() in groups:
                membership = True

        if is_master_or_backup and membership:
            raise DCMembership()
        elif not is_master_or_backup and not membership:
            raise DCMembership()


def check_dhcp(ou_base, dc_name, singlemaster, dhcp_dns_clearou, ucr, must_exist):
    ucr.load()
    if not singlemaster:
        # in multiserver setups all dhcp settings have to be checked
        dhcp_dn = "cn=dhcp,%s" % (ou_base)
    else:
        # in singleserver setup only the first OU sets dhcpd/ldap/base and all following OUs
        # should leave the UCR variable untouched.
        dhcpd_ldap_base = ucr.get("dhcpd/ldap/base")
        if not dhcpd_ldap_base or "ou=" not in dhcpd_ldap_base:
            raise DhcpdLDAPBase('dhcpd/ldap/base=%r contains no "ou="' % (dhcpd_ldap_base,))

        # use the UCR value and check if the DHCP service exists
        dhcp_dn = dhcpd_ldap_base

    # dhcp
    print("LDAP base of dhcpd = %r" % dhcp_dn)
    dhcp_service_dn = "cn=%s,%s" % (get_school_ou_from_dn(dhcp_dn, ucr), dhcp_dn)
    dhcp_server_dn = "cn=%s,%s" % (dc_name, dhcp_service_dn)
    if must_exist:
        utils.verify_ldap_object(
            dhcp_service_dn,
            expected_attr={
                "dhcpOption": ['wpad "http://%s.%s/proxy.pac"' % (dc_name, ucr.get("domainname"))]
            },
            should_exist=True,
        )
        utils.verify_ldap_object(dhcp_server_dn, should_exist=True)

    dhcp_dns_clearou_dn = "cn=dhcp-dns-clear,cn=policies,%s" % ou_base
    if dhcp_dns_clearou:
        utils.verify_ldap_object(
            dhcp_dns_clearou_dn,
            expected_attr={"emptyAttributes": ["univentionDhcpDomainNameServers"]},
            should_exist=must_exist,
        )
        try:
            utils.verify_ldap_object(
                ou_base,
                expected_attr={"univentionPolicyReference": [dhcp_dns_clearou_dn]},
                should_exist=must_exist,
                retry_count=0,
            )
        except utils.LDAPObjectUnexpectedValue:
            # ignore other policies
            pass
    else:
        utils.verify_ldap_object(dhcp_dns_clearou_dn, should_exist=False)


def verify_dc(ou, dc_name, dc_type, base_dn=None, must_exist=True):
    """
    Arguments:
    dc_name: name of the domaincontroller (cn)
    dc_type: type of the domaincontroller ('educational' or 'administrative')
    """
    assert dc_type in (TYPE_DC_ADMINISTRATIVE, TYPE_DC_EDUCATIONAL)

    ucr = univention.testing.ucr.UCSTestConfigRegistry()
    ucr.load()
    if not base_dn:
        base_dn = ucr.get("ldap/base")
    ou_base = get_ou_base(ou, ucr.is_true("ucsschool/ldap/district/enable", False))
    dc_dn = "cn=%s,cn=dc,cn=server,cn=computers,%s" % (dc_name, ou_base)

    # define list of (un-)desired group memberships ==> [(IS_MEMBER, GROUP_DN), ...]
    group_dn_list = []
    if dc_type == TYPE_DC_ADMINISTRATIVE:
        group_dn_list += [
            (True, "cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (ou.lower(), base_dn)),
            (True, "cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (base_dn,)),
            (False, "cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % base_dn),
            (False, "cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (ou, base_dn)),
            (False, "cn=OU%s-DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (ou.lower(), base_dn)),
            (False, "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (base_dn,)),
            (False, "cn=Member-Edukativnetz,cn=ucsschool,cn=groups,%s" % base_dn),
            (False, "cn=OU%s-Member-Edukativnetz,cn=ucsschool,cn=groups,%s" % (ou, base_dn)),
        ]
    else:
        group_dn_list += [
            (True, "cn=OU%s-DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (ou.lower(), base_dn)),
            (True, "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,%s" % (base_dn,)),
            (False, "cn=Member-Edukativnetz,cn=ucsschool,cn=groups,%s" % base_dn),
            (False, "cn=OU%s-Member-Edukativnetz,cn=ucsschool,cn=groups,%s" % (ou, base_dn)),
        ]
        if ucr.is_true("ucsschool/ldap/noneducational/create/objects", must_exist):
            group_dn_list += [
                (False, "cn=OU%s-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (ou.lower(), base_dn)),
                (False, "cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (base_dn,)),
                (False, "cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % base_dn),
                (False, "cn=OU%s-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,%s" % (ou, base_dn)),
            ]

    utils.verify_ldap_object(dc_dn, should_exist=must_exist)

    for expected_membership, grpdn in group_dn_list:
        if must_exist:
            utils.verify_ldap_object(
                grpdn,
                expected_attr={"uniqueMember": [dc_dn]} if expected_membership else None,
                not_expected_attr={"uniqueMember": [dc_dn]} if not expected_membership else None,
                strict=False,
                should_exist=True,
                retry_count=0,
            )


def parametrization_id_base64_decode(val):
    if isinstance(val, string_types) and val.strip().endswith("="):
        try:
            return base64.b64decode(val.encode("ASCII")).decode("ascii", errors="replace")
        except ValueError:
            pass


def generate_import_ou_basics_test_data(use_cli_api=True, use_python_api=False):
    for dc_administrative in [None, "generate"]:
        for dc in [None, "generate"]:
            for singlemaster in [True, False]:
                for noneducational_create_object in [True, False]:
                    for district_enable in [True, False]:
                        for default_dcs in [None, "edukativ", uts.random_string()]:
                            for dhcp_dns_clearou in [True, False]:
                                for sharefileserver in [None, "generate"]:
                                    if singlemaster and dc == "generate":
                                        continue
                                    if not dc and dc_administrative:
                                        # cannot specify administrative dc without educational dc
                                        continue
                                    if not noneducational_create_object and dc_administrative:
                                        # cannot create administrative DC without administrative objects
                                        # in LDAP
                                        continue
                                    ou_name = uts.random_name()
                                    # character set contains multiple whitespaces to increase chance to
                                    # get several words
                                    charset = (
                                        uts.STR_ALPHANUMDOTDASH
                                        + uts.STR_ALPHA.upper()
                                        + '()[]/,;:_#"+*@<>~ßöäüÖÄÜ$%&!     '
                                    )
                                    ou_displayname = uts.random_string(
                                        length=random.randint(1, 50), charset=charset
                                    )
                                    yield (
                                        ou_name,
                                        base64.b64encode(ou_displayname.encode("UTF-8")).decode(
                                            "ASCII"
                                        ),  # pytest doesn't like non-ascii chars in parametrization args
                                        uts.random_name() if dc else None,
                                        uts.random_name() if dc_administrative else None,
                                        bool(sharefileserver),
                                        singlemaster,
                                        noneducational_create_object,
                                        district_enable,
                                        default_dcs,
                                        dhcp_dns_clearou,
                                        use_cli_api,
                                        use_python_api,
                                    )


def import_ou_with_existing_dc(use_cli_api=True, use_python_api=False):
    with univention.testing.ucr.UCSTestConfigRegistry() as ucr:
        with univention.testing.udm.UCSTestUDM() as udm:
            create_mail_domain(ucr, udm)
            dc_name = uts.random_name()

            dhcp_service_name = uts.random_name()

            dhcp_service = udm.create_object("dhcp/service", service=dhcp_service_name)

            dhcp_server = udm.create_object("dhcp/server", server=dc_name, superordinate=dhcp_service)

            dhcp_subnet_properties = {
                "subnet": "10.20.30.0",
                "subnetmask": "24",
            }
            dhcp_subnet1 = udm.create_object(
                "dhcp/subnet", superordinate=dhcp_service, **dhcp_subnet_properties
            )

            default_ip = Interfaces().get_default_ip_address()
            dhcp_subnet_properties = {
                "subnet": str(default_ip.network.network_address),
                "subnetmask": str(default_ip.network.prefixlen),
            }
            dhcp_subnet2 = udm.create_object(
                "dhcp/subnet", superordinate=dhcp_service, **dhcp_subnet_properties
            )

            ou_name = uts.random_name()

            # creatd dc
            try:
                create_and_verify_ou(
                    ucr,
                    ou=ou_name,
                    ou_displayname=None,
                    dc=dc_name,
                    dc_administrative=None,
                    sharefileserver=None,
                    singlemaster=False,
                    noneducational_create_objects=True,
                    district_enable=False,
                    default_dcs=None,
                    dhcp_dns_clearou=False,
                    do_cleanup=False,
                    use_cli_api=use_cli_api,
                    use_python_api=use_python_api,
                )

                utils.verify_ldap_object(dhcp_subnet1, should_exist=True)
                utils.verify_ldap_object(dhcp_subnet2, should_exist=True)

                # dhcp subnet2 should be copied
                ou_base = get_ou_base(ou=ou_name, district_enable=False)
                new_dhcp_service_dn = "cn=%(ou)s,cn=dhcp,%(ou_base)s" % {
                    "ou": ou_name,
                    "ou_base": ou_base,
                }
                new_dhcp_subnet2_dn = "cn=%s,%s" % (
                    default_ip.network.network_address,
                    new_dhcp_service_dn,
                )
                utils.verify_ldap_object(new_dhcp_subnet2_dn, should_exist=True)

                # dhcp subnet1 should not be copied
                new_dhcp_subnet1_dn = "cn=10.20.30.0,%s" % (new_dhcp_service_dn)
                utils.verify_ldap_object(new_dhcp_subnet1_dn, should_exist=False)

                # dhcp server has been moved
                utils.verify_ldap_object("cn=%s,%s" % (dc_name, new_dhcp_service_dn), should_exist=True)
                utils.verify_ldap_object(dhcp_server, should_exist=False)
            finally:
                remove_ou(ou_name)

        utils.wait_for_replication()


def import_3_ou_in_a_row(use_cli_api=True, use_python_api=False):
    """Creates 3 OUs in a row"""
    with univention.testing.ucr.UCSTestConfigRegistry() as ucr, univention.testing.udm.UCSTestUDM() as udm:  # noqa: E501
        create_mail_domain(ucr, udm)
        for singlemaster in [True, False]:
            for district_enable in [False, True]:
                cleanup_ou_list = []
                try:
                    # reset DHCPD ldap search base which is also to be tested
                    univention.config_registry.handler_unset(["dhcpd/ldap/base"])
                    ucr.load()

                    for i in range(1, 4):
                        ou_name = uts.random_name()
                        print("\n*** Creating OU #%d (ou_name=%s) ***\n" % (i, ou_name))
                        cleanup_ou_list.append(ou_name)
                        create_and_verify_ou(
                            ucr,
                            ou=ou_name,
                            ou_displayname=ou_name,
                            dc=(uts.random_name() if not singlemaster else None),
                            dc_administrative=None,
                            sharefileserver=None,
                            singlemaster=singlemaster,
                            noneducational_create_objects=False,
                            district_enable=district_enable,
                            default_dcs=None,
                            dhcp_dns_clearou=True,
                            unset_dhcpd_base=False,
                            do_cleanup=False,
                            use_cli_api=use_cli_api,
                            use_python_api=use_python_api,
                        )
                finally:
                    for ou_name in cleanup_ou_list:
                        remove_ou(ou_name)


def import_ou_alter_dhcpd_base_flag(use_cli_api=True, use_python_api=False):
    with univention.testing.ucr.UCSTestConfigRegistry() as ucr, univention.testing.udm.UCSTestUDM() as udm:  # noqa: E501
        create_mail_domain(ucr, udm)
        cleanup_ou_list = []
        try:
            univention.config_registry.handler_unset(["dhcpd/ldap/base"])
            ucr.load()
            ou_name = uts.random_name()
            print("\n*** Creating OU #1 (ou_name=%s) ***\n" % (ou_name))
            cleanup_ou_list.append(ou_name)
            try:
                create_and_verify_ou(
                    ucr,
                    ou=ou_name,
                    ou_displayname=ou_name,
                    dc=None,
                    dc_administrative=None,
                    sharefileserver=None,
                    singlemaster=True,
                    noneducational_create_objects=False,
                    district_enable=False,
                    default_dcs=None,
                    dhcp_dns_clearou=True,
                    unset_dhcpd_base=False,
                    do_cleanup=False,
                    use_cli_api=use_cli_api,
                    use_python_api=use_python_api,
                    alter_dhcpd_base_option=False,
                )
            except DhcpdLDAPBase:
                print("dhcpd/ldap/base unset as expected!")
            for i in (True, None):
                ou_name = uts.random_name()
                print("\n*** Creating OU with alter-dhcpd-base: %s (ou_name=%s) ***\n" % (i, ou_name))
                cleanup_ou_list.append(ou_name)
                create_and_verify_ou(
                    ucr,
                    ou=ou_name,
                    ou_displayname=ou_name,
                    dc=None,
                    dc_administrative=None,
                    sharefileserver=None,
                    singlemaster=True,
                    noneducational_create_objects=False,
                    district_enable=False,
                    default_dcs=None,
                    dhcp_dns_clearou=True,
                    unset_dhcpd_base=False,
                    do_cleanup=False,
                    use_cli_api=use_cli_api,
                    use_python_api=use_python_api,
                    alter_dhcpd_base_option=i,
                )
                if "ou=%s" % cleanup_ou_list[1] not in ucr.get("dhcpd/ldap/base"):
                    raise DhcpdLDAPBase(
                        "Wrong dhcpd/ldap/base value set!: %s" % ucr.get("dhcpd/ldap/base")
                    )
                lo = univention.admin.uldap.getAdminConnection()[0]
                if len(DHCPServer.get_all(lo, cleanup_ou_list[1])) != 1:
                    raise DhcpServerLocation(
                        "No DHCP Server found in ou %s, but was expected." % cleanup_ou_list[1]
                    )
            univention.config_registry.handler_unset(["dhcpd/ldap/base"])
            ucr.load()
            ou_name = uts.random_name()
            print("\n*** Creating OU with alter-dhcpd-base: None (ou_name=%s) ***\n" % (ou_name))
            cleanup_ou_list.append(ou_name)
            create_and_verify_ou(
                ucr,
                ou=ou_name,
                ou_displayname=ou_name,
                dc=None,
                dc_administrative=None,
                sharefileserver=None,
                singlemaster=True,
                noneducational_create_objects=False,
                district_enable=False,
                default_dcs=None,
                dhcp_dns_clearou=True,
                unset_dhcpd_base=False,
                do_cleanup=False,
                use_cli_api=use_cli_api,
                use_python_api=use_python_api,
                alter_dhcpd_base_option=None,
            )
            if "ou=%s" % cleanup_ou_list[-1] not in ucr.get("dhcpd/ldap/base"):
                raise DhcpdLDAPBase(
                    "Wrong dhcpd/ldap/base value set! Expected to find ou: %s; found: %s"
                    % (cleanup_ou_list[-1], ucr.get("dhcpd/ldap/base"))
                )
            if len(DHCPServer.get_all(lo, cleanup_ou_list[-1])) != 1:
                raise DhcpServerLocation(
                    "No DHCP Server found in ou %s, but was expected." % cleanup_ou_list[-1]
                )
        finally:
            for ou_name in cleanup_ou_list:
                remove_ou(ou_name)
