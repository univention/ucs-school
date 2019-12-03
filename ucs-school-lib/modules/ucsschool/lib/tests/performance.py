import random
import time
from typing import Dict, List, Optional, Tuple, Type, Union

import requests
from ucsschool.lib.models.base import UCSSchoolHelperAbstractClass
from ucsschool.lib.models.group import Group
from ucsschool.lib.models.user import Teacher, User
from ucsschool.lib.models.utils import ucr

LDAP_BASE_DN = ucr["ldap/base"]
PARALLELISM = 4
SCHOOL_OU = "DEMOSCHOOL"
STR_NUMERIC = "0123456789"
STR_ALPHA = "abcdefghijklmnopqrstuvwxyz"
STR_ALPHANUM = STR_ALPHA + STR_NUMERIC


def random_string(
    length=10, alpha=True, numeric=True
):  # type: (Optional[int], Optional[bool], Optional[bool]) -> str
    result = ""
    for _ in range(length):
        if alpha and numeric:
            result += random.choice(STR_ALPHANUM)
        elif alpha:
            result += random.choice(STR_ALPHA)
        elif numeric:
            result += random.choice(STR_NUMERIC)
    return str(result)


def random_name(length=10):  # type: (Optional[int]) -> str
    """
	create random name (1 ALPHA, 8 ALPHANUM, 1 ALPHA)
	"""
    return (
        random_string(length=1, alpha=True, numeric=False)
        + random_string(length=(length - 2), alpha=True, numeric=True)
        + random_string(length=1, alpha=True, numeric=False)
    )


try:
    from multiprocessing import Pool  # multiprocessing -> processes
    from univention.admin.uldap import access

    print("*** UDM via Python ***")
    API = "python-udm"
    _lo_kwargs = {
        "host": "localhost",
        "port": 7389,
        "base": ucr["ldap/base"],
        "binddn": "uid=Administrator,cn=users,{}".format(ucr["ldap/base"]),
        "bindpw": "univention",
    }
    print("Connection args: {!r}".format(_lo_kwargs))
except ImportError:
    from multiprocessing.dummy import Pool  # multiprocessing.dummy -> threading
    from univention.admin.client import Module, Object, UDM
    from univention.admin.modules import ConnectionData, get as udm_modules_get
    from univention.admin.uldap import position

    print("*** UDM via HTTP ***")
    API = "UDM via HTTP"
    _lo_kwargs = dict(
        uri=ConnectionData.uri(), username="Administrator", password="univention",
    )
    print("Connection args: {!r}".format(_lo_kwargs))


def get_lo():  # type: () -> Union[access, UDM]
    if API == "python-udm":
        return access(**_lo_kwargs)
    else:
        return UDM.http(**_lo_kwargs)


def groups_kwargs(school):  # type: (str) -> Dict[str, str]
    return {
        "name": "{}-test{}".format(school, random_name()),
        "school": school,
        "description": random_name(20),
        "users": [
            "uid=demo_student,cn=schueler,cn=users,ou={},{}".format(
                school, LDAP_BASE_DN
            )
        ],
    }


def user_kwargs(school):  # type: (str) -> Dict[str, str]
    return {
        "name": "test{}".format(random_name()),
        "school": school,
        "schools": [school],
        "firstname": random_name(),
        "lastname": random_name(),
        "birthday": "2015-05-15",
        "email": None,
        "password": None,
        "disabled": False,
        "school_classes": {
            "DEMOSCHOOL": ["{}-Da".format(school), "{}-Db".format(school)],
        },
    }


def create_ucsschool_objs_sequential(kls, num):
    # type: (Type[UCSSchoolHelperAbstractClass], int) -> Tuple[float, List[str]]
    if issubclass(kls, Group):
        kwargs = [groups_kwargs(SCHOOL_OU) for _ in range(num)]
    elif issubclass(kls, User):
        kwargs = [user_kwargs(SCHOOL_OU) for _ in range(num)]
    else:
        raise NotImplementedError("Unknown type {!r}.".format(kls))
    lo = get_lo()
    t0 = time.time()
    dns = []
    for kw in kwargs:
        obj = kls(**kw)
        obj.create(lo)
        dns.append(obj.dn)
    return time.time() - t0, dns


async def read_ucsschool_objs_sequential(
    kls_name_school_dns,
):  # type: (Tuple[str, str, List[str]]) -> float
    kls_name, school, dns = kls_name_school_dns
    kls = globals()[kls_name]  # type: Type[UCSSchoolHelperAbstractClass]
    lo = get_lo()
    t0 = time.time()
    for dn in dns:
        obj = await kls.from_dn(dn, school, lo)
        assert obj.name in dn
    return time.time() - t0


async def modify_ucsschool_obj(
    kls_name_school_dn,
):  # type: (Tuple[str, str, str]) -> float
    kls_name, school, dn = kls_name_school_dn
    kls = globals()[kls_name]  # type: Type[UCSSchoolHelperAbstractClass]
    lo = get_lo()
    obj = await kls.from_dn(dn, school, lo)
    assert obj.name in dn
    if isinstance(obj, Group):
        obj.description = random_string(20)
        obj.users = [
            "uid=demo_admin,cn=schueler,cn=users,ou={},{}".format(
                school, ucr["ldap/base"]
            )
        ]
    elif isinstance(obj, User):
        obj.firstname = random_name()
        obj.lastname = random_name()
    else:
        raise NotImplementedError("Unknown type of obj {!r}.".format(obj))
    t0 = time.time()
    await obj.modify(lo)
    t_delta = time.time() - t0
    obj_new = await kls.from_dn(dn, school, lo)
    if isinstance(obj, Group):
        assert obj_new.description == obj.description
        assert obj_new.users == obj.users
    elif isinstance(obj, User):
        assert obj_new.firstname == obj.firstname
        assert obj_new.lastname == obj.lastname
    else:
        raise NotImplementedError("Unknown type of obj {!r}.".format(obj))
    return t_delta


def modify_ucsschool_objs_sequential(
    kls_name_school_dns,
):  # type: (Tuple[str, str, List[str]]) -> float
    kls_name, school, dns = kls_name_school_dns
    t_delta = 0.0
    for dn in dns:
        t_delta += modify_ucsschool_obj((kls_name, school, dn))
    return t_delta


async def delete_ucsschool_objs_sequential(kls, dns):
    # type: (Type[UCSSchoolHelperAbstractClass], List[str]) -> float
    print("Deleting {} {} sequentially...".format(len(dns), kls.__name__))
    lo = get_lo()
    t0 = time.time()
    for dn in dns:
        await kls.from_dn(dn, SCHOOL_OU, lo).remove(lo)
    return time.time() - t0


def sequential_ucsschool_objs_tests(
    kls,
):  # type: (Type[UCSSchoolHelperAbstractClass]) -> None
    print(
        "Starting sequential tests create {} via ucsschool.lib...".format(kls.__name__)
    )
    dns_to_delete = []
    print("Creating 1 {} (1st time)...".format(kls.__name__))
    t_1_1, dns = create_ucsschool_objs_sequential(kls, 1)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 10 {} (1st time)...".format(kls.__name__))
    t_10_1, dns = create_ucsschool_objs_sequential(kls, 10)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 100 {} (1st time)...".format(kls.__name__))
    t_100_1, dns = create_ucsschool_objs_sequential(kls, 100)
    dns_to_delete.extend(dns)
    time.sleep(2)

    print("Creating 1 {} (2nd time)...".format(kls.__name__))
    t_1_2, dns = create_ucsschool_objs_sequential(kls, 1)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 10 {} (2nd time)...".format(kls.__name__))
    t_10_2, dns = create_ucsschool_objs_sequential(kls, 10)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 100 {} (2nd time)...".format(kls.__name__))
    t_100_2, dns = create_ucsschool_objs_sequential(kls, 100)
    dns_to_delete.extend(dns)
    time.sleep(2)

    print("Creating 1 {} (3rd time)...".format(kls.__name__))
    t_1_3, dns1 = create_ucsschool_objs_sequential(kls, 1)
    dns_to_delete.extend(dns1)
    time.sleep(2)
    print("Creating 10 {} (3rd time)...".format(kls.__name__))
    t_10_3, dns2 = create_ucsschool_objs_sequential(kls, 10)
    dns_to_delete.extend(dns2)
    time.sleep(2)
    print("Creating 100 {} (3rd time)...".format(kls.__name__))
    t_100_3, dns3 = create_ucsschool_objs_sequential(kls, 100)
    dns_to_delete.extend(dns3)
    time.sleep(5)

    kls.invalidate_all_caches()
    print("Reading 1 {}...".format(kls.__name__))
    t_100_41 = read_ucsschool_objs_sequential((kls.__name__, SCHOOL_OU, dns1))
    print("Reading 10 {}...".format(kls.__name__))
    t_100_42 = read_ucsschool_objs_sequential((kls.__name__, SCHOOL_OU, dns2))
    print("Reading 100 {}...".format(kls.__name__))
    t_100_43 = read_ucsschool_objs_sequential((kls.__name__, SCHOOL_OU, dns3))

    print("Modifying 1 {}...".format(kls.__name__))
    t_1_51 = modify_ucsschool_objs_sequential((kls.__name__, SCHOOL_OU, dns1))
    time.sleep(2)
    print("Modifying 10 {}...".format(kls.__name__))
    t_10_52 = modify_ucsschool_objs_sequential((kls.__name__, SCHOOL_OU, dns2))
    time.sleep(2)
    print("Modifying 100 {}...".format(kls.__name__))
    t_100_53 = modify_ucsschool_objs_sequential((kls.__name__, SCHOOL_OU, dns3))
    time.sleep(5)

    print("Results sequential tests via ucsschool.lib for {}:".format(kls.__name__))
    print(
        "Seconds for creating   1 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_1_1, t_1_2, t_1_3
        )
    )
    print(
        "Seconds for creating  10 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_10_1, t_10_2, t_10_3
        )
    )
    print(
        "Seconds for creating 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_100_1, t_100_2, t_100_3
        )
    )
    print(
        "Seconds for reading  1, 10, 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_100_41, t_100_42, t_100_43
        )
    )
    print(
        "Seconds for modifying  1, 10, 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_1_51, t_10_52, t_100_53
        )
    )

    t_delta = delete_ucsschool_objs_sequential(kls, dns_to_delete)
    print("({:02.2f} sec)".format(t_delta))


def create_ucsschool_lib_obj_via_ucsschool_lib(
    kls_name_kwargs,
):  # type: (Tuple[str, Dict[str, str]]) -> str
    kls_name, kwargs = kls_name_kwargs
    kls = globals()[kls_name]  # type: Type[UCSSchoolHelperAbstractClass]
    lo = get_lo()
    sc = kls(**kwargs)
    sc.create(lo)
    return sc.dn


def create_obj_parallel_via_ucsschool_lib(kls, num, parallelism):
    # type: (Type[UCSSchoolHelperAbstractClass], int, int) -> Tuple[float, List[str]]
    if issubclass(kls, Group):
        kwargs = [(kls.__name__, groups_kwargs(SCHOOL_OU)) for _ in range(num)]
    elif issubclass(kls, User):
        kwargs = [(kls.__name__, user_kwargs(SCHOOL_OU)) for _ in range(num)]
    else:
        raise NotImplementedError("Unknown type {!r}.".format(kls))
    pool = Pool(processes=parallelism)
    t0 = time.time()
    map_async_result = pool.map_async(
        create_ucsschool_lib_obj_via_ucsschool_lib, kwargs
    )
    results = map_async_result.get()
    return time.time() - t0, results


def read_ucsschool_objs_parallel(kls, school, dns, parallelism):
    # type: (Type[UCSSchoolHelperAbstractClass], str, List[str], int) -> float
    kwargs = [(kls.__name__, school, [dn]) for dn in dns]
    pool = Pool(processes=parallelism)
    t0 = time.time()
    map_async_result = pool.map_async(read_ucsschool_objs_sequential, kwargs)
    results = map_async_result.get()
    return time.time() - t0


def modify_ucsschool_objs_parallel(kls, school, dns, parallelism):
    # type: (Type[UCSSchoolHelperAbstractClass], str, List[str], int) -> float
    kwargs = [(kls.__name__, school, dn) for dn in dns]
    pool = Pool(processes=parallelism)
    t0 = time.time()
    map_async_result = pool.map_async(modify_ucsschool_obj, kwargs)
    results = map_async_result.get()
    return time.time() - t0


async def delete_obj_via_ucsschool_lib(kls_name_dn):  # type: (Tuple[str, str]) -> None
    kls_name, dn = kls_name_dn
    kls = globals()[kls_name]  # type: Type[UCSSchoolHelperAbstractClass]
    lo = get_lo()
    await kls.from_dn(dn, SCHOOL_OU, lo).remove(lo)


def delete_objs_parallel_via_ucsschool_lib(kls, dns, parallelism):
    # type: (Type[UCSSchoolHelperAbstractClass], List[str], int) -> float
    print("Deleting {} {} in parallel...".format(len(dns), kls.__name__))
    kwargs = [(kls.__name__, dn) for dn in dns]
    pool = Pool(processes=parallelism)
    t0 = time.time()
    map_async_result = pool.map_async(delete_obj_via_ucsschool_lib, kwargs)
    results = map_async_result.get()
    return time.time() - t0


def parallel_ucsschool_objs_tests(
    kls,
):  # type: (Type[UCSSchoolHelperAbstractClass]) -> None
    print(
        "Starting parallel tests create {} via ucsschool.lib (parallelism={}, {})...".format(
            kls.__name__, PARALLELISM, Pool.__module__
        )
    )
    dns_to_delete = []
    print("Creating 1 {} (1st time)...".format(kls.__name__))
    t_1_1, dns = create_obj_parallel_via_ucsschool_lib(kls, 1, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 10 {} (1st time)...".format(kls.__name__))
    t_10_1, dns = create_obj_parallel_via_ucsschool_lib(kls, 10, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 100 {} (1st time)...".format(kls.__name__))
    t_100_1, dns = create_obj_parallel_via_ucsschool_lib(kls, 100, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)

    print("Creating 1 {} (2nd time)...".format(kls.__name__))
    t_1_2, dns = create_obj_parallel_via_ucsschool_lib(kls, 1, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 10 {} (2nd time)...".format(kls.__name__))
    t_10_2, dns = create_obj_parallel_via_ucsschool_lib(kls, 10, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 100 {} (2nd time)...".format(kls.__name__))
    t_100_2, dns = create_obj_parallel_via_ucsschool_lib(kls, 100, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)

    print("Creating 1 {} (3rd time)...".format(kls.__name__))
    t_1_3, dns1 = create_obj_parallel_via_ucsschool_lib(kls, 1, PARALLELISM)
    dns_to_delete.extend(dns1)
    time.sleep(2)
    print("Creating 10 {} (3rd time)...".format(kls.__name__))
    t_10_3, dns2 = create_obj_parallel_via_ucsschool_lib(kls, 10, PARALLELISM)
    dns_to_delete.extend(dns2)
    time.sleep(2)
    print("Creating 100 {} (3rd time)...".format(kls.__name__))
    t_100_3, dns3 = create_obj_parallel_via_ucsschool_lib(kls, 100, PARALLELISM)
    dns_to_delete.extend(dns3)
    time.sleep(5)

    kls.invalidate_all_caches()
    print("Reading 1 {}...".format(kls.__name__))
    t_100_41 = read_ucsschool_objs_parallel(kls, SCHOOL_OU, dns1, PARALLELISM)
    print("Reading 10 {}...".format(kls.__name__))
    t_100_42 = read_ucsschool_objs_parallel(kls, SCHOOL_OU, dns2, PARALLELISM)
    print("Reading 100 {}...".format(kls.__name__))
    t_100_43 = read_ucsschool_objs_parallel(kls, SCHOOL_OU, dns3, PARALLELISM)

    print("Modifying 1 {}...".format(kls.__name__))
    t_1_51 = modify_ucsschool_objs_parallel(kls, SCHOOL_OU, dns1, PARALLELISM)
    time.sleep(2)
    print("Modifying 10 {}...".format(kls.__name__))
    t_10_52 = modify_ucsschool_objs_parallel(kls, SCHOOL_OU, dns2, PARALLELISM)
    time.sleep(2)
    print("Modifying 100 {}...".format(kls.__name__))
    t_100_53 = modify_ucsschool_objs_parallel(kls, SCHOOL_OU, dns3, PARALLELISM)
    time.sleep(5)

    print("Results parallel create {} via ucsschool.lib".format(kls.__name__))
    print(
        "Seconds for creating   1 {}:  {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_1_1, t_1_2, t_1_3
        )
    )
    print(
        "Seconds for creating  10 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_10_1, t_10_2, t_10_3
        )
    )
    print(
        "Seconds for creating 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_100_1, t_100_2, t_100_3
        )
    )
    print(
        "Seconds for reading  1, 10, 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_100_41, t_100_42, t_100_43
        )
    )
    print(
        "Seconds for modifying  1, 10, 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_1_51, t_10_52, t_100_53
        )
    )

    t_delta = delete_objs_parallel_via_ucsschool_lib(kls, dns_to_delete, PARALLELISM)
    print("({:02.2f} sec)".format(t_delta))


def groups_resource_kwargs(school):
    return {
        "properties": {
            "name": "{}-test{}".format(school, random_name()),
            "description": "Text",
            "users": [
                "uid=demo_student,cn=schueler,cn=users,ou={},{}".format(
                    school, ucr["ldap/base"]
                ),
                "uid=demo_teacher,cn=lehrer,cn=users,ou={},{}".format(
                    school, ucr["ldap/base"]
                ),
            ],
        },
        "position": "cn=klassen,cn=schueler,cn=groups,ou={},{}".format(
            school, ucr["ldap/base"]
        ),
        "superordinate": None,
        "options": {"posix": True, "samba": True},
        "policies": {},
    }


def user_resource_kwargs(school):
    return {
        "properties": {
            "username": "test{}".format(random_name()),
            "password": random_name(),
            "firstname": random_name(),
            "lastname": random_name(),
            "birthday": "2015-05-15",
            "disabled": False,
            "groups": [
                "cn=DEMOSCHOOL-Da,cn=klassen,cn=schueler,cn=groups,ou={},{}".format(
                    school, ucr["ldap/base"]
                ),
                "cn=DEMOSCHOOL-Db,cn=klassen,cn=schueler,cn=groups,ou={},{}".format(
                    school, ucr["ldap/base"]
                ),
            ],
        },
        "position": "cn=lehrer,cn=users,ou={},{}".format(school, ucr["ldap/base"]),
        "superordinate": None,
        "options": {"ucsschoolTeacher": True},
        "policies": {},
    }


def create_obj_via_UDM_HTTP_API_sequential(
    kls_data,
):  # type: (Tuple[str, Dict[str, str]]) -> str
    kls_name, data = kls_data
    kls = globals()[kls_name]  # type: Type[UCSSchoolHelperAbstractClass]
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if issubclass(kls, Group):
        url = "{}/groups/group/".format(_lo_kwargs["uri"])
    elif issubclass(kls, User):
        url = "{}/users/user/".format(_lo_kwargs["uri"])
    else:
        raise NotImplementedError("Unknown type {!r}.".format(kls))
    resp = requests.post(
        url,
        headers=headers,
        json=data,
        auth=(_lo_kwargs["username"], _lo_kwargs["password"]),
    )
    if resp.status_code != 201:
        print("resp.status_code={!r}".format(resp.status_code))
        print("resp.text={!r}".format(resp.text))
        print("resp.json()={!r}".format(resp.json()))
        print("resp.headers={!r}".format(resp.headers))
        raise RuntimeError("Creation failed.")
    obj_url = resp.headers["Location"]
    # OK - now get the DN
    headers = {"Accept": "application/json"}
    resp = requests.get(
        obj_url, headers=headers, auth=(_lo_kwargs["username"], _lo_kwargs["password"])
    )
    if resp.status_code != 200:
        print("resp.status_code={!r}".format(resp.status_code))
        print("resp.text={!r}".format(resp.text))
        print("resp.json()={!r}".format(resp.json()))
        print("resp.headers={!r}".format(resp.headers))
        raise RuntimeError("Reading {} failed.".format(kls.__name__))
    return resp.json()["dn"]


def create_objs_via_UDM_HTTP_API_sequential(kls, num):
    # type: (Type[UCSSchoolHelperAbstractClass], int) -> Tuple[float, List[str]]
    t0 = time.time()
    res = []
    for _ in range(num):
        # create group
        if issubclass(kls, Group):
            data = groups_resource_kwargs(SCHOOL_OU)
        elif issubclass(kls, User):
            data = user_resource_kwargs(SCHOOL_OU)
        else:
            raise NotImplementedError("Unknown type {!r}.".format(kls))
        dn = create_obj_via_UDM_HTTP_API_sequential((kls.__name__, data))
        res.append(dn)
    return time.time() - t0, res


def read_obj_via_UDM_HTTP_API(kls_name_dn):  # type: (Tuple[str, str]) -> None
    kls_name, dn = kls_name_dn
    headers = {"Accept": "application/json"}
    if kls_name == "Group":
        base_url = "{}/groups/group/".format(_lo_kwargs["uri"])
    elif kls_name == "Teacher":
        base_url = "{}/users/user/".format(_lo_kwargs["uri"])
    else:
        raise NotImplementedError("Unknown type {!r}.".format(kls_name))
    obj_url = base_url + dn
    resp = requests.get(
        obj_url, headers=headers, auth=(_lo_kwargs["username"], _lo_kwargs["password"])
    )
    if resp.status_code != 200:
        print("resp.status_code={!r}".format(resp.status_code))
        print("resp.text={!r}".format(resp.text))
        print("resp.json()={!r}".format(resp.json()))
        print("resp.headers={!r}".format(resp.headers))
        raise RuntimeError("Reading {} failed.".format(kls_name))
    assert resp.json()["dn"] == dn, resp.json()


def read_objs_via_UDM_HTTP_API_sequential(
    kls_name_dns,
):  # type: (Tuple[str, List[str]]) -> float
    kls_name, dns = kls_name_dns
    t0 = time.time()
    for dn in dns:
        read_obj_via_UDM_HTTP_API((kls_name, dn))
    return time.time() - t0


def modify_obj_via_UDM_HTTP_API(
    kls_name_school_dn,
):  # type: (Tuple[str, str, str]) -> float
    kls_name, school, dn = kls_name_school_dn
    kls = globals()[kls_name]  # type: Type[UCSSchoolHelperAbstractClass]
    if kls_name == "Group":
        base_url = "{}/groups/group/".format(_lo_kwargs["uri"])
    elif kls_name == "Teacher":
        base_url = "{}/users/user/".format(_lo_kwargs["uri"])
    else:
        raise NotImplementedError("Unknown type of obj {!r}.".format(kls_name))
    obj_url = base_url + dn
    headers = {"Accept": "application/json"}
    resp = requests.get(
        obj_url, headers=headers, auth=(_lo_kwargs["username"], _lo_kwargs["password"])
    )
    if resp.status_code != 200:
        print("resp.status_code={!r}".format(resp.status_code))
        print("resp.text={!r}".format(resp.text))
        print("resp.json()={!r}".format(resp.json()))
        print("resp.headers={!r}".format(resp.headers))
        raise RuntimeError("Reading {} failed.".format(kls.__name__))
    obj_old = resp.json()
    data = {
        "position": obj_old["position"],
        "options": obj_old["options"],
        "policies": obj_old["policies"],
        "properties": {},
    }
    if kls_name == "Group":
        data["properties"] = {
            "description": random_string(20),
            "users": [
                "uid=demo_admin,cn=schueler,cn=users,ou={},{}".format(
                    school, ucr["ldap/base"]
                )
            ],
        }
    elif kls_name == "Teacher":
        data["properties"] = {
            "firstname": random_name(),
            "lastname": random_name(),
        }
    else:
        raise NotImplementedError("Unknown type of obj {!r}.".format(kls_name))
    t0 = time.time()
    resp = requests.patch(
        obj_url,
        headers=headers,
        json=data,
        auth=(_lo_kwargs["username"], _lo_kwargs["password"]),
    )
    t_delta = time.time() - t0
    if resp.status_code != 200:
        print("resp.status_code={!r}".format(resp.status_code))
        print("resp.text={!r}".format(resp.text))
        print("resp.json()={!r}".format(resp.json()))
        print("resp.headers={!r}".format(resp.headers))
        raise RuntimeError("Modification failed.")
    resp = requests.get(
        obj_url, headers=headers, auth=(_lo_kwargs["username"], _lo_kwargs["password"])
    )
    if resp.status_code != 200:
        print("resp.status_code={!r}".format(resp.status_code))
        print("resp.text={!r}".format(resp.text))
        print("resp.json()={!r}".format(resp.json()))
        print("resp.headers={!r}".format(resp.headers))
        raise RuntimeError("Reading {} failed.".format(kls.__name__))
    obj_new = resp.json()
    if kls_name == "Group":
        assert obj_new["properties"]["description"] == data["properties"]["description"]
        assert obj_new["properties"]["users"] == data["properties"]["users"]
    elif kls_name == "Teacher":
        assert obj_new["properties"]["firstname"] == data["properties"]["firstname"]
        assert obj_new["properties"]["lastname"] == data["properties"]["lastname"]
    else:
        raise NotImplementedError("Unknown type of obj {!r}.".format(kls_name))
    return t_delta


def modify_objs_via_UDM_HTTP_API_sequential(
    kls_name_school_dns,
):  # type: (Tuple[str, str, List[str]]) -> float
    kls_name, school, dns = kls_name_school_dns
    t_delta = 0.0
    for dn in dns:
        t_delta += modify_obj_via_UDM_HTTP_API((kls_name, school, dn))
    return t_delta


def delete_obj_via_UDM_HTTP_API(kls_name_dn):  # type: (Tuple[str, str]) -> None
    kls_name, dn = kls_name_dn
    headers = {"Accept": "application/json"}
    if kls_name == "Group":
        url = "{}/groups/group/{}".format(_lo_kwargs["uri"], dn)
    elif kls_name == "Teacher":
        url = "{}/users/user/{}".format(_lo_kwargs["uri"], dn)
    else:
        raise NotImplementedError("Unknown type {!r}.".format(kls_name))
    resp = requests.delete(
        url, headers=headers, auth=(_lo_kwargs["username"], _lo_kwargs["password"])
    )
    if resp.status_code != 200:
        print("resp.status_code={!r}".format(resp.status_code))
        print("resp.text={!r}".format(resp.text))
        print("resp.json()={!r}".format(resp.json()))
        print("resp.headers={!r}".format(resp.headers))
        raise RuntimeError("Deleting {} failed.".format(kls_name))


def delete_objs_via_UDM_HTTP_API_sequential(kls, dns):
    # type: (Type[UCSSchoolHelperAbstractClass], List[str]) -> float
    print(
        "Deleting {} {} directly via HTTP (sequentially)...".format(
            kls.__name__, len(dns)
        )
    )
    t0 = time.time()
    for dn in dns:
        delete_obj_via_UDM_HTTP_API((kls.__name__, dn))
    return time.time() - t0


def direct_http_tests_sequential(
    kls,
):  # type: (Type[UCSSchoolHelperAbstractClass]) -> None
    print(
        "Starting direct, non-restful, sequential HTTP tests create {}...".format(
            kls.__name__
        )
    )
    dns_to_delete = []
    print("Creating 1 {} (1st time)...".format(kls.__name__))
    t_1_1, dns = create_objs_via_UDM_HTTP_API_sequential(kls, 1)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 10 {} (1st time)...".format(kls.__name__))
    t_10_1, dns = create_objs_via_UDM_HTTP_API_sequential(kls, 10)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 100 {} (1st time)...".format(kls.__name__))
    t_100_1, dns = create_objs_via_UDM_HTTP_API_sequential(kls, 100)
    dns_to_delete.extend(dns)
    time.sleep(2)

    print("Creating 1 {} (2nd time)...".format(kls.__name__))
    t_1_2, dns = create_objs_via_UDM_HTTP_API_sequential(kls, 1)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 10 {} (2nd time)...".format(kls.__name__))
    t_10_2, dns = create_objs_via_UDM_HTTP_API_sequential(kls, 10)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 100 {} (2nd time)...".format(kls.__name__))
    t_100_2, dns = create_objs_via_UDM_HTTP_API_sequential(kls, 100)
    dns_to_delete.extend(dns)
    time.sleep(2)

    print("Creating 1 {} (3rd time)...".format(kls.__name__))
    t_1_3, dns1 = create_objs_via_UDM_HTTP_API_sequential(kls, 1)
    dns_to_delete.extend(dns1)
    time.sleep(2)
    print("Creating 10 {} (3rd time)...".format(kls.__name__))
    t_10_3, dns2 = create_objs_via_UDM_HTTP_API_sequential(kls, 10)
    dns_to_delete.extend(dns2)
    time.sleep(2)
    print("Creating 100 {} (3rd time)...".format(kls.__name__))
    t_100_3, dns3 = create_objs_via_UDM_HTTP_API_sequential(kls, 100)
    dns_to_delete.extend(dns3)
    time.sleep(5)

    kls.invalidate_all_caches()
    print("Reading 1 {}...".format(kls.__name__))
    t_100_41 = read_objs_via_UDM_HTTP_API_sequential((kls.__name__, dns1))
    print("Reading 10 {}...".format(kls.__name__))
    t_100_42 = read_objs_via_UDM_HTTP_API_sequential((kls.__name__, dns2))
    print("Reading 100 {}...".format(kls.__name__))
    t_100_43 = read_objs_via_UDM_HTTP_API_sequential((kls.__name__, dns3))

    print("Modifying 1 {}...".format(kls.__name__))
    t_1_51 = modify_objs_via_UDM_HTTP_API_sequential((kls.__name__, SCHOOL_OU, dns1))
    time.sleep(2)
    print("Modifying 10 {}...".format(kls.__name__))
    t_10_52 = modify_objs_via_UDM_HTTP_API_sequential((kls.__name__, SCHOOL_OU, dns2))
    time.sleep(2)
    print("Modifying 100 {}...".format(kls.__name__))
    t_100_53 = modify_objs_via_UDM_HTTP_API_sequential((kls.__name__, SCHOOL_OU, dns3))
    time.sleep(5)

    print(
        "Results for direct,, non-restful, sequential HTTP tests for {}".format(
            kls.__name__
        )
    )
    print(
        "Seconds for creating   1 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_1_1, t_1_2, t_1_3
        )
    )
    print(
        "Seconds for creating  10 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_10_1, t_10_2, t_10_3
        )
    )
    print(
        "Seconds for creating 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_100_1, t_100_2, t_100_3
        )
    )
    print(
        "Seconds for reading  1, 10, 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_100_41, t_100_42, t_100_43
        )
    )
    print(
        "Seconds for modifying  1, 10, 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_1_51, t_10_52, t_100_53
        )
    )

    t_delta = delete_objs_via_UDM_HTTP_API_sequential(kls, dns_to_delete)
    print("({:02.2f} sec)".format(t_delta))


def create_objs_via_UDM_HTTP_API_parallel(kls, school, num, parallelism):
    # type: (Type[UCSSchoolHelperAbstractClass], str, int, int) -> Tuple[float, List[str]]
    if issubclass(kls, Group):
        kwargs = [(kls.__name__, groups_resource_kwargs(school)) for _ in range(num)]
    elif issubclass(kls, User):
        kwargs = [(kls.__name__, user_resource_kwargs(school)) for _ in range(num)]
    else:
        raise NotImplementedError("Unknown type {!r}.".format(kls))

    pool = Pool(processes=parallelism)
    t0 = time.time()
    map_async_result = pool.map_async(create_obj_via_UDM_HTTP_API_sequential, kwargs)
    results = map_async_result.get()
    return time.time() - t0, results


def read_objs_via_UDM_HTTP_API_parallel(kls, dns, parallelism):
    # type: (Type[UCSSchoolHelperAbstractClass], List[str], int) -> float
    kwargs = [(kls.__name__, dn) for dn in dns]
    pool = Pool(processes=parallelism)
    t0 = time.time()
    map_async_result = pool.map_async(read_obj_via_UDM_HTTP_API, kwargs)
    results = map_async_result.get()
    return time.time() - t0


def modify_objs_via_UDM_HTTP_API_parallel(kls, school, dns, parallelism):
    # type: (Type[UCSSchoolHelperAbstractClass], str, List[str], int) -> float
    kwargs = [(kls.__name__, school, dn) for dn in dns]
    pool = Pool(processes=parallelism)
    map_async_result = pool.map_async(modify_obj_via_UDM_HTTP_API, kwargs)
    results = map_async_result.get()
    return sum(results)


def delete_objs_via_UDM_HTTP_API_parallel(kls, dns, parallelism):
    # type: (Type[UCSSchoolHelperAbstractClass], List[str], int) -> float
    print("Deleting {} groups directly via HTTP (parallel)...".format(len(dns)))
    kwargs = [(kls.__name__, dn) for dn in dns]
    pool = Pool(processes=parallelism)
    t0 = time.time()
    map_async_result = pool.map_async(delete_obj_via_UDM_HTTP_API, kwargs)
    results = map_async_result.get()
    return time.time() - t0


def direct_http_tests_parallel(
    kls,
):  # type: (Type[UCSSchoolHelperAbstractClass]) -> None
    print(
        "Starting direct, non-restful, parallel HTTP tests (parallelism={}, {})...".format(
            PARALLELISM, Pool.__module__
        )
    )
    dns_to_delete = []
    print("Creating 1 {} (1st time)...".format(kls.__name__))
    t_1_1, dns = create_objs_via_UDM_HTTP_API_parallel(kls, SCHOOL_OU, 1, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 10 {} (1st time)...".format(kls.__name__))
    t_10_1, dns = create_objs_via_UDM_HTTP_API_parallel(kls, SCHOOL_OU, 10, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 100 {} (1st time)...".format(kls.__name__))
    t_100_1, dns = create_objs_via_UDM_HTTP_API_parallel(
        kls, SCHOOL_OU, 100, PARALLELISM
    )
    dns_to_delete.extend(dns)
    time.sleep(2)

    print("Creating 1 {} (2nd time)...".format(kls.__name__))
    t_1_2, dns = create_objs_via_UDM_HTTP_API_parallel(kls, SCHOOL_OU, 1, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 10 {} (2nd time)...".format(kls.__name__))
    t_10_2, dns = create_objs_via_UDM_HTTP_API_parallel(kls, SCHOOL_OU, 10, PARALLELISM)
    dns_to_delete.extend(dns)
    time.sleep(2)
    print("Creating 100 {} (2nd time)...".format(kls.__name__))
    t_100_2, dns = create_objs_via_UDM_HTTP_API_parallel(
        kls, SCHOOL_OU, 100, PARALLELISM
    )
    dns_to_delete.extend(dns)
    time.sleep(2)

    print("Creating 1 {} (3rd time)...".format(kls.__name__))
    t_1_3, dns1 = create_objs_via_UDM_HTTP_API_parallel(kls, SCHOOL_OU, 1, PARALLELISM)
    dns_to_delete.extend(dns1)
    time.sleep(2)
    print("Creating 10 {} (3rd time)...".format(kls.__name__))
    t_10_3, dns2 = create_objs_via_UDM_HTTP_API_parallel(
        kls, SCHOOL_OU, 10, PARALLELISM
    )
    dns_to_delete.extend(dns2)
    time.sleep(2)
    print("Creating 100 {} (3rd time)...".format(kls.__name__))
    t_100_3, dns3 = create_objs_via_UDM_HTTP_API_parallel(
        kls, SCHOOL_OU, 100, PARALLELISM
    )
    dns_to_delete.extend(dns3)
    time.sleep(5)

    kls.invalidate_all_caches()
    print("Reading 1 {}...".format(kls.__name__))
    t_100_41 = read_objs_via_UDM_HTTP_API_parallel(kls, dns1, PARALLELISM)
    print("Reading 10 {}...".format(kls.__name__))
    t_100_42 = read_objs_via_UDM_HTTP_API_parallel(kls, dns2, PARALLELISM)
    print("Reading 100 {}...".format(kls.__name__))
    t_100_43 = read_objs_via_UDM_HTTP_API_parallel(kls, dns3, PARALLELISM)

    print("Modifying 1 {}...".format(kls.__name__))
    t_1_51 = modify_objs_via_UDM_HTTP_API_parallel(kls, SCHOOL_OU, dns1, PARALLELISM)
    time.sleep(2)
    print("Modifying 10 {}...".format(kls.__name__))
    t_10_52 = modify_objs_via_UDM_HTTP_API_parallel(kls, SCHOOL_OU, dns2, PARALLELISM)
    time.sleep(2)
    print("Modifying 100 {}...".format(kls.__name__))
    t_100_53 = modify_objs_via_UDM_HTTP_API_parallel(kls, SCHOOL_OU, dns3, PARALLELISM)
    time.sleep(5)

    print(
        "Results for direct, non-restful, parallel HTTP tests for {}".format(
            kls.__name__
        )
    )
    print(
        "Seconds for creating   1 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_1_1, t_1_2, t_1_3
        )
    )
    print(
        "Seconds for creating  10 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_10_1, t_10_2, t_10_3
        )
    )
    print(
        "Seconds for creating 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_100_1, t_100_2, t_100_3
        )
    )
    print(
        "Seconds for reading  1, 10, 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_100_41, t_100_42, t_100_43
        )
    )
    print(
        "Seconds for modifying  1, 10, 100 {}: {:02.2f} {:02.2f} {:02.2f}".format(
            kls.__name__, t_1_51, t_10_52, t_100_53
        )
    )

    t_delta = delete_objs_via_UDM_HTTP_API_parallel(kls, dns_to_delete, PARALLELISM)
    print("({:02.2f} sec)".format(t_delta))


def main():
    sequential_ucsschool_objs_tests(Group)
    time.sleep(10)
    parallel_ucsschool_objs_tests(Group)
    time.sleep(10)
    sequential_ucsschool_objs_tests(Teacher)
    time.sleep(10)
    parallel_ucsschool_objs_tests(Teacher)
    if API == "UDM via HTTP":
        time.sleep(10)
        direct_http_tests_sequential(Group)
        time.sleep(10)
        direct_http_tests_parallel(Group)
        time.sleep(10)
        direct_http_tests_sequential(Teacher)
        time.sleep(10)
        direct_http_tests_parallel(Teacher)


if __name__ == "__main__":
    main()
