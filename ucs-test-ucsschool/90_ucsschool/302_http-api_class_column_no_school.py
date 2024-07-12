#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Check that school names in classes column are not used
## tags: [apptest,ucsschool,ucsschool_import1,skip_in_upgrade_singleserver]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import-http-api
##   - ucs-school-import-http-api-client
## bugs: [47156]

# skipped in upgrade singleserver scenario, see Issue #1234

import logging
import random
import subprocess
import tempfile
import time
from csv import QUOTE_ALL, DictReader, DictWriter, excel

from ldap.filter import filter_format

import univention.testing.strings as uts
from ucsschool.http_api.client import Client
from ucsschool.importer.utils.test_user_creator import TestUserCreator
from ucsschool.importer.writer.test_user_csv_exporter import HttpApiTestUserCsvExporter
from ucsschool.lib.models.group import SchoolClass
from univention.testing.ucsschool.importusers_http import HttpApiImportTester


class Test(HttpApiImportTester):
    ou_C = None

    def get_school_classes_for_user(self, filter_s):
        users = self.lo.search(filter_s)
        if len(users) != 1:
            self.fail("Could not find user from filter {!r}. Got: {!r}".format(filter_s, users))
        school_classes = SchoolClass.get_all(
            self.lo,
            self.ou_A.name,
            filter_format("memberUid=%s", (users[0][1]["uid"][0].decode("UTF-8"),)),
        )
        self.log.debug(
            "Got school classes for user %r: %r", users[0][1]["uid"][0].decode("UTF-8"), school_classes
        )
        return school_classes

    def test(self):
        roles = list(self.all_roles)
        roles.remove("staff")
        self.log.info("------ Creating import user... ------")
        password = uts.random_name() + "§$!*"  # see bug #48137
        username, user_dn = self.schoolenv.create_teacher(self.ou_A.name, password=password)

        # Issue #1031
        self.log.info("------ Creating identifiable OU for error logging ------")
        ou_name_302, ou_dn_302 = self.schoolenv.create_ou(
            ou_name="302_http_api_no_school",
            name_edudc=self.schoolenv.ucr["hostname"],
            use_cache=False,
        )

        self.log.info("------ Creating import security groups... ------")
        self.create_import_security_group(
            ou_dn=self.ou_A.dn, allowed_ou_names=[self.ou_A.name], roles=roles, user_dns=[user_dn]
        )
        self.create_import_security_group(
            ou_dn=ou_dn_302, allowed_ou_names=[ou_name_302], roles=roles, user_dns=[user_dn]
        )

        self.log.info("------ Restarting service ucs-school-import-http-api... ------")
        subprocess.call(["/bin/systemctl", "restart", "ucs-school-import-http-api"])
        time.sleep(4)

        self.log.info("------ Connecting to HTTP-API... ------")
        if str is bytes:  # py 2
            username = username.decode("UTF-8")
            password = password.decode("UTF-8")
        client = Client(username, password, log_level=logging.DEBUG)

        self.log.info("------ Creating user information... ------")
        test_user_creator = TestUserCreator(
            [self.ou_A.name], students=3, teachers=3, staffteachers=2, classes=2, schools=1, email=False
        )
        test_user_creator.make_classes()
        csv_dialect = excel()
        csv_dialect.doublequote = True
        csv_dialect.quoting = QUOTE_ALL

        self.log.info('------ 1/3 no "$OU-" in the class column ------')

        with tempfile.NamedTemporaryFile() as tmpfile1:
            self.log.info("------ Writing user information to CSV file... ------")
            test_user_exporter = HttpApiTestUserCsvExporter()
            test_user_exporter.dump(test_user_creator.make_users(), tmpfile1.name)
            self.log.info(
                "------ CSV file content:\n{}------ End ------".format(open(tmpfile1.name).read())
            )
            self.log.info("------ Starting import through HTTP-API Python client... ------")
            role = random.choice(roles)
            import_job = self.run_http_import_through_python_client(
                client, tmpfile1.name, self.ou_A.name, role, False, config=self.default_config
            )
            self.log.debug("import_job=%r", import_job)
            if import_job.status == "Finished":
                self.log.info(
                    '*** OK: import succeeded without "$OU-" in the class column, class names should '
                    "start "
                    'with "$OU-"...'
                )
            else:
                self.fail(
                    "Import failed: status={!r} result={!r}".format(
                        import_job.status, import_job.result.result
                    ),
                    import_job=import_job,
                )

            with open(tmpfile1.name) as fp_in:
                reader = DictReader(fp_in)
                for row in reader:
                    school_classes_in_ldap = self.get_school_classes_for_user(
                        filter_format("(&(givenName=%s)(sn=%s))", (row["Vorname"], row["Nachname"]))
                    )
                    school_class_names_in_csv = [
                        "{}-{}".format(self.ou_A.name, klasse) for klasse in row["Klassen"].split(",")
                    ]
                    for sc in school_classes_in_ldap:
                        if sc.school != self.ou_A.name or sc.name not in school_class_names_in_csv:
                            self.fail(
                                "Unexpected school class name: school={!r} and name={!r}, expected {!r} "
                                "and one of {!r}.".format(
                                    sc.school, sc.name, self.ou_A.name, school_class_names_in_csv
                                ),
                                import_job=import_job,
                            )
            self.log.info("*** OK: all school class names are as expected.")

        self.log.info("------ 2/3 with allowed OU (%r) in the class column ------", self.ou_A.name)

        with tempfile.NamedTemporaryFile() as tmpfile1, tempfile.NamedTemporaryFile() as tmpfile2:
            self.log.info("------ Writing user information to CSV file %r... ------", tmpfile1.name)
            test_user_exporter.dump(test_user_creator.make_users(), tmpfile1.name)
            self.log.info("------ Manipulating CSV data... ------")
            with open(tmpfile1.name) as fp_in, open(tmpfile2.name, "w") as fp_out:
                reader = DictReader(fp_in)
                writer = None  # need the field names, will get them with the first line below
                for row in reader:
                    row["Klassen"] = ",".join(
                        ["{}-{}".format(self.ou_A.name, kl) for kl in row["Klassen"].split(",")]
                    )
                    if not writer:
                        writer = DictWriter(fp_out, fieldnames=list(row.keys()), dialect=csv_dialect)
                        writer.writeheader()
                    writer.writerow(row)
            self.log.info(
                "------ CSV file content:\n{}------ End ------".format(open(tmpfile2.name).read())
            )
            self.log.info("------ Starting import through HTTP-API Python client... ------")
            role = random.choice(roles)
            import_job = self.run_http_import_through_python_client(
                client, tmpfile2.name, self.ou_A.name, role, False, config=self.default_config
            )
            self.log.debug("import_job=%r", import_job)
            if import_job.status == "Finished":
                self.log.info(
                    '*** OK: import succeded with allowed "$OU-" in the class column, class names should'
                    ' start with "$OU-$OU-"...'
                )
            else:
                self.fail(
                    "Import failed: status={!r} result={!r}".format(
                        import_job.status, import_job.result.result
                    ),
                    import_job=import_job,
                )

            with open(tmpfile1.name) as fp_in:
                reader = DictReader(fp_in)
                for row in reader:
                    school_classes_in_ldap = self.get_school_classes_for_user(
                        filter_format("(&(givenName=%s)(sn=%s))", (row["Vorname"], row["Nachname"]))
                    )
                    school_class_names_in_csv = [
                        "{0}-{0}-{1}".format(self.ou_A.name, klasse)
                        for klasse in row["Klassen"].split(",")
                    ]
                    for sc in school_classes_in_ldap:
                        if sc.school != self.ou_A.name or sc.name not in school_class_names_in_csv:
                            self.fail(
                                "Unexpected school class name: school={!r} and name={!r}, expected {!r} "
                                "and one of {!r}.".format(
                                    sc.school, sc.name, self.ou_A.name, school_class_names_in_csv
                                ),
                                import_job=import_job,
                            )
            self.log.info("*** OK: all school class names are as expected.")

        self.log.info("------ 3/3 with disallowed OU (%r) in the class column ------", ou_name_302)

        self.log.info("------ Creating user information... ------")
        test_user_creator = TestUserCreator(
            [self.ou_A.name], students=3, teachers=3, staffteachers=2, classes=2, schools=1, email=False
        )
        test_user_creator.make_classes()

        with tempfile.NamedTemporaryFile() as tmpfile1, tempfile.NamedTemporaryFile() as tmpfile2:
            self.log.info("------ Writing user information to CSV file %r... ------", tmpfile1.name)
            test_user_exporter.dump(test_user_creator.make_users(), tmpfile1.name)
            self.log.info("------ Manipulating CSV data... ------")
            with open(tmpfile1.name) as fp_in, open(tmpfile2.name, "w") as fp_out:
                reader = DictReader(fp_in)
                writer = None  # need the field names, will get them with the first line below
                for row in reader:
                    row["Klassen"] = ",".join(
                        ["{}-{}".format(self.ou_A.name, kl) for kl in row["Klassen"].split(",")]
                    )
                    if not writer:
                        writer = DictWriter(fp_out, fieldnames=list(row.keys()), dialect=csv_dialect)
                        writer.writeheader()
                    writer.writerow(row)
            self.log.info(
                "------ CSV file content:\n{}------ End ------".format(open(tmpfile2.name).read())
            )
            self.log.info("------ Starting import through HTTP-API Python client... ------")
            role = random.choice(roles)
            import_job = self.run_http_import_through_python_client(
                client, tmpfile2.name, ou_name_302, role, False, config=self.default_config
            )
            self.log.debug("import_job=%r", import_job)
            if import_job.status == "Aborted":
                self.log.info(
                    "OK: import failed: status=%r result=%r", import_job.status, import_job.result.result
                )
            else:
                self.fail(
                    "Import succeeded: status={!r} result={!r}".format(
                        import_job.status, import_job.result.result
                    ),
                    import_job=import_job,
                )


if __name__ == "__main__":
    Test().run()
