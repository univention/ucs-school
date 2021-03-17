#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test if exam and import groups are created correctly
## roles: []
## tags: [apptest, ucsschool]
## exposure: dangerous
## packages:
##   - python-ucs-school

import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.models.group import Group
from ucsschool.lib.models.misc import Container
from ucsschool.lib.roles import role_staff, role_student, role_teacher
from ucsschool.lib.schoolldap import SchoolSearchBase
from univention.testing.utils import verify_ldap_object
from ucsschool.lib.models.utils import ucr
import pytest
from univention.config_registry import handler_set, handler_unset


@pytest.mark.parametrize("ucr_value", ["yes", "no", "unset"])
def test_import_import_group(ucr_value):
    with utu.UCSTestSchool() as schoolenv:
        if ucr_value == "unset":
            handler_unset(["ucsschool/import/generate/import/group"])
        else:
            handler_set(["ucsschool/import/generate/import/group={}".format(ucr_value)])
        ucr.load()
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr["hostname"], use_cache=False)
        ou_import_group_dn = "cn={}-import-all,cn=groups,{}".format(ou_name, ou_dn)
        if ucr_value in ("no", "unset"):
            verify_ldap_object(ou_import_group_dn, should_exist=False)
        else:
            policy_dn = "cn=schoolimport-all,cn=UMC,cn=policies,{}".format(schoolenv.ucr["ldap/base"])
            expected_attr = {
                "cn": ["{}-import-all".format(ou_name)],
                "ucsschoolImportSchool": [ou_name],
                "ucsschoolImportRole": [role_student, role_staff, role_teacher, "teacher_and_staff"],
                "univentionPolicyReference": [policy_dn],
            }
            verify_ldap_object(ou_import_group_dn, expected_attr=expected_attr, strict=False)


def test_create_exam_group():
    with utu.UCSTestSchool() as schoolenv:
        ucr = schoolenv.ucr
        ldap_base = ucr["ldap/base"]
        ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr["hostname"], use_cache=False)
        exam_users = ucr.get("ucsschool/ldap/default/container/exam", "examusers")
        exam_container = Container(name=exam_users, school=ou_name)
        exam_container.name = exam_users
        assert exam_container.exists(schoolenv.lo)
        search_base = SchoolSearchBase([ou_dn], school=ou_name)
        exam_group_name = search_base.examGroupName
        group = Group(exam_group_name, ou_name)
        group.position = "cn=ucsschool,cn=groups,{}".format(ldap_base)
        group.name = exam_group_name
        assert group.exists(schoolenv.lo)
