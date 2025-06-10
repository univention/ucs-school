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

IMPORT_TIMEOUT = 10  # wait 10 seconds for imports to finish


def test_cleanup_jobs(schoolenv, ucr, udm_session, copy_file):
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
    jobs_to_keep = 2
    ucr.handler_set([f"ucsschool/import/http_api/import_jobs_to_keep={jobs_to_keep}"])
    csv_file = io.StringIO(
        f'"Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"\n'
        f'"{school}","Altman","Koehler","1a","A student.","+40-680-107371",""'
    )
    csv_file_cleanup = io.StringIO(
        '"Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"\n'
    )
    copy_file(
        "/usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json",
        f"/var/lib/ucs-school-import/configs/{school}.json",
    )
    # perform a dryrun and a non-dryrun import and a non-dryrun cleanup import
    for i in range(4):
        for dryrun, csv_obj in ((True, csv_file), (False, csv_file), (False, csv_file_cleanup)):
            job = client.userimportjob.create(
                "some_file.csv",
                source_uid="UCSTEST_IMPORT",
                school=school,
                user_role="student",
                dryrun=dryrun,
                file_obj=csv_obj,
            )
            job_id = job.id
            for attempt in range(IMPORT_TIMEOUT):
                job = client.userimportjob.get(job_id)
                if job.status == "Finished":
                    break
                sleep(1.0)
            else:
                raise Exception(f"The dryrun={dryrun} import did not complete in time or failed.")

    # check if the dryrun filter for import/users/ is working properly
    all_jobs = client.call_api("get", "imports/users/")
    dryrun_jobs = client.call_api("get", "imports/users/", params={"dryrun": True})
    non_dryrun_jobs = client.call_api("get", "imports/users/", params={"dryrun": False})
    assert all_jobs["count"] == jobs_to_keep * 2
    assert dryrun_jobs["count"] == jobs_to_keep
    assert non_dryrun_jobs["count"] == jobs_to_keep
