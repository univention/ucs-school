#!/usr/share/ucs-test/runner pytest-3 -l -s -v
## desc: Test the leagl guardian feature
## bugs: []
## roles:
## - domaincontroller_master
## - domaincontroller_backup
## - domaincontroller_slave
## packages: [ucs-school-import]
## tags: [apptest,ucsschool,ucsschool_base1,ucs-school-import]
## exposure: dangerous

import re

import pytest

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.udm import UCSTestUDM_ModifyUDMObjectFailed

MAX_LEGAL_GUARDIANS = 4
MAX_LEGAL_WARDS = 10


def test_udm_legal_guardian(udm_session):
    """
    On a UCS@school system, UDM must provide the
    ucschoolLegalGuardian and ucsschoolLegalWard attributes.
    When the DN of a legal guardian is added to a legal wards ucsschoolLegalWard attribute
    The legal guardian object attribute ucsschoolLegalWard must
    contain the DNs of the legal wards he is assigned to.

    univention/product-management/requirements-management#398
    univention/dev/education/ucsschool#1453
    """
    legal_guardian_uid = uts.random_username()
    legal_guardian_dn, _ = udm_session.create_user(
        username=legal_guardian_uid, options=["ucsschoolLegalGuardian"]
    )

    legal_ward_uid_1 = uts.random_username()
    legal_ward_dn_1, _ = udm_session.create_user(username=legal_ward_uid_1, options=["ucsschoolStudent"])
    udm_session.modify_object(
        "users/user", dn=legal_ward_dn_1, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
    )

    legal_ward_uid_2 = uts.random_username()
    legal_ward_dn_2, _ = udm_session.create_user(username=legal_ward_uid_2, options=["ucsschoolStudent"])
    udm_session.modify_object(
        "users/user", dn=legal_ward_dn_2, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
    )

    objs = udm_session.list_objects("users/user", filter=f"uid={legal_ward_uid_1}")
    assert len(objs) == 1
    legal_ward = objs[0][1]
    assert legal_ward["ucsschoolLegalGuardian"] == [legal_guardian_dn]

    objs = udm_session.list_objects("users/user", filter=f"uid={legal_ward_uid_2}")
    assert len(objs) == 1
    legal_ward = objs[0][1]
    assert legal_ward["ucsschoolLegalGuardian"] == [legal_guardian_dn]

    objs = udm_session.list_objects("users/user", filter=f"uid={legal_guardian_uid}")
    assert len(objs) == 1
    legal_guardian = objs[0][1]
    assert legal_guardian["ucsschoolLegalWard"] == [legal_ward_dn_1, legal_ward_dn_2]


def test_deactivated_legal_wards(udm_session):
    """In UCS a student should still show up as a legal ward even if deactivated."""
    legal_guardian_uid = uts.random_username()
    legal_guardian_dn, _ = udm_session.create_user(
        username=legal_guardian_uid, options=["ucsschoolLegalGuardian"]
    )

    legal_wards = [udm_session.create_user(options=["ucsschoolStudent"])[0] for _ in range(3)]
    for legal_ward_dn in legal_wards:
        udm_session.modify_object(
            "users/user", dn=legal_ward_dn, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
        )

    legal_wards_deactivated = [
        udm_session.create_user(options=["ucsschoolStudent"])[0] for _ in range(3)
    ]
    for legal_ward_dn in legal_wards_deactivated:
        udm_session.modify_object(
            "users/user",
            dn=legal_ward_dn,
            disabled="1",
            append={"ucsschoolLegalGuardian": [legal_guardian_dn]},
        )

    objs = udm_session.list_objects("users/user", filter=f"uid={legal_guardian_uid}")
    assert len(objs) == 1
    legal_guardian = objs[0][1]
    assert len(legal_guardian["ucsschoolLegalWard"]) == 6
    assert legal_guardian["ucsschoolLegalWard"] == legal_wards + legal_wards_deactivated


def test_restriction_max_legal_wards(udm_session):
    """
    One legal guardian must not have more than 10 legal wards.

    univention/product-management/requirements-management#398
    univention/dev/education/ucsschool#1453
    """
    legal_guardian_dn, _ = udm_session.create_user(
        options=["ucsschoolLegalGuardian"],
    )
    for _ in range(MAX_LEGAL_WARDS):
        legal_ward_dn, _ = udm_session.create_user(
            options=["ucsschoolStudent"],
        )
        udm_session.modify_object(
            "users/user",
            wait_for_replication=False,
            dn=legal_ward_dn,
            append={"ucsschoolLegalGuardian": [legal_guardian_dn]},
        )

    expected_exception_regex = (
        r".*"
        + re.escape(
            f"Legal guardian {legal_guardian_dn} already has {MAX_LEGAL_WARDS} legal wards. Adding"
        )
        + r".*"
    )
    with pytest.raises(UCSTestUDM_ModifyUDMObjectFailed, match=expected_exception_regex):
        legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])
        udm_session.modify_object(
            "users/user", dn=legal_ward_dn, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
        )


def test_restriction_max_legal_guardians(udm_session):
    """
    One legal ward must not have more than 4 legal guardians.

    univention/product-management/requirements-management#398
    univention/dev/education/ucsschool#1453
    """
    legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])
    for _ in range(MAX_LEGAL_GUARDIANS):
        legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
        udm_session.modify_object(
            "users/user", dn=legal_ward_dn, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
        )

    expected_exception_regex = (
        r".*"
        + re.escape(
            f"Legal ward {legal_ward_dn} has {MAX_LEGAL_GUARDIANS+1} legal guardians, which is above"
        )
        + r".*"
    )
    with pytest.raises(UCSTestUDM_ModifyUDMObjectFailed, match=expected_exception_regex):
        legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
        udm_session.modify_object(
            "users/user", dn=legal_ward_dn, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
        )


def test_removal_of_legal_guardians(udm_session):
    """
    Legal guardians should always be able to be removed from a ward, even if they somehow were
    above the maximum.

    univention/product-management/requirements-management#398
    univention/dev/education/ucsschool#1453
    """
    legal_ward_uid = uts.random_username()
    legal_ward_dn, _ = udm_session.create_user(username=legal_ward_uid, options=["ucsschoolStudent"])

    legal_guardian_dns = []

    for _ in range(MAX_LEGAL_GUARDIANS + 2):
        legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
        legal_guardian_dns.append(legal_guardian_dn)

    # add legal guardian directly
    lo = utils.get_ldap_connection()
    ml = [("ucsschoolLegalGuardian", b"", [dn.encode("utf-8")]) for dn in legal_guardian_dns]
    lo.modify(legal_ward_dn, ml)

    objs = udm_session.list_objects("users/user", filter=f"uid={legal_ward_uid}")
    assert len(objs) == 1
    legal_guardian = objs[0][1]
    assert set(legal_guardian["ucsschoolLegalGuardian"]) == set(legal_guardian_dns)

    # Remove all legal guardians, one by one
    for dn in legal_guardian_dns:
        udm_session.modify_object(
            "users/user", dn=legal_ward_dn, remove={"ucsschoolLegalGuardian": [dn]}
        )

    objs = udm_session.list_objects("users/user", filter=f"uid={legal_ward_uid}")
    assert len(objs) == 1
    legal_ward = objs[0][1]
    assert "ucsschoolLegalGuardian" not in legal_ward


def test_refint_overlay(udm_session):
    """
    The legal guardians attribute on a student should be updated
    if a legal guadian is deleted or renamed.
    """
    legal_guardian_uid = uts.random_username()
    legal_guardian_dn, _ = udm_session.create_user(
        username=legal_guardian_uid, options=["ucsschoolLegalGuardian"]
    )

    legal_ward_uid = uts.random_username()
    legal_ward_dn, _ = udm_session.create_user(username=legal_ward_uid, options=["ucsschoolStudent"])
    udm_session.modify_object(
        "users/user", dn=legal_ward_dn, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
    )
    objs = udm_session.list_objects("users/user", filter=f"uid={legal_ward_uid}")
    assert len(objs) == 1
    legal_ward = objs[0][1]
    assert legal_ward["ucsschoolLegalGuardian"] == [legal_guardian_dn]

    # rename legal guardian
    legal_guardian_uid = uts.random_username()
    udm_session.modify_object("users/user", dn=legal_guardian_dn, set={"username": legal_guardian_uid})
    objs = udm_session.list_objects("users/user", filter=f"uid={legal_guardian_uid}")
    assert len(objs) == 1
    legal_guardian_dn = objs[0][0]
    objs = udm_session.list_objects("users/user", filter=f"uid={legal_ward_uid}")
    assert len(objs) == 1
    legal_ward = objs[0][1]
    assert legal_ward["ucsschoolLegalGuardian"] == [legal_guardian_dn]

    # delete legal guardian
    udm_session.remove_object(
        "users/user",
        dn=legal_guardian_dn,
    )
    objs = udm_session.list_objects("users/user", filter=f"uid={legal_ward_uid}")
    assert len(objs) == 1
    legal_ward = objs[0][1]
    assert "ucsschoolLegalGuardian" not in legal_ward
