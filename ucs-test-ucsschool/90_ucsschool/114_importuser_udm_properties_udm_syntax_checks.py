#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test if UDM syntax checks are applied to ImportUser.udm_properties
## tags: [apptest,ucsschool,ucsschool_base1]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [42513]

import univention.testing.strings as uts
import univention.testing.ucr
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.importer.exceptions import NotSupportedError, UDMValueError
from ucsschool.importer.utils.shell import (
    ImportStaff,
    ImportStudent,
    ImportTeacher,
    ImportTeachersAndStaff,
    config,
    logger,
)
from univention.testing import utils
from univention.testing.ucsschool.importusers import get_mail_domain


def main():
    if not isinstance(config, dict) or not isinstance(config["verbose"], bool):
        utils.fail("Import configuration has not been not setup.")
    with univention.testing.ucr.UCSTestConfigRegistry() as ucr:

        def random_value(prop):
            if prop == "mailPrimaryAddress":
                return "{}@{}".format(uts.random_name(), get_mail_domain())
            else:
                return uts.random_name()

        with utu.UCSTestSchool() as schoolenv:
            ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
            lo = schoolenv.open_ldap_connection(admin=True)
            for kls in [ImportStaff, ImportStudent, ImportTeacher, ImportTeachersAndStaff]:
                #
                # check if UDM syntax checks are applied
                #
                # 1. len(udm_properties['organisation']) > 64 and create()
                #
                user = kls(
                    name=uts.random_username(),
                    school=ou_name,
                    firstname=uts.random_name(),
                    lastname=uts.random_name(),
                    record_uid=uts.random_name(),
                    source_uid="TestDB",
                )
                user.udm_properties["organisation"] = uts.random_name(65)
                user.prepare_all(True)
                try:
                    user.create(lo)
                    utils.fail(
                        "UDMValueError should have been raised in create() (tried to store 65 chars in "
                        "string64)."
                    )
                except UDMValueError as exc:
                    logger.info("*** OK: Caught expected UDMValueError exception: %s", exc)

                # 2. len(udm_properties['organisation']) > 64 and modify()
                user = kls(
                    name=uts.random_username(),
                    school=ou_name,
                    firstname=uts.random_name(),
                    lastname=uts.random_name(),
                    record_uid=uts.random_name(),
                    source_uid="TestDB",
                )
                user.prepare_all(True)
                user.create(lo)
                utils.verify_ldap_object(
                    user.dn, expected_attr={"uid": [user.name]}, strict=False, should_exist=True
                )
                user.udm_properties["organisation"] = uts.random_name(65)
                try:
                    user.modify(lo)
                    utils.fail(
                        "UDMValueError should have been raised in modify() (tried to store 65 chars in "
                        "string64)."
                    )
                except UDMValueError as exc:
                    logger.info("*** OK: Caught expected UDMValueError exception: %s", exc)

                #
                # check if attributes mapped by the ucsschool.lib are prevented
                # from being read from udm_properties
                #
                # 1. create()
                #
                mapped_props = [
                    "birthday",
                    "disabled",
                    "firstname",
                    "lastname",
                    "mailPrimaryAddress",
                    "password",
                    "school",
                    "ucsschoolRecordUID",
                    "ucsschoolSourceUID",
                    "username",
                ]  # ImportUser._attributes
                for prop in mapped_props:
                    user = kls(
                        name=uts.random_username(),
                        school=ou_name,
                        firstname=uts.random_name(),
                        lastname=uts.random_name(),
                        record_uid=uts.random_name(),
                        source_uid="TestDB",
                        password=uts.random_string(config["password_length"]),
                    )
                    user.udm_properties[prop] = random_value(prop)
                    try:
                        user.create(lo)
                        utils.fail(
                            'NotSupportedError should have been raised in create() when storing "{}" '
                            "from udm_properties.".format(prop)
                        )
                    except NotSupportedError as exc:
                        logger.info("*** OK: Caught expected NotSupportedError exception: %s", exc)

                    # 2. modify()
                    user = kls(
                        name=uts.random_username(),
                        school=ou_name,
                        firstname=uts.random_name(),
                        lastname=uts.random_name(),
                        record_uid=uts.random_name(),
                        source_uid="TestDB",
                        password=uts.random_string(config["password_length"]),
                    )
                    user.create(lo)
                    utils.verify_ldap_object(
                        user.dn, expected_attr={"uid": [user.name]}, strict=False, should_exist=True
                    )
                    user.udm_properties[prop] = random_value(prop)
                    try:
                        user.modify(lo)
                        utils.fail(
                            'NotSupportedError should have been raised in modify() when storing "{}" '
                            "from udm_properties.".format(prop)
                        )
                    except NotSupportedError as exc:
                        logger.info("*** OK: Caught expected NotSupportedError exception: %s", exc)
            logger.info("Test was successful.\n\n\n")


if __name__ == "__main__":
    main()
