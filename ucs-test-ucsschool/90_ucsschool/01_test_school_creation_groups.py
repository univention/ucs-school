#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test if groups are created correct
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python-ucs-school

import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models import Container, Group
from ucsschool.lib.roles import role_staff, role_student, role_teacher
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.utils import verify_ldap_object


def test_import_group():
    with utu.UCSTestSchool() as schoolenv:
        ou_name, ou_dn = schoolenv.create_ou()
        ou_import_group_dn = "cn={}-import-all,cn=groups,{}".format(ou_name, ou_dn)
        expected_attr = {
            "cn": ["{}-import-all".format(ou_name)],
            "ucsschoolImportSchool": [ou_name],
            "ucsschoolImportRole": [role_student, role_staff, role_teacher, "teacher_and_staff"],
        }
        verify_ldap_object(ou_import_group_dn, expected_attr=expected_attr, strict=False)
        policy_dn = "cn=schoolimport-all,cn=UMC,cn=policies,{}".format(schoolenv.ucr["ldap/base"])
        expected = {"univentionPolicyReference": [policy_dn]}
        verify_ldap_object(ou_import_group_dn, expected_attr=expected, strict=False)


def test_create_exam_group():
    with utu.UCSTestSchool() as schoolenv:
        ucr = schoolenv.ucr
        ldap_base = ucr["ldap/base"]
        ou_name, ou_dn = schoolenv.create_ou()
        exam_users = ucr.get("ucsschool/ldap/default/container/exam", "examusers")
        district = schoolenv.get_district(ou_name) or ""
        exam_container = Container(name=exam_users, school=ou_name)
        exam_container.position = "ou={}{},{}".format(ou_name, district, ldap_base)
        exam_container.name = exam_users
        assert exam_container.exists(schoolenv.lo)
        search_base = SchoolSearchBase([ou_dn], school=ou_name)
        exam_group_name = search_base.examGroupName
        group = Group(exam_group_name, ou_name)
        group.position = "cn=ucsschool,cn=groups,{}".format(ldap_base)
        group.name = exam_group_name
        assert group.exists(schoolenv.lo)
