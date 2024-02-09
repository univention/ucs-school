#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Test umc calls to generate school class lists
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-groups]

import magic
import pytest
import requests

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.testing import utils
from univention.testing.umc import Client
from univention.udm import UDM


def get_random_special_name():
    return uts.random_string() + "\U0001F680"


@pytest.fixture(scope="module")
def env_test(ucr):
    with utu.UCSTestSchool() as schoolenv:
        host = ucr.get("hostname")
        school_name, oudn = schoolenv.create_ou(name_edudc=host)
        class_name, class_dn = schoolenv.create_school_class(school_name)
        stu = {"firstname": get_random_special_name(), "lastname": get_random_special_name()}
        stu["uid"], stu["dn"] = schoolenv.create_user(
            school_name,
            classes=class_name,
            firstname=stu["firstname"],
            lastname=stu["lastname"],
            is_active=True,
        )
        stu_inactive = {"firstname": get_random_special_name(), "lastname": get_random_special_name()}
        stu_inactive["uid"], stu_inactive["dn"] = schoolenv.create_user(
            school_name,
            classes=class_name,
            firstname=stu_inactive["firstname"],
            lastname=stu_inactive["lastname"],
            is_active=False,
        )

        # Student with no class should never appear
        stu_no_class = {"firstname": get_random_special_name(), "lastname": get_random_special_name()}
        stu_no_class["uid"], stu_no_class["dn"] = schoolenv.create_user(
            school_name,
            classes=class_name,
            firstname=stu_no_class["firstname"],
            lastname=stu_no_class["lastname"],
            is_active=True,
        )

        workg_name, workg_dn = schoolenv.create_workgroup(
            school_name, users=[stu["dn"], stu_inactive["dn"], stu_no_class["dn"]]
        )

        if ucr.get("server/role") in {"domaincontroller_master", "domaincontroller_backup"}:
            udm = UDM.admin().version(2)
        else:
            udm = UDM.machine().version(2)

        class_mod = udm.get("groups/group")
        class_obj = class_mod.get(class_dn)
        class_obj.props.users.remove(stu_no_class["dn"])
        class_obj.save()
        env_test = {
            "school_name": school_name,
            "stu": stu,
            "stu_inactive": stu_inactive,
            "stu_no_class": stu_no_class,
            "school_class": {"dn": class_dn, "name": class_name},
            "workgroup": {"dn": workg_dn, "name": workg_name},
        }
        yield env_test


@pytest.mark.parametrize("language", ["en_US", "de_DE"])
@pytest.mark.parametrize("separator", [",", "\t"])
@pytest.mark.parametrize("exclude", [False, True])
@pytest.mark.parametrize("group_type", ["school_class", "workgroup"])
def test_ucs_school_schoollists(ucr, env_test, language, separator, exclude, group_type):
    stu = env_test["stu"]
    stu_inactive = env_test["stu_inactive"]
    env_test["stu_no_class"]
    school_class = env_test["school_class"]
    workgroup = env_test["workgroup"]
    school_name = env_test["school_name"]

    host = ucr.get("hostname")
    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw
    connection = Client(host, language=language)
    connection.authenticate(admin, passwd)

    options = {
        "school": school_name,
        "group": school_class["dn"] if group_type == "school_class" else workgroup["dn"],
        "separator": separator,
        "exclude_deactivated": exclude,
    }
    umc_response = connection.umc_command("schoollists/csvlist", options).result
    file_url: str = umc_response["url"]
    filename = umc_response["filename"]
    expected_class_list_lines = ["Firstname{sep}Lastname{sep}Class{sep}Username".format(sep=separator)]
    expected_users = [stu]
    if not exclude:
        expected_users.append(stu_inactive)
    for expected_user in expected_users:
        expected_class_list_lines.append(
            "{first}{sep}{last}{sep}{grp_name}{sep}{uid}".format(
                sep=separator,
                first=expected_user["firstname"],
                last=expected_user["lastname"],
                grp_name=school_class["name"].replace(school_name + "-", "", 1),
                uid=expected_user["uid"],
            )
        )

    # check that file is not accessible while not authenticated
    response = requests.get("https://{host}/{file_url}".format(host=host, file_url=file_url))
    assert response.status_code == 401

    # use the umc clients cookies and GET the file with requests
    response = requests.get(
        "https://{host}/{file_url}".format(host=host, file_url=file_url), cookies=connection.cookies
    )
    received_class_list = response.text
    # Check windows line breaks
    assert received_class_list.count("\r\n") == len(expected_class_list_lines)

    # Check expected lines
    assert len(received_class_list.splitlines()) == len(expected_class_list_lines)

    # Check Header
    assert received_class_list.startswith(expected_class_list_lines[0] + "\r\n")

    # List is not sorted
    for line in expected_class_list_lines:
        assert line in received_class_list.splitlines()

    class_specifier, timestamp = filename.split("_", 1)[0], filename.split("_", 1)[1][:-4]
    assert f"classlist={class_specifier}" in file_url
    assert timestamp in file_url

    # retrieve classname from dn
    classname = options["group"].split(",", 1)[0].split("-", 1)[1]
    # build filename without timestamp
    expected_filename = f"{options['school']}-{classname}"

    assert filename.startswith(
        expected_filename
    ), f"Received malformatted filename {filename}. Expected: {expected_filename}"

    # Bug #57018 - correct mimetype in response headers
    expected_mimetype = f'text/csv; charset="{"utf-8" if separator == "," else "utf-16"}"'
    assert expected_mimetype == response.headers["Content-Type"], (
        f'Expected {expected_mimetype} as "Content-Type" header of response.'
        f'Got: {response.headers["Content-Type"]}'
    )

    encoding = "utf-16le" if separator == "\t" else "utf-8"
    detected_encoding = magic.Magic(mime_encoding=True).from_buffer(response.content)
    assert encoding == detected_encoding
