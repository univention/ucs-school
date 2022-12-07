#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## -*- coding: utf-8 -*-
## desc: test operations on user resource
## tags: [ucs_school_kelvin]
## exposure: dangerous
## packages: []
## bugs: []

from __future__ import unicode_literals

import logging
import random
import time
from multiprocessing import Pool

import pytest
import requests

from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.user import Staff as LibStaff, User as LibUser
from univention.testing.ucsschool.kelvin_api import (
    RESOURCE_URLS,
    api_call,
    create_remote_static,
    partial_update_remote_static,
)
from univention.testing.utils import wait_for_listener_replication, wait_for_s4connector_replication

try:
    from urlparse import urljoin  # py2
except ImportError:
    from urllib.parse import urljoin  # py3

logger = logging.getLogger("univention.testing.ucsschool")


def get_class_dn(class_name, school, lo):
    # copied from models.user as static version
    school_class = SchoolClass.cache(class_name, school)
    if school_class.get_relative_name() == school_class.name:
        if not school_class.exists(lo):
            class_name = "%s-%s" % (school, class_name)
            school_class = SchoolClass.cache(class_name, school)
    return school_class.dn


@pytest.fixture
def extract_class_dns(lo):
    def _func(attrs):
        school_class_objs = []
        for school, school_classes in attrs.get("school_classes", {}).items():
            school_class_objs.extend(SchoolClass.cache(sc, school) for sc in school_classes)
        return [get_class_dn(sc.name, sc.school, lo) for sc in school_class_objs]

    return _func


def assert_equal_dicts(dict1, dict2):
    assert set(dict1.keys()) == set(dict2.keys())
    for k, v in dict1.items():
        if isinstance(v, list):
            assert set(v) == set(dict2[k])
        else:
            assert v == dict2[k]


def test_list_resource_from_external(auth_header, lo):
    response = requests.get(RESOURCE_URLS["users"], headers=auth_header, params={"school": "DEMOSCHOOL"})
    res = response.json()
    assert isinstance(res, list), repr(res)
    assert isinstance(res[0], dict), repr(res)
    assert "name" in res[0], repr(res)
    assert "firstname" in res[0], repr(res)
    all_usernames_in_response = [user["name"] for user in res]
    for lib_user in LibUser.get_all(lo, "DEMOSCHOOL"):
        assert lib_user.name in all_usernames_in_response


def test_create_user_parallel_from_external_different_classes(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    import_config,
    lo,
    make_user_attrs,
    schoolenv,
    setup_import_config,
    ucr,
):
    parallelism = 20
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    logger.info("*** Using OUs %r and %r, parallelism=%d.", ous[0], ous[1], parallelism)
    attrs = [make_user_attrs(ous) for _i in range(parallelism)]
    for _attr in attrs:
        schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(_attr))

    pool = Pool(processes=parallelism)
    job_args = [(auth_header, attr) for attr in attrs]
    t0 = time.time()
    map_async_result = pool.map_async(create_remote_static, job_args)
    results = map_async_result.get()
    t1 = time.time()
    logger.info("***** got %d results in %d seconds", len(results), t1 - t0)
    logger.debug("***** results=%r", results)
    errors = []
    for r in results:
        try:
            schoolenv.udm._cleanup.setdefault("users/user", []).append(r["dn"])
        except KeyError:
            # continue to collect user DNs, so we can cleanup as much as possible
            errors.append("Result without DN: {!r}.".format(r))
    assert not errors, " ".join(errors)
    wait_for_listener_replication()
    wait_for_s4connector_replication()
    for num, result in enumerate(results, start=1):
        logger.info("*** Checking result %d/%d (%r)...", num, parallelism, result["name"])
        user = get_import_user(result["dn"])
        compare_import_user_and_resource(user, result)
        logger.info("*** OK: LDAP <-> resource")
        # now compare with attrs
        for attr in attrs:
            if attr["name"] == user.name:
                break
        else:
            raise AssertionError("Could not find user with name {!r} in attrs.".format(user.name))
        import_user_cls = user.__class__
        user2 = import_user_cls(**attr)
        user2.disabled = "1" if attr["disabled"] else "0"
        user2.password = ""
        user2.roles = user.roles
        user2.school = ous[0]
        user2.schools = ous
        user2.ucsschool_roles = user.ucsschool_roles  # not in attr
        # add mapped udm_properties not in attr
        mup = import_config["mapped_udm_properties"]
        user2.udm_properties.update({prop: None for prop in mup if prop not in user2.udm_properties})
        compare_import_user_and_resource(user2, result, "ATTR")
        logger.info("*** OK: attr <-> resource")


def test_create_user_parallel_from_external_same_classes(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    import_config,
    lo,
    make_user_attrs,
    schoolenv,
    setup_import_config,
    ucr,
):
    parallelism = 20
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r, parallelism=%d.", ou1, ou2, parallelism)
    attrs = [make_user_attrs(ous) for _i in range(parallelism)]
    for _attr in attrs:
        schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(_attr))

    # put everyone (except staff) into same classes
    everyone_classes = {}
    for attr in attrs:
        if attr["school_classes"]:
            everyone_classes = attr["school_classes"]
            # TODO: create bug report for this, or handle in API server:
            # work around school.lib failing when trying to create same class (and share) in two
            # processes
            group_dns = extract_class_dns(attr)
            for group_dn in group_dns:
                logger.debug("*** Creating group %r...", group_dn)
                LibUser.get_or_create_group_udm_object(group_dn, lo)
            break
    for attr in attrs:
        if not (len(attr["roles"]) == 1 and attr["roles"][0].endswith("/staff")):
            # don't set school_classes on staff
            attr["school_classes"] = everyone_classes
    pool = Pool(processes=parallelism)
    job_args = [(auth_header, attr) for attr in attrs]
    t0 = time.time()
    map_async_result = pool.map_async(create_remote_static, job_args)
    results = map_async_result.get()
    t1 = time.time()
    logger.info("***** got %d results in %d seconds", len(results), t1 - t0)
    logger.debug("***** results=%r", results)
    errors = []
    for r in results:
        try:
            schoolenv.udm._cleanup.setdefault("users/user", []).append(r["dn"])
        except KeyError:
            # continue to collect user DNs, so we can cleanup as much as possible
            errors.append("Result without DN: {!r}.".format(r))
    assert not errors, " ".join(errors)
    wait_for_listener_replication()
    wait_for_s4connector_replication()
    for num, result in enumerate(results, start=1):
        logger.info("*** Checking result %d/%d (%r)...", num, parallelism, result["name"])
        user = get_import_user(result["dn"])
        compare_import_user_and_resource(user, result)
        logger.info("*** OK: LDAP <-> resource")
        # now compare with attrs
        for attr in attrs:
            if attr["name"] == user.name:
                break
        else:
            raise AssertionError("Could not find user with name {!r} in attrs.".format(user.name))
        import_user_cls = user.__class__
        user2 = import_user_cls(**attr)
        user2.disabled = "1" if attr["disabled"] else "0"
        user2.password = ""
        user2.roles = user.roles
        user2.school = ou1
        user2.schools = ous
        user2.ucsschool_roles = user.ucsschool_roles  # not in attr
        # add mapped udm_properties not in attr
        mup = import_config["mapped_udm_properties"]
        user2.udm_properties.update({prop: None for prop in mup if prop not in user2.udm_properties})
        compare_import_user_and_resource(user2, result, "ATTR")
        logger.info("*** OK: attr <-> resource")


def test_partial_update_user_parallel_from_external_different_classes(
    auth_header,
    compare_import_user_and_resource,
    create_import_user,
    extract_class_dns,
    get_import_user,
    import_config,
    make_user_attrs,
    schoolenv,
    setup_import_config,
    ucr,
):
    parallelism = 20
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r, parallelism=%d.", ou1, ou2, parallelism)

    # create users sequentially using Python interface
    jobs = []
    for _i in range(parallelism):
        create_attrs = make_user_attrs(ous, school=ou1, schools=ous)  # overwrite URLs
        del create_attrs["roles"]
        schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))
        user_obj = create_import_user(**create_attrs)
        logger.info("*** Created: %r", user_obj.to_dict())
        assert create_attrs["disabled"] == user_obj.disabled
        roles = tuple(user_obj.roles)
        if roles == ("pupil",):
            roles = ("student",)
        attrs_new = make_user_attrs(
            ous,
            partial=True,
            name=user_obj.name,
            roles=roles,
            source_uid=user_obj.source_uid,
            record_uid=user_obj.record_uid,
            disabled=create_attrs["disabled"],  # TODO: changing 'disabled' in parallel fails
        )
        if isinstance(user_obj, LibStaff):
            create_attrs["school_classes"] = {}
            if "school_classes" in attrs_new:
                attrs_new["school_classes"] = {}
        logger.info("*** attrs_new=%r", attrs_new)
        schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(attrs_new))
        jobs.append((create_attrs, attrs_new))

    # modify users in parallel using HTTP
    wait_for_listener_replication()
    wait_for_s4connector_replication()
    pool = Pool(processes=parallelism)
    t0 = time.time()
    map_async_result = pool.map_async(
        partial_update_remote_static, [(auth_header, job[0]["name"], job[1]) for job in jobs]
    )
    results = map_async_result.get()
    t1 = time.time()
    logger.info("***** got %d results in %d seconds", len(results), t1 - t0)
    logger.debug("***** results=%r", results)
    wait_for_listener_replication()
    wait_for_s4connector_replication()
    for num, result in enumerate(results, start=1):
        logger.info("*** Checking result %d/%d (%r)...", num, parallelism, result.get("name", "N/A"))
        logger.debug("***** result=%r", result)
        user = get_import_user(result["dn"])  # this will fail, when an error was reported
        compare_import_user_and_resource(user, result)
        logger.info("*** OK: LDAP <-> resource")
        # now compare with attrs
        for job in jobs:
            if job[0]["name"] == user.name:
                attr, new_attrs = job
                for k, v in new_attrs.items():
                    if k == "school_classes" and not v:
                        # special case `school_classes`: if newly empty but previously
                        # non-empty -> use old value
                        # see end of ImportUser.make_classes()
                        # Bug #48045
                        continue
                    attr[k] = v
                break
        else:
            raise AssertionError("Could not find user with name {!r} in jobs.".format(user.name))
        import_user_cls = user.__class__
        logger.debug("***** initializing %s 'user2' from attr=%r", user.__class__.__name__, attr)
        user2 = import_user_cls(**attr)
        user2.disabled = "1" if attr["disabled"] else "0"
        logger.debug(
            "####### attr['disabled']=%r -> %r (%r)", attr["disabled"], user2.disabled, user2.name
        )
        user2.password = ""
        user2.roles = user.roles
        user2.school = user2.school.split("/")[-1]  # URL 2 OU
        user2.schools = [ou.split("/")[-1] for ou in user2.schools]  # URLs 2 OUs
        user2.ucsschool_roles = user.ucsschool_roles  # not in attr
        # add mapped udm_properties not in attr
        mup = import_config["mapped_udm_properties"]
        user2.udm_properties.update({prop: None for prop in mup if prop not in user2.udm_properties})
        compare_import_user_and_resource(user2, result, "ATTR")
        logger.info("*** OK: attr <-> resource")


def test_rename_single_user(
    auth_header,
    compare_import_user_and_resource,
    create_import_user,
    extract_class_dns,
    get_import_user,
    make_user_attrs,
    random_username,
    schoolenv,
    setup_import_config,
    ucr,
):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r.", ou1, ou2)
    name_old = random_username()
    logger.info("*** creating user with username %r", name_old)
    create_attrs = make_user_attrs(
        [ou1],
        school=ou1,  # overwrite URLs
        schools=[ou1],  # overwrite URLs
        partial=False,
        name=name_old,
    )
    del create_attrs["roles"]
    logger.info("*** create_attrs=%r", create_attrs)
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))
    old_user_obj = create_import_user(**create_attrs)
    logger.info("*** API call (create) returned: %r", old_user_obj)

    name_new = random_username()
    logger.info("*** renaming user from %r to %r", name_old, name_new)
    schoolenv.udm._cleanup.setdefault("users/user", []).append(
        old_user_obj.dn.replace(name_old, name_new)
    )
    modify_attrs = {"name": name_new}
    logger.info("*** modify_attrs=%r", modify_attrs)
    resource_new = partial_update_remote_static((auth_header, name_old, modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert name_new == resource_new["name"]
    user = get_import_user(resource_new["dn"])
    assert name_new == user.name
    url = urljoin(RESOURCE_URLS["users"], name_new)
    assert resource_new["url"] == url
    resource_new2 = api_call("get", url, headers=auth_header)
    assert_equal_dicts(resource_new, resource_new2)
    url = urljoin(RESOURCE_URLS["users"], name_old)
    response = requests.get(url, headers=auth_header)
    assert response.status_code == 404
    logger.info("*** OK: LDAP <-> resource")
    compare_import_user_and_resource(user, resource_new)


def test_create_user_without_name(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    make_user_attrs,
    schoolenv,
    setup_import_config,
    ucr,
):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r.", ou1, ou2)
    attrs = make_user_attrs(ous)
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(attrs))
    del attrs["name"]
    logger.debug("*** attrs=%r", attrs)
    expected_username = "test.{}.{}".format(attrs["firstname"][:2], attrs["lastname"][:3]).lower()
    result = create_remote_static((auth_header, attrs))
    assert result["name"] == expected_username
    user = get_import_user(result["dn"])
    assert user.name == expected_username
    compare_import_user_and_resource(user, result)
    logger.info("*** OK: LDAP <-> resource")


def test_move_teacher_one_school_only(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    lo,
    make_user_attrs,
    random_username,
    schoolenv,
    ucr,
):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r.", ou1, ou2)
    logger.info("*** Going to move teacher from OU %r to %r ***", ou1, ou2)
    create_attrs = make_user_attrs([ou1], partial=False, roles=("teacher",))
    logger.info("*** create_attrs=%r", create_attrs)
    assert create_attrs["school"].strip("/").split("/")[-1] == ou1
    assert create_attrs["schools"] == [create_attrs["school"]]
    assert list(create_attrs["school_classes"].keys()) == [ou1]
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))

    create_result = create_remote_static((auth_header, create_attrs))
    logger.debug("*** create_result=%r", create_result)
    assert create_result["name"] == create_attrs["name"]
    assert create_result["school"].strip("/").split("/")[-1] == ou1
    assert create_result["schools"] == [create_result["school"]]
    assert create_result["school_classes"] == create_attrs["school_classes"]

    user_old = get_import_user(create_result["dn"])
    logger.debug("*** user_old.school_classes=%r", user_old.school_classes)
    user_old_udm = user_old.get_udm_object(lo)
    old_groups = user_old_udm["groups"]
    logger.info("*** old_groups=%r", old_groups)
    for grp in old_groups:
        assert ou1 in grp
        assert ou2 not in grp

    modify_attrs = {
        "school": create_result["school"].replace(ou1, ou2),
        "schools": [create_result["school"].replace(ou1, ou2)],
        "school_classes": {ou2: sorted([random_username(4), random_username(4)])},
    }
    logger.info("*** modify_attrs=%r", modify_attrs)

    resource_new = partial_update_remote_static((auth_header, create_result["name"], modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert create_result["name"] == resource_new["name"]
    assert modify_attrs["school_classes"] == resource_new["school_classes"]

    user = get_import_user(resource_new["dn"])
    logger.debug("*** user.school_classes=%r", user.school_classes)
    assert create_result["name"] == user.name
    url = urljoin(RESOURCE_URLS["users"], create_result["name"])
    assert resource_new["url"] == url

    resource_new2 = api_call("get", url, headers=auth_header)
    assert_equal_dicts(resource_new, resource_new2)

    compare_import_user_and_resource(user, resource_new)
    logger.info("*** OK: LDAP <-> resource")

    user_new_udm = user.get_udm_object(lo)
    new_groups = user_new_udm["groups"]
    logger.info("*** new_groups=%r", new_groups)
    for grp in new_groups:
        assert ou2 in grp
        assert ou1 not in grp


def test_move_teacher_remove_primary(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    lo,
    make_user_attrs,
    random_username,
    schoolenv,
    ucr,
):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r.", ou1, ou2)
    logger.info(
        "*** Going to create teacher in OUs %r and %r, then remove it from primary (%r). ***",
        ou1,
        ou2,
        ou1,
    )
    create_attrs = make_user_attrs(ous, partial=False, roles=("teacher",))
    logger.info("*** create_attrs=%r", create_attrs)
    assert create_attrs["school"].strip("/").split("/")[-1] == ou1
    assert [
        create_attrs["schools"][0].strip("/").split("/")[-1],
        create_attrs["schools"][1].strip("/").split("/")[-1],
    ] == ous
    assert set(create_attrs["school_classes"].keys()) == {ou1, ou2}
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))

    create_result = create_remote_static((auth_header, create_attrs))
    logger.debug("*** create_result=%r", create_result)
    assert create_result["name"] == create_attrs["name"]
    assert create_result["school"] == create_attrs["school"]
    assert set(create_result["schools"]) == set(create_attrs["schools"])
    assert create_result["school_classes"] == create_attrs["school_classes"]

    user_old = get_import_user(create_result["dn"])
    logger.debug("*** user_old.school_classes=%r", user_old.school_classes)
    user_old_udm = user_old.get_udm_object(lo)
    old_groups = user_old_udm["groups"]
    logger.info("*** old_groups=%r", old_groups)
    for grp_name in (
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou1),
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou2),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou1),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou2),
    ):
        assert any(dn.startswith(grp_name) for dn in old_groups)

    create_attrs_school_classes = {
        (ou, {"{}-{}".format(ou, k) for k in kls}) for ou, kls in create_attrs["school_classes"].items()
    }
    logger.info("*** user_old.school_classes    =%r", user_old.school_classes)
    logger.info("*** create_attrs_school_classes=%r", create_attrs_school_classes)
    assert {s: set(c) for s, c in user_old.school_classes.items()} == create_attrs_school_classes

    modify_attrs = {
        "school": create_result["school"].replace(ou1, ou2),
        "schools": [create_result["school"].replace(ou1, ou2)],
        "school_classes": {ou2: sorted([random_username(4), random_username(4)])},
    }
    logger.info("*** modify_attrs=%r", modify_attrs)

    resource_new = partial_update_remote_static((auth_header, create_result["name"], modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert create_result["name"] == resource_new["name"]
    assert modify_attrs["school_classes"] == resource_new["school_classes"]

    logger.debug("*** zzz...")
    time.sleep(10)

    user = get_import_user(resource_new["dn"])
    logger.debug("*** user.school_classes=%r", user.school_classes)
    assert create_result["name"] == user.name
    url = urljoin(RESOURCE_URLS["users"], create_result["name"])
    assert resource_new["url"] == url

    resource_new2 = api_call("get", url, headers=auth_header)
    assert_equal_dicts(resource_new, resource_new2)

    compare_import_user_and_resource(user, resource_new)
    logger.info("*** OK: LDAP <-> resource")

    user_new_udm = user.get_udm_object(lo)
    new_groups = user_new_udm["groups"]
    logger.info("*** new_groups=%r", new_groups)
    for grp in new_groups:
        assert ou2 in grp
        assert ou1 not in grp


def test_move_teacher_remove_primary_with_classes(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    lo,
    make_user_attrs,
    schoolenv,
    ucr,
):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r.", ou1, ou2)
    logger.info(
        "*** Going to create teacher in OUs %r and %r, then remove it from primary (%r). ***",
        ou1,
        ou2,
        ou1,
    )
    create_attrs = make_user_attrs(ous, partial=False, roles=("teacher",))
    logger.info("*** create_attrs=%r", create_attrs)
    assert create_attrs["school"].strip("/").split("/")[-1] == ou1
    assert [
        create_attrs["schools"][0].strip("/").split("/")[-1],
        create_attrs["schools"][1].strip("/").split("/")[-1],
    ] == ous
    assert set(create_attrs["school_classes"].keys()) == {ou1, ou2}
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))

    create_result = create_remote_static((auth_header, create_attrs))
    logger.debug("*** create_result=%r", create_result)
    assert create_result["name"] == create_attrs["name"]
    assert create_result["school"] == create_attrs["school"]
    assert set(create_result["schools"]) == set(create_attrs["schools"])
    assert create_result["school_classes"] == create_attrs["school_classes"]

    user_old = get_import_user(create_result["dn"])
    logger.debug("*** user_old.school_classes=%r", user_old.school_classes)
    user_old_udm = user_old.get_udm_object(lo)
    old_groups = user_old_udm["groups"]
    logger.info("*** old_groups=%r", old_groups)
    for grp_name in (
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou1),
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou2),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou1),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou2),
    ):
        assert any(dn.startswith(grp_name) for dn in old_groups)

    create_attrs_school_classes = {
        ou: {f"{ou}-{k}" for k in kls} for ou, kls in create_attrs["school_classes"].items()
    }

    logger.info("*** user_old.school_classes    =%r", user_old.school_classes)
    logger.info("*** create_attrs_school_classes=%r", create_attrs_school_classes)
    assert {s: set(c) for s, c in user_old.school_classes.items()} == create_attrs_school_classes

    modify_attrs = {
        "school": create_result["school"].replace(ou1, ou2),
        "schools": [create_result["school"].replace(ou1, ou2)],
    }
    logger.info("*** modify_attrs=%r", modify_attrs)
    logger.debug("*** zzz...")
    time.sleep(5)

    resource_new = partial_update_remote_static((auth_header, create_result["name"], modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert create_result["name"] == resource_new["name"]
    assert resource_new["school_classes"] == {ou2: create_attrs["school_classes"][ou2]}
    logger.debug("*** zzz...")
    time.sleep(5)

    user = get_import_user(resource_new["dn"])
    logger.debug("*** user.school_classes=%r", user.school_classes)
    assert user.school_classes == {
        ou2: ["{}-{}".format(ou2, k) for k in create_attrs["school_classes"][ou2]]
    }
    assert create_result["name"] == user.name
    url = urljoin(RESOURCE_URLS["users"], create_result["name"])
    assert resource_new["url"] == url

    resource_new2 = api_call("get", url, headers=auth_header)
    assert_equal_dicts(resource_new, resource_new2)

    compare_import_user_and_resource(user, resource_new)
    logger.info("*** OK: LDAP <-> resource")

    user_new_udm = user.get_udm_object(lo)
    new_groups = user_new_udm["groups"]
    logger.info("*** new_groups=%r", new_groups)
    for grp in new_groups:
        assert ou2 in grp
        assert ou1 not in grp


def test_move_teacher_remove_primary_no_classes_in_new_school(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    lo,
    make_user_attrs,
    schoolenv,
    setup_import_config,
    ucr,
):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r.", ou1, ou2)
    logger.info(
        "*** Going to create teacher in OUs %r and %r, then remove it from primary (%r). ***",
        ou1,
        ou2,
        ou1,
    )
    create_attrs = make_user_attrs(ous, partial=False, roles=("teacher",))
    del create_attrs["school_classes"][ou2]
    logger.info("*** create_attrs=%r", create_attrs)
    assert create_attrs["school"].strip("/").split("/")[-1] == ou1
    assert [
        create_attrs["schools"][0].strip("/").split("/")[-1],
        create_attrs["schools"][1].strip("/").split("/")[-1],
    ] == ous
    assert list(create_attrs["school_classes"].keys()) == [ou1]
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))

    create_result = create_remote_static((auth_header, create_attrs))
    logger.debug("*** create_result=%r", create_result)
    assert create_result["name"] == create_attrs["name"]
    assert create_result["school"] == create_attrs["school"]
    assert set(create_result["schools"]) == set(create_attrs["schools"])
    assert create_result["school_classes"] == create_attrs["school_classes"]

    user_old = get_import_user(create_result["dn"])
    logger.debug("*** user_old.school_classes=%r", user_old.school_classes)
    user_old_udm = user_old.get_udm_object(lo)
    old_groups = user_old_udm["groups"]
    logger.info("*** old_groups=%r", old_groups)
    for grp_name in (
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou1),
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou1),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou1),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou2),
    ):
        assert any(dn.startswith(grp_name) for dn in old_groups)

    create_attrs_school_classes = {
        (ou, {"{}-{}".format(ou, k) for k in kls}) for ou, kls in create_attrs["school_classes"].items()
    }
    logger.info("*** user_old.school_classes    =%r", user_old.school_classes)
    logger.info("*** create_attrs_school_classes=%r", create_attrs_school_classes)
    assert {s: set(c) for s, c in user_old.school_classes.items()} == create_attrs_school_classes

    modify_attrs = {
        "school": create_result["school"].replace(ou1, ou2),
        "schools": [create_result["school"].replace(ou1, ou2)],
    }
    logger.info("*** modify_attrs=%r", modify_attrs)
    logger.debug("*** zzz...")
    time.sleep(5)

    resource_new = partial_update_remote_static((auth_header, create_result["name"], modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert create_result["name"] == resource_new["name"]
    assert resource_new["school_classes"] == {}
    logger.debug("*** zzz...")
    time.sleep(5)

    user = get_import_user(resource_new["dn"])
    logger.debug("*** user.school_classes=%r", user.school_classes)
    assert user.school_classes == {}
    assert create_result["name"] == user.name
    url = urljoin(RESOURCE_URLS["users"], create_result["name"])
    assert resource_new["url"] == url

    resource_new2 = api_call("get", url, headers=auth_header)
    assert_equal_dicts(resource_new, resource_new2)

    compare_import_user_and_resource(user, resource_new)
    logger.info("*** OK: LDAP <-> resource")

    user_new_udm = user.get_udm_object(lo)
    new_groups = user_new_udm["groups"]
    logger.info("*** new_groups=%r", new_groups)
    for grp in new_groups:
        assert ou2 in grp
        assert ou1 not in grp


def test_move_teacher_remove_primary_with_classes_and_rename(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    lo,
    make_user_attrs,
    random_username,
    schoolenv,
    ucr,
):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ous = sorted([ou_name, ou_name2])
    ou1, ou2 = ous
    logger.info("*** Using OUs %r and %r.", ou1, ou2)
    logger.info(
        "*** Going to create teacher in OUs %r and %r, then remove it from primary (%r) and rename "
        "it. ***",
        ou1,
        ou2,
        ou1,
    )
    create_attrs = make_user_attrs(ous, partial=False, roles=("teacher",))
    logger.info("*** create_attrs=%r", create_attrs)
    assert create_attrs["school"].strip("/").split("/")[-1] == ou1
    assert [
        create_attrs["schools"][0].strip("/").split("/")[-1],
        create_attrs["schools"][1].strip("/").split("/")[-1],
    ] == ous
    assert set(create_attrs["school_classes"].keys()) == {ou1, ou2}
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))

    create_result = create_remote_static((auth_header, create_attrs))
    logger.debug("*** create_result=%r", create_result)
    assert create_result["name"] == create_attrs["name"]
    assert create_result["school"] == create_attrs["school"]
    assert set(create_result["schools"]) == set(create_attrs["schools"])
    assert create_result["school_classes"] == create_attrs["school_classes"]

    user_old = get_import_user(create_result["dn"])
    logger.debug("*** user_old.school_classes=%r", user_old.school_classes)
    user_old_udm = user_old.get_udm_object(lo)
    old_groups = user_old_udm["groups"]
    logger.info("*** old_groups=%r", old_groups)
    for grp_name in (
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou1),
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou2),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou1),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou2),
    ):
        assert any(dn.startswith(grp_name) for dn in old_groups)

    create_attrs_school_classes = {
        (ou, {"{}-{}".format(ou, k) for k in kls}) for ou, kls in create_attrs["school_classes"].items()
    }
    logger.info("*** user_old.school_classes    =%r", user_old.school_classes)
    logger.info("*** create_attrs_school_classes=%r", create_attrs_school_classes)
    assert {s: set(c) for s, c in user_old.school_classes.items()} == create_attrs_school_classes

    modify_attrs = {
        "name": random_username(),
        "school": create_result["school"].replace(ou1, ou2),
        "schools": [create_result["school"].replace(ou1, ou2)],
    }
    assert user_old.name != modify_attrs["name"]
    logger.info("*** modify_attrs=%r", modify_attrs)
    logger.debug("*** zzz...")
    time.sleep(5)

    resource_new = partial_update_remote_static((auth_header, create_result["name"], modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert modify_attrs["name"] == resource_new["name"]
    assert resource_new["school_classes"] == {ou2: create_attrs["school_classes"][ou2]}
    logger.debug("*** zzz...")
    time.sleep(5)

    user = get_import_user(resource_new["dn"])
    logger.debug("*** user.school_classes=%r", user.school_classes)
    assert {s: set(c) for s, c in user.school_classes.items()} == {
        ou2: {"{}-{}".format(ou2, k) for k in create_attrs["school_classes"][ou2]}
    }
    assert modify_attrs["name"] == user.name
    url = urljoin(RESOURCE_URLS["users"], modify_attrs["name"])
    assert resource_new["url"] == url

    resource_new2 = api_call("get", url, headers=auth_header)
    assert_equal_dicts(resource_new, resource_new2)

    compare_import_user_and_resource(user, resource_new)
    logger.info("*** OK: LDAP <-> resource")

    user_new_udm = user.get_udm_object(lo)
    new_groups = user_new_udm["groups"]
    logger.info("*** new_groups=%r", new_groups)
    for grp in new_groups:
        assert ou2 in grp
        assert ou1 not in grp


def test_modify_teacher_remove_all_classes(
    auth_header,
    compare_import_user_and_resource,
    extract_class_dns,
    get_import_user,
    lo,
    make_user_attrs,
    schoolenv,
    ucr,
):
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ou = random.choice([ou_name, ou_name2])
    logger.info("*** Going to create teacher in OU %r, then remove all its classes. ***", ou)
    create_attrs = make_user_attrs([ou], partial=False, roles=("teacher",))
    logger.info("*** create_attrs=%r", create_attrs)
    assert list(create_attrs["school_classes"].keys()) == [ou]
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))

    create_result = create_remote_static((auth_header, create_attrs))
    logger.debug("*** create_result=%r", create_result)
    assert create_result["name"] == create_attrs["name"]
    assert create_result["school"] == create_attrs["school"]
    assert set(create_result["schools"]) == set(create_attrs["schools"])
    assert create_result["school_classes"] == create_attrs["school_classes"]

    user_old = get_import_user(create_result["dn"])
    logger.debug("*** user_old.school_classes=%r", user_old.school_classes)
    user_old_udm = user_old.get_udm_object(lo)
    old_groups = user_old_udm["groups"]
    logger.info("*** old_groups=%r", old_groups)
    for grp_name in (
        "cn=lehrer-{0},cn=groups,ou={0},".format(ou),
        "cn=Domain Users {0},cn=groups,ou={0},".format(ou),
    ):
        assert any(dn.startswith(grp_name) for dn in old_groups)

    create_attrs_school_classes = {
        ou: {f"{ou}-{k}" for k in kls} for ou, kls in create_attrs["school_classes"].items()
    }

    logger.info("*** user_old.school_classes    =%r", user_old.school_classes)
    logger.info("*** create_attrs_school_classes=%r", create_attrs_school_classes)
    assert {s: set(c) for s, c in user_old.school_classes.items()} == create_attrs_school_classes

    modify_attrs = {
        "school_classes": {},
    }
    logger.info("*** modify_attrs=%r", modify_attrs)
    logger.debug("*** zzz...")
    time.sleep(5)

    resource_new = partial_update_remote_static((auth_header, create_result["name"], modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert create_result["name"] == resource_new["name"]
    assert resource_new["school_classes"] == {}
    logger.debug("*** zzz...")
    time.sleep(5)

    user = get_import_user(resource_new["dn"])
    logger.debug("*** user.school_classes=%r", user.school_classes)
    assert user.school_classes == {}
    assert create_result["name"] == user.name
    url = urljoin(RESOURCE_URLS["users"], create_result["name"])
    assert resource_new["url"] == url

    resource_new2 = api_call("get", url, headers=auth_header)
    assert_equal_dicts(resource_new, resource_new2)

    compare_import_user_and_resource(user, resource_new)
    logger.info("*** OK: LDAP <-> resource")


def test_modify_classes_2old_2new(
    auth_header,
    extract_class_dns,
    get_import_user,
    make_user_attrs,
    random_username,
    schoolenv,
    ucr,
):
    role = random.choice(("student", "teacher"))
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ou = random.choice([ou_name, ou_name2])
    logger.info("*** Going to create %s in OU %r. ***", role, ou)
    create_attrs = make_user_attrs([ou], partial=False, roles=(role,))
    logger.info("*** create_attrs=%r", create_attrs)
    assert list(create_attrs["school_classes"].keys()) == [ou]
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(create_attrs))

    create_result = create_remote_static((auth_header, create_attrs))
    logger.debug("*** create_result=%r", create_result)
    assert create_result["name"] == create_attrs["name"]
    assert create_result["school"] == create_attrs["school"]
    assert set(create_result["schools"]) == set(create_attrs["schools"])
    assert create_result["school_classes"] == create_attrs["school_classes"]

    user_old = get_import_user(create_result["dn"])
    old_school_classes = user_old.school_classes
    logger.debug("*** old_school_classes=%r", old_school_classes)

    new_school_classes = {
        ou: sorted([random_username(4), random_username(4)]) for ou in old_school_classes.keys()
    }

    logger.debug("*** new_school_classes=%r", new_school_classes)
    modify_attrs = {
        "school_classes": new_school_classes,
    }
    logger.info("*** modify_attrs=%r", modify_attrs)
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(modify_attrs))
    resource_new = partial_update_remote_static((auth_header, create_result["name"], modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert create_result["name"] == resource_new["name"]
    assert resource_new["school_classes"] == new_school_classes

    user = get_import_user(resource_new["dn"])
    assert create_result["name"] == user.name
    logger.debug("*** user.school_classes=%r", user.school_classes)
    classes_without_ous = {
        ou: [k.split("-", 1)[1] for k in kls] for ou, kls in user.school_classes.items()
    }

    logger.debug("*** user.school_classes without ous=%r", classes_without_ous)
    assert classes_without_ous == new_school_classes
    logger.info("*** OK: 2 classes in old and 2 changed classes in new")


def test_modify_classes_0old_2new(
    auth_header,
    extract_class_dns,
    get_import_user,
    make_user_attrs,
    random_username,
    schoolenv,
    ucr,
):
    role = random.choice(("student", "teacher"))
    (ou_name, ou_dn), (ou_name2, ou_dn2) = schoolenv.create_multiple_ous(2, name_edudc=ucr["hostname"])
    ou = random.choice([ou_name, ou_name2])
    logger.info("*** Going to create %s in OU %r. ***", role, ou)
    create_attrs = make_user_attrs([ou], partial=False, roles=(role,), school_classes={})
    logger.info("*** create_attrs=%r", create_attrs)
    assert create_attrs["school_classes"] == {}

    create_result = create_remote_static((auth_header, create_attrs))
    logger.debug("*** create_result=%r", create_result)
    assert create_result["name"] == create_attrs["name"]
    assert create_result["school"] == create_attrs["school"]
    assert set(create_result["schools"]) == set(create_attrs["schools"])
    assert create_result["school_classes"] == {}

    user_old = get_import_user(create_result["dn"])
    old_school_classes = user_old.school_classes
    logger.debug("*** old_school_classes=%r", old_school_classes)
    assert old_school_classes == {}

    new_school_classes = {
        ou: sorted([random_username(4), random_username(4)]) for ou in old_school_classes.keys()
    }

    logger.debug("*** new_school_classes=%r", new_school_classes)
    modify_attrs = {
        "school_classes": new_school_classes,
    }
    logger.info("*** modify_attrs=%r", modify_attrs)
    schoolenv.udm._cleanup.setdefault("groups/group", []).extend(extract_class_dns(modify_attrs))
    resource_new = partial_update_remote_static((auth_header, create_result["name"], modify_attrs))
    logger.info("*** API call (modify) returned: %r", resource_new)
    assert create_result["name"] == resource_new["name"]
    assert resource_new["school_classes"] == new_school_classes

    user = get_import_user(resource_new["dn"])
    assert create_result["name"] == user.name
    logger.debug("*** user.school_classes=%r", user.school_classes)
    classes_without_ous = {
        ou: [k.split("-", 1)[1] for k in kls] for ou, kls in user.school_classes.items()
    }

    logger.debug("*** user.school_classes without ous=%r", classes_without_ous)
    assert classes_without_ous == new_school_classes
    logger.info("*** OK: 0 classes in old and 2 classes in new")
