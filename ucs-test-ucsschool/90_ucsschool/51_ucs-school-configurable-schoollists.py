#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Test umc calls to generate school class lists with altered attributes.
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-groups]

from __future__ import print_function

import pytest
import requests

import univention.config_registry
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.user import Student
from univention.lib.umc import HTTPError
from univention.testing import utils
from univention.testing.umc import Client

UCRV_NAME = "ucsschool/umc/lists/class/attributes"
# Number of attributes tested per generated csv list.
CHUNK_SIZE = 5
# Attributes whose value legitimately differs between primary and replica and can
# therefore not be compared: the expected list is built from the primary's data,
# while the received list is generated on the replica, which gets its own
# modifiersName from the replication process.
EXCLUDED_PROPERTIES = frozenset({"modifiersName"})


def properties_with_values(udm_user, klass_name):
    """
    Collect all udm properties which are set, plus the pseudo-attribute 'Class'.

    Returns a deterministically ordered list of
    ``(udm_property, column_name, expected_value)`` tuples.
    """
    columns = []
    for key in sorted(udm_user.keys()):
        if key in EXCLUDED_PROPERTIES:
            continue
        value = udm_user.get(key)
        if not value:
            continue
        if isinstance(value, list):
            value = " ".join(value)
        columns.append((key, key.upper(), value))
    columns.append(("Class", "CLASS", klass_name))
    return columns


def chunked(items, size):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def request_class_list(host, school_name, class_dn, columns):
    """Configure the given attributes and download the generated csv class list."""
    ucr_value = ",".join("{} {}".format(prop, column) for prop, column, _ in columns)
    print("## Set {}={}".format(UCRV_NAME, ucr_value))
    univention.config_registry.handler_set(["{}={}".format(UCRV_NAME, ucr_value)])

    account = utils.UCSTestDomainAdminCredentials()
    connection = Client(host, language="en_US")
    connection.authenticate(account.username, account.bindpw)
    options = {
        "school": school_name,
        "group": class_dn,
        "separator": ",",
        "exclude_deactivated": False,
    }
    umc_response = connection.umc_command("schoollists/csvlist", options).result
    file_url = umc_response["url"]

    # The download must not be possible without authentication.
    response = requests.get("https://{host}/{file_url}".format(host=host, file_url=file_url))
    assert response.status_code == 401

    response = requests.get(
        "https://{host}/{file_url}".format(host=host, file_url=file_url),
        cookies=connection.cookies,
    )
    return response.content.decode("latin-1")


@pytest.fixture(scope="module")
def school_data():
    with utu.UCSTestSchool() as schoolenv, ucr_test.UCSTestConfigRegistry() as ucr:
        host = ucr.get("hostname")
        school_name, _ = schoolenv.create_ou(name_edudc=host)
        class_name, class_dn = schoolenv.create_school_class(school_name)
        _, student_dn = schoolenv.create_user(school_name, classes=class_name)
        klass_name = class_name.split("-", 1)[1]
        udm_user = Student.from_dn(student_dn, school_name, schoolenv.lo).get_udm_object(schoolenv.lo)
        yield {
            "host": host,
            "school_name": school_name,
            "class_dn": class_dn,
            "columns": properties_with_values(udm_user, klass_name),
        }


def test_ucs_school_configurable_schoollists(school_data):
    """Generate csv class lists for all configurable attributes (in chunks)."""
    for chunk in chunked(school_data["columns"], CHUNK_SIZE):
        received_class_list = request_class_list(
            school_data["host"],
            school_data["school_name"],
            school_data["class_dn"],
            chunk,
        )
        expected_class_list = "{fieldnames_string}\r\n{expected_values}\r\n".format(
            fieldnames_string=",".join(column for _, column, _ in chunk),
            expected_values=",".join(value for _, _, value in chunk),
        )
        print("Expected: {}".format(expected_class_list))
        print("Received: {}".format(received_class_list))
        # Multi-values are returned in "", replacing them was the easiest way.
        received_class_list = received_class_list.replace('"', "")
        assert received_class_list == expected_class_list


def test_ucs_school_configurable_schoollists_invalid_attribute(school_data):
    """A non-existent udm attribute must make the umc request fail."""
    columns = list(school_data["columns"][:CHUNK_SIZE])
    prop, _, value = columns[0]
    invalid_property = "{}-false".format(prop)
    # Mess up one udm-property to get an error.
    columns[0] = (invalid_property, invalid_property.upper(), value)
    with pytest.raises(HTTPError) as exc_info:
        request_class_list(
            school_data["host"],
            school_data["school_name"],
            school_data["class_dn"],
            columns,
        )
    assert invalid_property in exc_info.value.message
