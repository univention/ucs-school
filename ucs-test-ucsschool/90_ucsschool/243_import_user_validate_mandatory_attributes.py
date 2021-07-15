#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Test validation of "mandatory_attributes" property
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [47691]

import random

import pytest

import univention.testing.strings as uts
import univention.testing.utils as utils
from ucsschool.importer.exceptions import EmptyMandatoryAttribute, MissingMandatoryAttribute
from ucsschool.importer.utils.shell import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
    config,
    logger,
)


def test_import_user_validate_mandatory_attributes(ucr, schoolenv):
    if not isinstance(config, dict) or not isinstance(config["verbose"], bool):
        utils.fail("Import configuration has not been not setup.")
    additional_attr = random.choice(
        ("description", "organisation", "employeeType", "roomNumber", "city")
    )
    config["mandatory_attributes"].append(additional_attr)
    ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr["hostname"])
    lo = schoolenv.open_ldap_connection(admin=True)
    for kls in [ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff]:
        logger.info("*** Positive test (additional_attr %r is set) -> no fail expected", additional_attr)
        user = kls(
            name=uts.random_username(),
            school=ou_name,
            firstname=uts.random_name(),
            lastname=uts.random_name(),
            record_uid=uts.random_name(),
        )
        user.udm_properties[additional_attr] = uts.random_name()
        user.prepare_all(True)
        logger.info("Going to create: %r attr: %r", user, user.to_dict())
        user.create(lo)
        logger.info("OK: user was created.")

        logger.info(
            "*** Additional_attr %r does not exist -> MissingMandatoryAttribute expected",
            additional_attr,
        )
        user = kls(
            name=uts.random_username(),
            school=ou_name,
            firstname=uts.random_name(),
            lastname=uts.random_name(),
            record_uid=uts.random_name(),
        )
        user.prepare_all(True)
        logger.info("Going to create: %r attr: %r", user, user.to_dict())
        with pytest.raises(MissingMandatoryAttribute) as exc:
            user.create(lo)
            user = kls.from_dn(user.dn, user.school, lo)
            print(
                "MissingMandatoryAttribute was not raised (but {!r} was not created).\nCreated "
                "user: {!r} attr: {!r}".format(additional_attr, user, user.to_dict())
            )
        logger.info("OK: MissingMandatoryAttribute was raised: %r", exc.value)

        logger.info('*** "firstname" is empty -> EmptyMandatoryAttribute expected')
        config["mandatory_attributes"].remove(additional_attr)
        user = kls(
            name=uts.random_username(),
            school=ou_name,
            firstname=uts.random_name(),
            lastname=uts.random_name(),
            record_uid=uts.random_name(),
        )
        user.prepare_all(True)
        user.firstname = ""
        logger.info("Going to create: %r attr: %r", user, user.to_dict())
        with pytest.raises(EmptyMandatoryAttribute) as exc:
            user.create(lo)
            user = kls.from_dn(user.dn, user.school, lo)
            print(
                "EmptyMandatoryAttribute was not raised (but firstname was empty).\nCreated "
                "user: {!r} attr: {!r}".format(user, user.to_dict())
            )
        logger.info("OK: EmptyMandatoryAttribute was raised: %r", exc.value)

        config["mandatory_attributes"].append(additional_attr)
        for empty in (None, ""):
            logger.info(
                "*** Additional_attr %r is empty (%r) -> EmptyMandatoryAttribute expected",
                additional_attr,
                empty,
            )
            user = kls(
                name=uts.random_username(),
                school=ou_name,
                firstname=uts.random_name(),
                lastname=uts.random_name(),
                record_uid=uts.random_name(),
            )
            user.udm_properties[additional_attr] = empty
            user.prepare_all(True)
            logger.info("Going to create: %r attr: %r", user, user.to_dict())
            with pytest.raises(EmptyMandatoryAttribute) as exc:
                user.create(lo)
                user = kls.from_dn(user.dn, user.school, lo)
                print(
                    "EmptyMandatoryAttribute was not raised (but firstname was empty).\n"
                    "Created user: {!r} attr: {!r}".format(user, user.to_dict())
                )
            logger.info("OK: EmptyMandatoryAttribute was raised: %r", exc.value)
    logger.info("Test was successful.\n\n\n")
