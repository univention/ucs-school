#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: Test umc calls to generate school class lists
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-groups]

import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.testing.umc import Client

from univention.udm import UDM

def test_ucs_school_schoollists(ucr, schoolenv):
    host = ucr.get("hostname")
    school_name, oudn = schoolenv.create_ou(name_edudc=host)
    class_name, class_dn = schoolenv.create_school_class(school_name)
    stu_firstname = uts.random_string()
    stu_lastname = uts.random_string()
    stu, studn = schoolenv.create_user(
        school_name, classes=class_name, firstname=stu_firstname, lastname=stu_lastname
    )

    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw

    connection = Client(host, language="en_US")
    connection.authenticate(admin, passwd)
    for separator in [",", "\t"]:
        options = {"school": school_name, "group": class_dn, "separator": separator}
        class_list = connection.umc_command("schoollists/csvlist", options).result
        expected_class_list = {
            u"csv": u"Firstname{sep}Lastname{sep}Class{sep}Username\r\n{first}{sep}{last}{sep}"
            u"{cls_name}{sep}{uid}\r\n".format(
                sep=separator,
                first=stu_firstname,
                last=stu_lastname,
                cls_name=class_name.replace(school_name + "-", "", 1),
                uid=stu,
            ),
            u"filename": u"{}.csv".format(class_name),
        }
        print("Expected: {}".format(expected_class_list))
        print("Received: {}".format(class_list))
        assert class_list == expected_class_list


def test_ucs_school_schoollists_student_without_class(ucr, schoolenv):
    host = ucr.get("hostname")
    school_name, oudn = schoolenv.create_ou(name_edudc=host)
    class_name, class_dn = schoolenv.create_school_class(school_name)
    stu_firstname = uts.random_string()
    stu_lastname = uts.random_string()
    stu, studn = schoolenv.create_user(
        school_name, classes=class_name, firstname=stu_firstname, lastname=stu_lastname
    )
    workg_name, workg_dn = schoolenv.create_workgroup(school_name, users=[studn])

    class_mod = UDM.admin().version(2).get('groups/group')
    class_obj = class_mod.get(class_dn)
    class_obj.props.users = []
    class_obj.save()

    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw

    connection = Client(host, language="en_US")
    connection.authenticate(admin, passwd)
    for separator in [",", "\t"]:
        options = {"school": school_name, "group": workg_dn, "separator": separator}
        class_list = connection.umc_command("schoollists/csvlist", options).result
        expected_class_list = {
            u"csv": u"Firstname{sep}Lastname{sep}Class{sep}Username\r\n".format(sep=separator),
            u"filename": u"{}.csv".format(workg_name),
        }
        print("Expected: {}".format(expected_class_list))
        print("Received: {}".format(class_list))
        assert class_list == expected_class_list