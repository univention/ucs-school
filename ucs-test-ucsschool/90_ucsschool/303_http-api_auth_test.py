#!/usr/share/ucs-test/runner python
# coding=utf-8
## desc: Check if auth via HTTP-API works with non-ASCII passwords (gunicorns log is checked)
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-import-http-api]

from ldap.filter import filter_format

import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.http_api.client import Client, ObjectNotFound, PermissionError, ServerError
from univention.testing.ucs_samba import wait_for_drs_replication


def count_unicode_exceptions_in_gunicorn_log():
    with open("/var/log/univention/ucs-school-import/gunicorn_error.log", "r") as fd:
        content = fd.read()
    return content.count("UnicodeEncodeError: 'ascii' codec can't encode characters in position")


def main():
    with utu.UCSTestSchool() as schoolenv:
        with ucr_test.UCSTestConfigRegistry() as ucr:
            password = '!"§$%&/()=*'

            school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
            school_admin, school_admin_dn = schoolenv.create_school_admin(school, password=password)
            wait_for_drs_replication(filter_format("cn=%s", (school_admin,)))

            old_exception_count = count_unicode_exceptions_in_gunicorn_log()

            try:
                Client(
                    name=school_admin.decode("utf-8"),
                    password=password.decode("utf-8"),
                    server="{}.{}".format(ucr["hostname"], ucr["domainname"]),
                    log_level=Client.LOG_RESPONSE,
                    ssl_verify=True,
                )
            except ObjectNotFound:
                raise Exception(
                    "The UCS@school import API HTTP server could not be reached. It seems it is "
                    "misconfigured, not installed or a proxy/firewall is blocking it."
                )
            except ServerError as exc:
                raise Exception("The UCS@school Import API HTTP server is not reachable: %s" % (exc,))
            except PermissionError as exc:
                print("*** Authentication failed... checking if gunicorn failed with traceback...")
                new_exception_count = count_unicode_exceptions_in_gunicorn_log()
                print("*** old_exception_count: {}".format(old_exception_count))
                print("*** new_exception_count: {}".format(new_exception_count))
                if new_exception_count > old_exception_count:
                    utils.fail(
                        "Authentication against HTTP-API failed with unicode exception in gunicorn. See "
                        "bug #48137."
                    )
                else:
                    print(
                        "*** Authentication failed for unknown reason! Test does not fail because "
                        "school_admin was not explicitly allowed to use import."
                    )
                    print("*** Nevertheless bug #48137 does not seem to happen.")
                    raise


if __name__ == "__main__":
    main()
