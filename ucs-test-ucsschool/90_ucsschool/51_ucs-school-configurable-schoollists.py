#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: Test umc calls to generate school class lists with altered attributes.
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-groups]

from __future__ import print_function

import random

import univention.config_registry
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models.user import Student
from univention.lib.umc import HTTPError
from univention.testing.umc import Client


def random_properties(udm_user, klass_name, n=5):
    """
    Choose n random properties, which are already set.
    Always add pseudo-attribute 'Class'

    """
    udm_properties = []
    expected_values = []
    while len(udm_properties) < n:
        key = random.choice(list(udm_user.keys()))
        value = udm_user.get(key)
        if value:
            udm_properties.append(key)
            if isinstance(value, list):
                value = " ".join(udm_user.get(key))
            expected_values.append(value)
    udm_properties.append("Class")
    expected_values.append(klass_name)
    column_names = [_value.upper() for _value in udm_properties]
    return expected_values, udm_properties, column_names


def test_ucs_school_configurable_schoollists():
    """Test umc calls to generate school class lists with altered attributes"""
    with utu.UCSTestSchool() as schoolenv, ucr_test.UCSTestConfigRegistry() as ucr:
        host = ucr.get("hostname")
        ucrv_name = "ucsschool/umc/lists/class/attributes"
        school_name, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
        class_name, class_dn = schoolenv.create_school_class(school_name)
        student, student_dn = schoolenv.create_user(school_name, classes=class_name)
        klass_name = class_name.split("-", 1)[1]
        udm_user = Student.from_dn(student_dn, school_name, schoolenv.lo).get_udm_object(schoolenv.lo)
        cases = [random_properties(udm_user, klass_name) for _ in range(5)]
        # Mess up one udm-property to get an error.
        _udm_properties = cases[-1][1]
        _udm_properties[0] = "{}-false".format(_udm_properties[0])
        expected_error = _udm_properties[0]

        for expected_values, udm_properties, column_names in cases:
            ucr_value = ",".join([" ".join(pair) for pair in zip(udm_properties, column_names)])
            print("## Set {}={}".format(ucrv_name, ucr_value))
            univention.config_registry.handler_set(["{}={}".format(ucrv_name, ucr_value)])
            schoolenv.ucr.load()

            account = utils.UCSTestDomainAdminCredentials()
            connection = Client(host, language="en_US")
            connection.authenticate(account.username, account.bindpw)
            expected_class_list = {
                u"csv": u"{fieldnames_string}\r\n{expected_values}\r\n".format(
                    fieldnames_string=",".join(column_names), expected_values=",".join(expected_values)
                ),
                u"filename": u"{}.csv".format(class_name),
            }
            options = {"school": school_name, "group": class_dn, "separator": ","}
            try:
                class_list = connection.umc_command("schoollists/csvlist", options).result
            except HTTPError as exc:
                assert expected_error in exc.message
                print("The failed UMC request failed was expected.")
                continue
            print("Expected: {}".format(expected_class_list))
            print("Received: {}".format(class_list))
            # Multi-values are returned in "", replacing them was the easiest way.
            class_list["csv"] = class_list["csv"].replace('"', "")
            assert class_list == expected_class_list
