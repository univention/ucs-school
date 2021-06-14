#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: Test wireless gpo replication
## roles: [domaincontroller_slave]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: []

from subprocess import PIPE, Popen

import univention.testing.utils as utils
from univention.testing.ucs_samba import wait_for_s4connector


def test_samba4_wireless_gpp_replication(schoolenv):
        values_set = [
            schoolenv.ucr.is_true("connector/s4/mapping/msgpwl", False),
        ]
        assert all(values_set)
        gpo_name = "{00000001-6CF5-4327-8EB1-0635DD98A83E}"
        schoolenv.udm.create_object(
            "container/msgpo",
            position="cn=Policies,cn=System,{}".format(schoolenv.ucr.get("ldap/base")),
            name=gpo_name,
            msGPOFlags="2",
            msGPOFileSysPath=r"\\{0}\SysVol\{0}\Policies\{1}".format(
                schoolenv.ucr.get("domainname"), gpo_name
            ),
            msGPOVersionNumber="2",
            msNTSecurityDescriptor=(
                "O:DAG:DAD:P(A;CI;RPWPCCDCLCLORCWOWDSDDTSW;;;DA)(A;CI;RPWPCCDCLCLORCWOWDSDDTSW;;;EA)"
                "(A;CIIO;RPWPCCDCLCLORCWOWDSDDTSW;;;CO)(A;;RPWPCCDCLCLORCWOWDSDDTSW;;;DA)"
                "(A;CI;RPWPCCDCLCLORCWOWDSDDTSW;;;SY)(A;CI;RPLCLORC;;;AU)"
                "(OA;CI;CR;edacfd8f-ffb3-11d1-b41d-00a0c968f939;;AU)(A;CI;RPLCLORC;;;ED)"
                "S:AI(OU;CIIOIDSA;WP;"
                "f30e3bbe-9ff0-11d1-b603-0000f80367c1;bf967aa5-0de6-11d0-a285-00aa003049e2;WD)"
                "(OU;CIIOIDSA;WP;"
                "f30e3bbf-9ff0-11d1-b603-0000f80367c1;bf967aa5-0de6-11d0-a285-00aa003049e2;WD)"
            ),
            wait_for_replication=True,
        )
        wait_for_s4connector()
        cmd = (
            "samba-tool",
            "gpo",
            "listall",
            "--username=" + utils.UCSTestDomainAdminCredentials().username,
            "--password=" + utils.UCSTestDomainAdminCredentials().bindpw,
        )
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate(proc)
        assert gpo_name in stdout.decode("UTF-8")
