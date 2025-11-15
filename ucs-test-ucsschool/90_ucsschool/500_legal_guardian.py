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

import ldap
import pytest

import univention.admin.modules
import univention.admin.uldap
import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.udm import UCSTestUDM_CreateUDMObjectFailed, UCSTestUDM_ModifyUDMObjectFailed

MAX_LEGAL_GUARDIANS = 4
MAX_LEGAL_WARDS = 10

RETRY_ARGS = {
    "delay": 2,
    "retry_count": 3,
}


def workaround_58536():
    # Remove me after ucs-test 12.2.43 has been released #58536
    lo = utils.get_ldap_connection(admin_uldap=True)
    position = univention.admin.uldap.position(lo.base)
    udm_module = univention.admin.modules.get("users/user")
    if not udm_module.initialized:
        univention.admin.modules.init(lo, position, udm_module)


def test_udm_legal_guardian(udm_session):
    """
    On a UCS@school system, UDM must provide the
    ucsschoolLegalGuardian and ucsschoolLegalWard attributes.
    When the DN of a legal guardian is added to a legal wards ucsschoolLegalGuard attribute
    The legal guardian object attribute ucsschoolLegalWard must
    contain the DNs of the legal wards he is assigned to.

    univention/product-management/requirements-management#398
    univention/dev/education/ucsschool#1453
    """
    workaround_58536()

    # create guardian
    legal_guardian_dn, legal_guardian_uid = udm_session.create_user(options=["ucsschoolLegalGuardian"])

    # create ward and then attach guardian in second step
    legal_ward_dn_1, legal_ward_uid_1 = udm_session.create_user(options=["ucsschoolStudent"])
    udm_session.modify_object(
        "users/user", dn=legal_ward_dn_1, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
    )
    # verify references between objects
    udm_session.verify_udm_object(
        "users/user",
        legal_ward_dn_1,
        expected_properties={"ucsschoolLegalGuardian": [legal_guardian_dn]},
    )
    udm_session.verify_udm_object(
        "users/user", legal_guardian_dn, expected_properties={"ucsschoolLegalWard": [legal_ward_dn_1]}
    )

    # create ward and immediately attach guardian
    legal_ward_dn_2, legal_ward_uid_2 = udm_session.create_user(
        options=["ucsschoolStudent"], ucsschoolLegalGuardian=[legal_guardian_dn]
    )

    # verify references between objects
    udm_session.verify_udm_object(
        "users/user",
        legal_ward_dn_1,
        expected_properties={"ucsschoolLegalGuardian": [legal_guardian_dn]},
    )
    udm_session.verify_udm_object(
        "users/user",
        legal_ward_dn_2,
        expected_properties={"ucsschoolLegalGuardian": [legal_guardian_dn]},
    )
    udm_session.verify_udm_object(
        "users/user",
        legal_guardian_dn,
        expected_properties={"ucsschoolLegalWard": [legal_ward_dn_1, legal_ward_dn_2]},
    )


def test_deactivated_legal_wards(udm_session):
    workaround_58536()
    legal_guardian_dn, legal_guardian_uid = udm_session.create_user(
        options=["ucsschoolLegalGuardian"],
    )

    legal_wards = [
        udm_session.create_user(
            options=["ucsschoolStudent"],
            ucsschoolLegalGuardian=[legal_guardian_dn],
        )[0]
        for _ in range(3)
    ]
    udm_session.verify_udm_object(
        "users/user", legal_guardian_dn, expected_properties={"ucsschoolLegalWard": legal_wards}
    )

    legal_wards_deactivated = [
        udm_session.create_user(
            options=["ucsschoolStudent"],
            disabled="1",
            ucsschoolLegalGuardian=[legal_guardian_dn],
        )[0]
        for _ in range(3)
    ]

    udm_session.verify_udm_object(
        "users/user",
        legal_guardian_dn,
        expected_properties={"ucsschoolLegalWard": legal_wards + legal_wards_deactivated},
    )


def test_restriction_max_legal_wards(udm_session):
    """
    One legal guardian must not have more than 10 legal wards.
    1) Add one legal ward too much
    2) Create a legal guardian with too many legal wards

    univention/product-management/requirements-management#398
    univention/dev/education/ucsschool#1453
    """
    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    legal_wards = [
        udm_session.create_user(
            options=["ucsschoolStudent"],
            ucsschoolLegalGuardian=[legal_guardian_dn],
        )[0]
        for _ in range(MAX_LEGAL_WARDS)
    ]

    expected_exception_regex_modify = (
        r".*This legal guardian already has \d+ assigned students. Adding more would increase it above"
        r" the maximum allowed number of assigned students.*"
    )
    expected_exception_regex_create = (
        r".*This legal guardian would have \d+ assigned students, which is above the maximum allowed"
        r" number of assigned students.*"
    )

    # 1) Add one legal ward too much
    with pytest.raises(UCSTestUDM_ModifyUDMObjectFailed, match=expected_exception_regex_modify):
        legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])
        legal_wards.append(legal_ward_dn)
        udm_session.modify_object(
            "users/user",
            dn=legal_ward_dn,
            append={"ucsschoolLegalGuardian": [legal_guardian_dn]},
        )
    # 2) Create a legal guardian with too many legal wards
    with pytest.raises(UCSTestUDM_CreateUDMObjectFailed, match=expected_exception_regex_create):
        assert len(legal_wards) > MAX_LEGAL_WARDS
        legal_guardian_dn, _ = udm_session.create_user(
            options=["ucsschoolLegalGuardian"],
            ucsschoolLegalWard=legal_wards,
        )


def test_restriction_max_legal_guardians(udm_session):
    """
    One legal ward must not have more than 4 legal guardians.
    1) Add one legal guardian too much
    2) Create a legal ward with too many legal guardians

    univention/product-management/requirements-management#398
    univention/dev/education/ucsschool#1453
    """
    legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])
    legal_guardians = [
        udm_session.create_user(
            options=["ucsschoolLegalGuardian"],
            ucsschoolLegalWard=[legal_ward_dn],
        )[0]
        for _ in range(MAX_LEGAL_GUARDIANS)
    ]

    expected_exception_regex = (
        r".*This student would have "
        + re.escape(f"{MAX_LEGAL_GUARDIANS + 1}")
        + r" assigned legal guardians, which is above the maximum allowed"
        + r" number of assigned legal guardians.*"
    )
    # 1) Add one legal guardian too much
    with pytest.raises(UCSTestUDM_ModifyUDMObjectFailed, match=expected_exception_regex):
        legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
        legal_guardians.append(legal_guardian_dn)
        udm_session.modify_object(
            "users/user", dn=legal_ward_dn, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
        )

    # 2) Create a legal ward with too many legal guardians
    with pytest.raises(UCSTestUDM_CreateUDMObjectFailed, match=expected_exception_regex):
        assert len(legal_guardians) > MAX_LEGAL_GUARDIANS
        legal_ward_dn, _ = udm_session.create_user(
            options=["ucsschoolStudent"],
            ucsschoolLegalGuardian=legal_guardians,
        )


def test_ldap_constraints(udm_session):
    """
    Test the constraint overlay of the LDAP server for ucsschoolLegalGuardian
    and ucsschoolLegalWard.
    """
    legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])
    legal_guardian_dns = [
        udm_session.create_user(
            options=["ucsschoolLegalGuardian"],
        )[0]
        for _ in range(MAX_LEGAL_GUARDIANS + 1)
    ]

    # add legal guardian directly
    lo = utils.get_ldap_connection()
    ml = [("ucsschoolLegalGuardian", b"", [dn.encode("utf-8")]) for dn in legal_guardian_dns]
    with pytest.raises(ldap.CONSTRAINT_VIOLATION):
        lo.modify(legal_ward_dn, ml)

    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    legal_ward_dns = [
        udm_session.create_user(
            options=["ucsschoolStudent"],
        )[0]
        for _ in range(MAX_LEGAL_WARDS + 1)
    ]

    # add legal guardian directly
    ml = [("ucsschoolLegalWard", b"", [dn.encode("utf-8")]) for dn in legal_ward_dns]
    with pytest.raises(ldap.CONSTRAINT_VIOLATION):
        lo.modify(legal_guardian_dn, ml)


@pytest.mark.parametrize("useroption", ("ucsschoolLegalGuardian", "ucsschoolStudent"))
def test_create_and_remove_objects_ldap(udm_session, useroption):
    """
    Create a legal guardian and legal ward without references and verify that it can be removed.
    It is verified on the LDAP level that the user is created / removed.
    """
    user_dn, _ = udm_session.create_user(options=[useroption])
    udm_session.verify_ldap_object(
        user_dn,
        should_exist=True,
        strict=False,
        expected_attr={"objectClass": [useroption.encode()]},
        **RETRY_ARGS,
    )
    udm_session.remove_object("users/user", dn=user_dn)
    udm_session.verify_ldap_object(user_dn, should_exist=False)


def test_attach_guardian_to_a_ward_during_creation(udm_session):
    """Create a legal ward with a reference to a legal guardian."""
    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [],
        },
        **RETRY_ARGS,
    )

    # create ward and immediately attach guardian
    legal_ward_dn, legal_ward_uid = udm_session.create_user(
        options=["ucsschoolStudent"], ucsschoolLegalGuardian=[legal_guardian_dn]
    )
    # legal guardian is attached to legal ward?
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [legal_guardian_dn],
        },
        **RETRY_ARGS,
    )
    # legal ward is attached to legal guardian?
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [legal_ward_dn],
        },
        **RETRY_ARGS,
    )


def test_attach_guardian_to_a_ward_during_modification(udm_session):
    """
    Create a legal ward without a reference to a legal guardian and
    attach the legal guardian to the legal ward in a second step.
    """
    # create guardian without references
    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [],
        },
        **RETRY_ARGS,
    )

    # create ward without references
    legal_ward_dn, legal_ward_uid = udm_session.create_user(options=["ucsschoolStudent"])
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [],
        },
        **RETRY_ARGS,
    )

    udm_session.modify_object(
        "users/user", dn=legal_ward_dn, append={"ucsschoolLegalGuardian": [legal_guardian_dn]}
    )
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [legal_guardian_dn],
        },
        **RETRY_ARGS,
    )
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [legal_ward_dn],
        },
        **RETRY_ARGS,
    )


def test_attach_ward_to_a_guardian_during_creation(udm_session):
    """Create a legal guardian with a reference to a legal ward."""
    legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [],
        },
        **RETRY_ARGS,
    )

    # create legal guardian and immediately attach legal ward
    legal_guardian_dn, _ = udm_session.create_user(
        options=["ucsschoolLegalGuardian"], ucsschoolLegalWard=[legal_ward_dn]
    )
    # legal ward is attached to legal guardian?
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [legal_ward_dn],
        },
        **RETRY_ARGS,
    )
    # legal guardian is attached to legal ward?
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [legal_guardian_dn],
        },
        **RETRY_ARGS,
    )


def test_attach_ward_to_a_guardian_during_modification(udm_session):
    """
    Create a legal guardian without a reference to a legal ward and
    attach the legal ward to the legal guardian in a second step.
    """
    # create legal ward without references
    legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [],
        },
        **RETRY_ARGS,
    )

    # create guardian without references
    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [],
        },
        **RETRY_ARGS,
    )

    udm_session.modify_object(
        "users/user", dn=legal_guardian_dn, append={"ucsschoolLegalWard": [legal_ward_dn]}
    )
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [legal_guardian_dn],
        },
        **RETRY_ARGS,
    )
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [legal_ward_dn],
        },
        **RETRY_ARGS,
    )


def test_remove_ward_from_a_guardian(udm_session):
    """Remove a legal ward reference from a legal guardian object."""
    legal_ward_dn_1, _ = udm_session.create_user(options=["ucsschoolStudent"])
    legal_ward_dn_2, _ = udm_session.create_user(options=["ucsschoolStudent"])
    legal_ward_dn_3, _ = udm_session.create_user(options=["ucsschoolStudent"])

    # create legal guardian and immediately attach the legal wards
    legal_guardian_dn, _ = udm_session.create_user(
        options=["ucsschoolLegalGuardian"],
        ucsschoolLegalWard=[legal_ward_dn_1, legal_ward_dn_2, legal_ward_dn_3],
    )
    # legal wards are attached to legal guardian?
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [legal_ward_dn_1, legal_ward_dn_2, legal_ward_dn_3],
        },
        **RETRY_ARGS,
    )

    # remove legal ward #1 reference from legal guardian object
    udm_session.modify_object(
        "users/user", dn=legal_guardian_dn, remove={"ucsschoolLegalWard": [legal_ward_dn_1]}
    )
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [legal_ward_dn_2, legal_ward_dn_3],
        },
        **RETRY_ARGS,
    )


def test_remove_guardian_from_a_ward(udm_session):
    """Remove a legal guardian reference from a legal ward object."""
    legal_guardian_dn_1, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    legal_guardian_dn_2, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    legal_guardian_dn_3, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])

    # create legal ward and immediately attach the legal guardians
    legal_ward_dn, _ = udm_session.create_user(
        options=["ucsschoolStudent"],
        ucsschoolLegalGuardian=[legal_guardian_dn_1, legal_guardian_dn_2, legal_guardian_dn_3],
    )
    # legal guardians are attached to legal ward?
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [legal_guardian_dn_1, legal_guardian_dn_2, legal_guardian_dn_3],
        },
        **RETRY_ARGS,
    )

    # remove legal guardian #1 reference from legal ward object
    udm_session.modify_object(
        "users/user", dn=legal_ward_dn, remove={"ucsschoolLegalGuardian": [legal_guardian_dn_1]}
    )
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [legal_guardian_dn_2, legal_guardian_dn_3],
        },
        **RETRY_ARGS,
    )


def test_attach_nonexisting_legal_ward_to_legal_guardian(udm_session):
    """
    1) Create a legal guardian with a reference to a non-existing legal ward.
    2) Attach a non-existing legal_ward to a legal guardian.
    Both cases should not be possible.
    """
    invalid_ward_dn = "uid=NONEXISTING,cn=users,dc=does,dc=not,dc=exist"
    expected_exception_regex = r".*Could not find student.*"
    with pytest.raises(UCSTestUDM_CreateUDMObjectFailed, match=expected_exception_regex):
        legal_guardian_dn, _ = udm_session.create_user(
            options=["ucsschoolLegalGuardian"], ucsschoolLegalWard=[invalid_ward_dn]
        )

    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    with pytest.raises(UCSTestUDM_ModifyUDMObjectFailed, match=expected_exception_regex):
        udm_session.modify_object(
            "users/user", dn=legal_guardian_dn, append={"ucsschoolLegalWard": [invalid_ward_dn]}
        )


def test_attach_nonexisting_legal_guardian_to_legal_ward(udm_session):
    """
    1) Create a legal ward with a reference to a non-existing legal guardian.
    2) Attach a non-existing legal guardian to a legal ward.
    Both cases should not be possible.
    """
    invalid_guardian_dn = "uid=NONEXISTING,cn=users,dc=does,dc=not,dc=exist"
    expected_exception_regex = r".*Could not find legal guardian.*"
    with pytest.raises(UCSTestUDM_CreateUDMObjectFailed, match=expected_exception_regex):
        legal_ward_dn, _ = udm_session.create_user(
            options=["ucsschoolStudent"], ucsschoolLegalGuardian=[invalid_guardian_dn]
        )

    legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])
    with pytest.raises(UCSTestUDM_ModifyUDMObjectFailed, match=expected_exception_regex):
        udm_session.modify_object(
            "users/user", dn=legal_ward_dn, append={"ucsschoolLegalGuardian": [invalid_guardian_dn]}
        )


@pytest.mark.parametrize(
    "role", ["ucsschoolTeacher", "ucsschoolExam", "ucsschoolStaff", "ucsschoolAdministrator"]
)
def test_attach_wrong_role_to_legal_guardian(udm_session, role):
    """
    Create a legal guardian with a reference to a user that is not a legal ward (wrong role).
    This should not be possible.
    """
    invalid_ward_dn, _ = udm_session.create_user(options=[role])

    # create legal guardian and immediately attach the invalid legal ward
    expected_exception_regex_create = r".*The specified user .* is no student.*"
    with pytest.raises(UCSTestUDM_CreateUDMObjectFailed, match=expected_exception_regex_create):
        legal_guardian_dn, _ = udm_session.create_user(
            options=["ucsschoolLegalGuardian"], ucsschoolLegalWard=[invalid_ward_dn]
        )


@pytest.mark.parametrize(
    "role",
    [
        "ucsschoolStudent",
        "ucsschoolTeacher",
        "ucsschoolExam",
        "ucsschoolStaff",
        "ucsschoolAdministrator",
    ],
)
def test_attach_wrong_role_to_legal_ward(udm_session, role):
    """Create a legal ward with a reference to a user that is not a legal guardian (wrong role)."""
    invalid_guardian_dn, _ = udm_session.create_user(options=[role])

    # create legal ward and immediately attach the invalid legal guardian
    expected_exception_regex_create = r".*The specified user .* is no legal guardian.*"
    with pytest.raises(UCSTestUDM_CreateUDMObjectFailed, match=expected_exception_regex_create):
        legal_ward_dn, _ = udm_session.create_user(
            options=["ucsschoolStudent"], ucsschoolLegalGuardian=[invalid_guardian_dn]
        )


def test_refint_after_deleting_ward(udm_session):
    """
    Create a legal ward with a reference to a legal guardian.
    Delete the legal ward and check the reference at the legal guardian.
    """
    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    legal_ward_dn, _ = udm_session.create_user(
        options=["ucsschoolStudent"], ucsschoolLegalGuardian=[legal_guardian_dn]
    )
    # Hint: references between the objects above already tested by other tests

    # remove legal ward
    udm_session.remove_object("users/user", dn=legal_ward_dn)

    # check reference at remaining legal guardian object
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [],
        },
        **RETRY_ARGS,
    )


def test_refint_after_deleting_guardian(udm_session):
    """
    Create a legal ward with a reference to a legal guardian.
    Delete the legal guardian and check the reference at the legal ward.
    """
    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    legal_ward_dn, _ = udm_session.create_user(
        options=["ucsschoolStudent"], ucsschoolLegalGuardian=[legal_guardian_dn]
    )
    # Hint: references between the objects above already tested by other tests

    # remove legal ward
    udm_session.remove_object("users/user", dn=legal_guardian_dn)

    # check reference at remaining legal ward object
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [],
        },
        **RETRY_ARGS,
    )


def test_refint_after_renaming_ward(udm_session):
    """
    Create a legal ward with a reference to a legal guardian.
    Rename the legal ward and check the reference at the legal guardian.
    Hint: this should also cover the case when users are moved within the LDAP.
    """
    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    legal_ward_dn, _ = udm_session.create_user(
        options=["ucsschoolStudent"], ucsschoolLegalGuardian=[legal_guardian_dn]
    )
    # Hint: references between the objects above already tested by other tests

    # rename legal ward
    new_legal_ward_dn = udm_session.modify_object(
        "users/user", dn=legal_ward_dn, username=uts.random_username()
    )

    # check reference at remaining legal guardian object
    udm_session.verify_ldap_object(
        legal_guardian_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalWard": [new_legal_ward_dn],
        },
        **RETRY_ARGS,
    )


def test_refint_after_renaming_guardian(udm_session):
    """
    Create a legal ward with a reference to a legal guardian.
    Rename the legal guardian and check the reference at the legal ward.
    Hint: this should also cover the case when users are moved within the LDAP.
    """
    legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])
    legal_ward_dn, _ = udm_session.create_user(
        options=["ucsschoolStudent"], ucsschoolLegalGuardian=[legal_guardian_dn]
    )
    # Hint: references between the objects above already tested by other tests

    # rename legal guardian
    new_legal_guardian_dn = udm_session.modify_object(
        "users/user", dn=legal_guardian_dn, username=uts.random_username()
    )

    # check reference at remaining legal ward object
    udm_session.verify_ldap_object(
        legal_ward_dn,
        should_exist=True,
        strict=True,
        expected_attr={
            "ucsschoolLegalGuardian": [new_legal_guardian_dn],
        },
        **RETRY_ARGS,
    )


def test_replace_a_ward_at_guardian_while_at_limit(udm_session):
    """
    Create a legal guardian with the maximum allowed number of legal wards.
    Replace one reference of a legal ward with another reference.
    """
    legal_wards = [
        udm_session.create_user(
            options=["ucsschoolStudent"],
        )[0]
        for _ in range(MAX_LEGAL_WARDS)
    ]
    legal_guardian_dn, _ = udm_session.create_user(
        options=["ucsschoolLegalGuardian"], ucsschoolLegalWard=legal_wards
    )
    extra_legal_ward_dn, _ = udm_session.create_user(options=["ucsschoolStudent"])

    # remove one existing reference to a legal ward and add a new one
    udm_session.modify_object(
        "users/user",
        dn=legal_guardian_dn,
        remove={"ucsschoolLegalWard": [legal_wards[0]]},
        append={"ucsschoolLegalWard": [extra_legal_ward_dn]},
    )


def test_replace_a_guardian_at_ward_while_at_limit(udm_session):
    """
    Create a legal ward with the maximum allowed number of legal guards.
    Replace one reference of a legal guardian with another reference.
    """
    legal_guardians = [
        udm_session.create_user(
            options=["ucsschoolLegalGuardian"],
        )[0]
        for _ in range(MAX_LEGAL_GUARDIANS)
    ]
    legal_ward_dn, _ = udm_session.create_user(
        options=["ucsschoolStudent"], ucsschoolLegalGuardian=legal_guardians
    )
    extra_legal_guardian_dn, _ = udm_session.create_user(options=["ucsschoolLegalGuardian"])

    # remove one existing reference to a legal ward and add a new one
    udm_session.modify_object(
        "users/user",
        dn=legal_ward_dn,
        remove={"ucsschoolLegalGuardian": [legal_guardians[0]]},
        append={"ucsschoolLegalGuardian": [extra_legal_guardian_dn]},
    )
