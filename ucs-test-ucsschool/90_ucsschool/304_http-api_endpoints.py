#!/usr/share/ucs-test/runner pytest-3 -s -l -v
# -*- coding: utf-8 -*-
## desc: Checks if the HTTP-API endpoints work as expected.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool_base1,ucs-school-import]
## exposure: dangerous
## packages: [ucs-school-import-http-api]


import io
from time import sleep

from ldap.filter import filter_format

from ucsschool.http_api.client import Client
from ucsschool.lib.models import SchoolAdmin
from univention.testing.ucs_samba import wait_for_drs_replication
from univention.testing.utils import wait_for_s4_connector_to_be_inactive


def test_download_passwords(schoolenv, ucr, udm_session, copy_file):
    password = "univention"
    school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
    school_admin, school_admin_dn = schoolenv.create_school_admin(school, password=password)
    school_admin_udm_obj = SchoolAdmin.get_first_udm_obj(schoolenv.lo, f"uid={school_admin}")
    assert school_admin_udm_obj is not None
    school_admin_udm_obj.info["groups"].append(f"cn={school}-import-all,cn=groups,{oudn}")
    school_admin_udm_obj.modify(schoolenv.lo)
    wait_for_drs_replication(filter_format("cn=%s", (school_admin,)))
    wait_for_s4_connector_to_be_inactive()
    client = Client(
        name=school_admin,
        password=password,
        server="{}.{}".format(ucr["hostname"], ucr["domainname"]),
        log_level=Client.LOG_RESPONSE,
        ssl_verify=True,
    )
    csv_file = io.StringIO(
        f'"Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"\n'
        f'"{school}","Altman","Koehler","1a","A student.","+40-680-107371",""'
    )
    copy_file(
        "/usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json",
        f"/var/lib/ucs-school-import/configs/{school}.json",
    )
    job = client.userimportjob.create(
        "some_file.csv",
        source_uid="TEST_IMPORT",
        school=school,
        user_role="student",
        dryrun=True,
        file_obj=csv_file,
    )
    job_id = job.id
    tries = 0
    while True:
        if tries > 9:
            raise Exception("The import did not complete in time or failed.")
        job = client.userimportjob.get(job_id)
        if job.status == "Finished":
            break
        tries += 1
        sleep(1.0)
    passwords = client.call_api("get", f"imports/users/{job_id}/passwords")
    summary = client.call_api("get", f"imports/users/{job_id}/summary")
    assert "altman.koehl" in passwords["text"]
    assert "altman.koehl" in summary["text"]
