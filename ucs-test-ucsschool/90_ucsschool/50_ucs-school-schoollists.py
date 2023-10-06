#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: Test umc calls to generate school class lists
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-groups]

import magic
import requests

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.umc import Client
from univention.udm import UDM


def test_ucs_school_schoollists(ucr, schoolenv):
    host = ucr.get("hostname")
    school_name, oudn = schoolenv.create_ou(name_edudc=host)
    class_name, class_dn = schoolenv.create_school_class(school_name)
    stu_firstname = uts.random_string() + "\U0001F680"
    stu_lastname = uts.random_string() + "\U0001F680"
    uts.random_name_special_characters()
    stu, studn = schoolenv.create_user(
        school_name, classes=class_name, firstname=stu_firstname, lastname=stu_lastname, is_active=False
    )

    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw

    connection = Client(host, language="en_US")
    connection.authenticate(admin, passwd)
    for separator, exclude in [
        (separator, exclude) for separator in [",", "\t"] for exclude in [True, False]
    ]:
        options = {
            "school": school_name,
            "group": class_dn,
            "separator": separator,
            "exclude_deactivated": exclude,
        }
        umc_response = connection.umc_command("schoollists/csvlist", options).result
        file_url: str = umc_response["url"]
        filename = umc_response["filename"]
        expected_class_list = (
            u"Firstname{sep}Lastname{sep}Class{sep}Username\r\n{first}{sep2}{last}{sep2}"
            u"{cls_name}{sep2}{uid}{linebreak}".format(
                sep=separator,
                sep2="" if exclude else separator,
                first="" if exclude else stu_firstname,
                last="" if exclude else stu_lastname,
                cls_name="" if exclude else class_name.replace(school_name + "-", "", 1),
                uid="" if exclude else stu,
                linebreak="" if exclude else "\r\n",
            )
        )

        # check that file is not accessible while not authenticated
        response = requests.get("https://{host}/{file_url}".format(host=host, file_url=file_url))
        assert response.status_code == 401

        # use the umc clients cookies and GET the file with requests
        response = requests.get(
            "https://{host}/{file_url}".format(host=host, file_url=file_url), cookies=connection.cookies
        )
        try:
            received_class_list = response.content.decode("utf-8")
            assert received_class_list == expected_class_list
        except UnicodeDecodeError:
            received_class_list = response.content.decode("utf-16le")

            # slicing the received class list to remove leading BOM character
            assert str(received_class_list[1:]) == str(expected_class_list)

        print("Expected: {}".format(expected_class_list))
        print("Received: {}".format(received_class_list))

        assert file_url.endswith(filename)


def test_ucs_school_schoollists_student_without_class(ucr, schoolenv):
    host = ucr.get("hostname")
    school_name, oudn = schoolenv.create_ou(name_edudc=host)
    class_name, class_dn = schoolenv.create_school_class(school_name)

    stu_firstname = uts.random_name() + "\U0001F680"
    stu_lastname = uts.random_name() + "\U0001F680"
    stu, studn = schoolenv.create_user(
        school_name, classes=class_name, firstname=stu_firstname, lastname=stu_lastname
    )
    workg_name, workg_dn = schoolenv.create_workgroup(school_name, users=[studn])

    if ucr.get("server/role") in {"domaincontroller_master", "domaincontroller_backup"}:
        udm = UDM.admin().version(2)
    else:
        udm = UDM.machine().version(2)

    class_mod = udm.get("groups/group")
    class_obj = class_mod.get(class_dn)
    class_obj.props.users = []
    class_obj.save()

    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw

    connection = Client(host, language="en_US")
    connection.authenticate(admin, passwd)
    for separator in [",", "\t"]:
        options = {
            "school": school_name,
            "group": workg_dn,
            "separator": separator,
            "exclude_deactivated": False,
        }
        umc_response = connection.umc_command("schoollists/csvlist", options).result
        file_url = umc_response["url"]
        filename = umc_response["filename"]
        expected_class_list = u"Firstname{sep}Lastname{sep}Class{sep}Username\r\n".format(sep=separator)

        # check that file is not accessible while not authenticated
        response = requests.get("https://{host}/{file_url}".format(host=host, file_url=file_url))
        assert response.status_code == 401

        # use the umc clients cookies and GET the file with requests
        response = requests.get(
            "https://{host}/{file_url}".format(host=host, file_url=file_url), cookies=connection.cookies
        )

        try:
            received_class_list = response.content.decode("utf-8")
            assert received_class_list == expected_class_list
        except UnicodeDecodeError:
            received_class_list = response.content.decode("utf-16le")

            # slicing the received class list to remove leading BOM character
            assert str(received_class_list[1:]) == str(expected_class_list)

        print("Expected: {}".format(expected_class_list))
        print("Received: {}".format(received_class_list))

        assert file_url.endswith(filename)


def test_ucs_school_schoollists_correct_encoding(ucr, schoolenv):
    host = ucr.get("hostname")
    school_name, oudn = schoolenv.create_ou(name_edudc=host)
    class_name, class_dn = schoolenv.create_school_class(school_name)

    stu_firstname = uts.random_name() + "\U0001F680"
    stu_lastname = uts.random_name() + "\U0001F680"
    stu, studn = schoolenv.create_user(
        school_name, classes=class_name, firstname=stu_firstname, lastname=stu_lastname
    )
    workg_name, workg_dn = schoolenv.create_workgroup(school_name, users=[studn])

    if ucr.get("server/role") in {"domaincontroller_master", "domaincontroller_backup"}:
        udm = UDM.admin().version(2)
    else:
        udm = UDM.machine().version(2)

    class_mod = udm.get("groups/group")
    class_obj = class_mod.get(class_dn)
    class_obj.props.users = []
    class_obj.save()

    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw

    connection = Client(host, language="en_US")
    connection.authenticate(admin, passwd)
    for separator in [",", "\t"]:
        options = {
            "school": school_name,
            "group": workg_dn,
            "separator": separator,
            "exclude_deactivated": False,
        }
        umc_response = connection.umc_command("schoollists/csvlist", options).result
        file_url = umc_response["url"]

        # check that file is not accessible while not authenticated
        response = requests.get("https://{host}/{file_url}".format(host=host, file_url=file_url))
        assert response.status_code == 401

        # use the umc clients cookies and GET the file with requests
        response = requests.get(
            "https://{host}/{file_url}".format(host=host, file_url=file_url), cookies=connection.cookies
        )
        received_class_list = response.content

        # check encoding (magic uses the system language utf-8 will be converted to us-ascii)
        encoding = "utf-16le" if separator == "\t" else "us-ascii"
        assert encoding == magic.Magic(mime_encoding=True).from_buffer(received_class_list)
