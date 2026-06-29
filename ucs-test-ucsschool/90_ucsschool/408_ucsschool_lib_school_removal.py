#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: deleting a school relocates multi-school users and frees their primary group
## roles: [domaincontroller_master]
## tags: [apptest, ucsschool, ucsschool_import1, ucs-school-lib]
## exposure: dangerous
## packages:
##   - python3-ucsschool-lib

#
# Bug #59576: School.remove() must detach/relocate the school's users *before* the
# OU (and with it the "Domain Users <school>" primary group) is removed. Otherwise:
#   * a multi-school user homed in the deleted OU is cascade-deleted together with
#     the OU, losing its membership in all its other schools (data loss), and
#   * the "Domain Users <school>" group is deleted while users still reference it as
#     their primaryGroupID, which the S4 connector cannot replicate to Samba 4
#     ("Refusing to delete ... still the primaryGroupID for N users").
#
# The Samba refusal itself cannot be reproduced here (no S4 connector in this
# environment), but the relocation and the primary-group reset are observable in
# OpenLDAP and guard against the regression.
#

from __future__ import annotations

from typing import TYPE_CHECKING

from ldap.filter import filter_format

from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import Student
from univention.testing import utils
from univention.testing.ucsschool.conftest import UserType

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from univention.admin.uldap import access as LoType


def _domain_users_dn(ou: str, ldap_base: str) -> str:
    return "cn=Domain Users {0},cn=groups,ou={0},{1}".format(ou, ldap_base)


def test_delete_school_relocates_multi_school_user(
    create_ou: Callable[..., tuple[str, str]],
    lo: LoType,
    user_school_attributes: Callable[..., dict[str, Any]],
    ucr_ldap_base: str,
) -> None:
    ou_a, ou_a_dn = create_ou(use_cache=False)
    ou_b, ou_b_dn = create_ou(use_cache=False)

    # multi-school student homed in ou_a (its LDAP object lives below ou_a)
    multi_attrs = user_school_attributes([ou_a, ou_b], UserType.Student)
    multi = Student(**multi_attrs)
    assert multi.create(lo)
    assert multi.school == ou_a
    assert ou_a_dn.lower() in multi.dn.lower()

    # single-school student homed in ou_a (control: must be deleted with the OU)
    single = Student(**user_school_attributes([ou_a], UserType.Student))
    assert single.create(lo)
    single_dn = single.dn

    du_a_dn = _domain_users_dn(ou_a, ucr_ldap_base)
    du_b_dn = _domain_users_dn(ou_b, ucr_ldap_base)
    utils.verify_ldap_object(du_a_dn, should_exist=True)

    # the multi-school user must initially use "Domain Users <ou_a>" as primary group
    du_a_gid = lo.get(du_a_dn, attr=["gidNumber"])["gidNumber"][0]
    assert lo.get(multi.dn, attr=["gidNumber"])["gidNumber"][0] == du_a_gid

    # delete school ou_a via the library (the production code path)
    school = School.from_dn(ou_a_dn, None, lo)
    assert school.remove(lo)

    # the OU and its primary group are gone ...
    utils.verify_ldap_object(ou_a_dn, should_exist=False)
    utils.verify_ldap_object(du_a_dn, should_exist=False)
    # ... and so is the single-school user, which only belonged to ou_a
    utils.verify_ldap_object(single_dn, should_exist=False)

    # the multi-school user survives, relocated below ou_b
    found = lo.searchDn(filter_format("(&(uid=%s)(ucsschoolSchool=%s))", (multi.name, ou_b)))
    assert len(found) == 1, "multi-school user was not relocated to %r" % (ou_b,)
    relocated_dn = found[0]
    assert ou_b_dn.lower() in relocated_dn.lower()
    assert ou_a_dn.lower() not in relocated_dn.lower()

    relocated = Student.from_dn(relocated_dn, ou_b, lo)
    assert relocated.school == ou_b
    assert relocated.schools == [ou_b]

    # its primary group has been reset to "Domain Users <ou_b>"
    du_b_gid = lo.get(du_b_dn, attr=["gidNumber"])["gidNumber"][0]
    assert lo.get(relocated_dn, attr=["gidNumber"])["gidNumber"][0] == du_b_gid
