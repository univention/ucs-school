#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Import OU via python API
## tags: [apptest,ucsschool,ucsschool_import4]
## roles: [domaincontroller_master]
## timeout: 14400
## exposure: dangerous
## packages:
##   - ucs-school-import

import base64
import datetime
import os
import shutil

import pytest

import univention.testing.strings as uts
import univention.testing.ucr
import univention.testing.ucsschool.importou as eio
import univention.testing.udm
import univention.testing.utils as utils


@pytest.mark.parametrize(
    "ou_name,ou_displayname,dc,dc_administrative,sharefileserver,singlemaster,"
    "noneducational_create_objects,district_enable,default_dcs,dhcp_dns_clearou,use_cli_api,"
    "use_python_api",
    eio.generate_import_ou_basics_test_data(use_cli_api=False, use_python_api=True),
    ids=eio.parametrization_id_base64_decode,
)
def test_ou_basics(
    ou_name,
    ou_displayname,
    dc,
    dc_administrative,
    sharefileserver,
    singlemaster,
    noneducational_create_objects,
    district_enable,
    default_dcs,
    dhcp_dns_clearou,
    use_cli_api,
    use_python_api,
    disable_hooks,
):
    with univention.testing.ucr.UCSTestConfigRegistry() as ucr:
        with univention.testing.udm.UCSTestUDM() as udm:
            eio.create_mail_domain(ucr, udm)
            if sharefileserver:
                sharefileserver = uts.random_name()
                udm.create_object("computers/domaincontroller_slave", name=sharefileserver)
            try:
                eio.create_and_verify_ou(
                    ucr,
                    ou=ou_name,
                    ou_displayname=base64.b64decode(ou_displayname.encode("ASCII")).decode("UTF-8"),
                    dc=dc,
                    dc_administrative=dc_administrative,
                    sharefileserver=sharefileserver,
                    singlemaster=singlemaster,
                    noneducational_create_objects=noneducational_create_objects,
                    district_enable=district_enable,
                    default_dcs=default_dcs,
                    dhcp_dns_clearou=dhcp_dns_clearou,
                    use_cli_api=use_cli_api,
                    use_python_api=use_python_api,
                )
            finally:
                eio.remove_ou(ou_name)
    utils.wait_for_replication()


def test_import_ou_with_existing_dc():
    eio.import_ou_with_existing_dc(use_cli_api=False, use_python_api=True)


def test_import_3_ou_in_a_row():
    eio.import_3_ou_in_a_row(use_cli_api=False, use_python_api=True)
