#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: check availability of umc modules
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-multiserver|ucs-school-replica|ucs-school-singleserver]

from univention.testing import utils
from univention.testing.umc import Client


def listUnion(firstList, secondList):
    return list(set(firstList).union(set(secondList)))


def contains(big, small):
    print("small = {}".format(small))
    print("big = {}".format(big))
    intersection = [x for x in small if x in big]
    print("intersect = {}".format(intersection))
    return sorted(intersection) == sorted(small)


def removeListFromOther(big, small):
    big_copy = big[:]
    for item in big_copy:
        if item in small:
            big_copy.remove(item)
    return big_copy


def checkModules(modules, userType, serverRole, singleMaster):
    defaultList = []
    ignoreList = [("lib", None), ("passwordreset", None)]

    # Lehrer auf dem Primary Directory Node
    dc_teacher = defaultList + [
        ("schoolgroups", "workgroup-admin"),
        ("schoolusers", "student"),
        ("schoollists", None),
    ]
    # Lehrer auf dem Schul-DC
    dcs_teacher = defaultList + [
        ("computerroom", None),
        ("distribution", "teacher"),
        ("schoolexam", None),
        ("helpdesk", None),
        ("printermoderation", None),
        ("schoolgroups", "workgroup-admin"),
        ("schoolusers", "student"),
        ("schoollists", None),
    ]
    # Schuladmin sollte auf dem Primary Directory Node
    dc_schooladmin = defaultList + [
        ("schoolusers", "student"),
        ("schoolusers", "teacher"),
        ("schoolusers", "staff"),
        ("schoolrooms", None),
        ("schoolgroups", "workgroup-admin"),
        ("schoolgroups", "class"),
        ("schoolgroups", "teacher"),
        ("schoollists", None),
    ]
    # Schuladmin sollte auf dem Schul-DC
    dcs_schooladmin = defaultList + [
        ("computerroom", None),
        ("distribution", "admin"),
        ("schoolexam", None),
        ("printermoderation", None),
        ("helpdesk", None),
        ("schoolusers", "student"),
        ("schoolusers", "teacher"),
        ("schoolusers", "staff"),
        ("schoolrooms", None),
        ("schoolgroups", "class"),
        ("schoolgroups", "teacher"),
        ("schoolgroups", "workgroup-admin"),
        ("internetrules", "admin"),
        ("internetrules", "assign"),
        ("lessontimes", None),
        ("schoollists", None),
    ]
    # Domanenadministrator auf dem Primary Directory Node
    dc_domainadmin = defaultList + [
        ("udm", "users/user"),
        ("udm", "groups/group"),
        ("udm", "computers/computer"),
        ("schoolwizards", "schoolwizards/schools"),
        ("schoolusers", "student"),
        ("schoolusers", "teacher"),
        ("schoolusers", "staff"),
        ("schoolrooms", None),
        ("schoolgroups", "class"),
        ("schoolgroups", "teacher"),
        ("schoolgroups", "workgroup-admin"),
        ("schoollists", None),
    ]
    # Domanenadministrator auf dem Schul-DC
    dcs_domainadmin = defaultList + [
        ("computerroom", None),
        ("distribution", "admin"),
        ("schoolexam", None),
        ("printermoderation", None),
        ("helpdesk", None),
        ("schoolinstaller", None),
        ("schoolusers", "student"),
        ("schoolusers", "teacher"),
        ("schoolusers", "staff"),
        ("schoolrooms", None),
        ("schoolgroups", "class"),
        ("schoolgroups", "teacher"),
        ("schoolgroups", "workgroup-admin"),
        ("internetrules", "admin"),
        ("internetrules", "assign"),
        ("lessontimes", None),
        ("schoollists", None),
    ]
    checks = {
        ("student", "domaincontroller_master", False): defaultList,
        ("student", "domaincontroller_slave", False): defaultList,
        ("staff", "domaincontroller_master", False): defaultList,
        ("teacher", "domaincontroller_master", False): dc_teacher,
        ("teacher", "domaincontroller_slave", False): dcs_teacher,
        ("schooladmin", "domaincontroller_master", False): dc_schooladmin,
        ("schooladmin", "domaincontroller_slave", False): dcs_schooladmin,
        ("domainadmin", "domaincontroller_master", False): dc_domainadmin,
        ("domainadmin", "domaincontroller_slave", False): dcs_domainadmin,
        ("student", "domaincontroller_master", True): defaultList,
        ("student", "domaincontroller_slave", True): defaultList,
        ("staff", "domaincontroller_master", True): defaultList,
        ("teacher", "domaincontroller_master", True): listUnion(dc_teacher, dcs_teacher),
        ("schooladmin", "domaincontroller_master", True): listUnion(dc_schooladmin, dcs_schooladmin),
        ("domainadmin", "domaincontroller_master", True): listUnion(dc_domainadmin, dcs_domainadmin),
    }
    modules = removeListFromOther(modules, ignoreList)
    res = checks[(userType, serverRole, singleMaster)]
    expected = set(modules)
    found = set(res)
    if userType != "domainadmin":
        success = expected == found
    else:
        success = contains(modules, res)
    if not success:
        raise AssertionError(
            'Modules for "%r" are not correct.\nExpected, but missing: %r\nNot expected:    %r'
            % ((userType, serverRole, singleMaster), expected - found, found - expected)
        )


def test_available_umc_modules(schoolenv, udm_session, ucr):
    udm = udm_session
    host = ucr.get("hostname")
    serverRole = ucr.get("server/role")
    print("Role = {!r}".format(serverRole))
    singleMaster = ucr.is_true("ucsschool/singlemaster", False)
    basedn = ucr.get("ldap/base")

    # Create ou, teacher, student, staff member, schooladmin, domainadmin
    school, oudn = schoolenv.create_ou(name_edudc=host)
    users = []

    tea, teadn = schoolenv.create_user(school, is_teacher=True)
    users.append((tea, "teacher"))

    # staff is not replicated to login to Replica Directory Node
    if serverRole != "domaincontroller_slave":
        staf, stafdn = schoolenv.create_user(school, is_staff=True)
        users.append((staf, "staff"))

    stu, studn = schoolenv.create_user(school)
    users.append((stu, "student"))

    position = "cn=admins,cn=users,ou=%s,%s" % (school, basedn)
    groups = ["cn=admins-%s,cn=ouadmins,cn=groups,%s" % (school, basedn)]
    dn, schooladmin = udm.create_user(position=position, groups=groups)
    users.append((schooladmin, "schooladmin"))

    groups = ["cn=Domain Admins,cn=groups,%s" % (basedn,)]
    dn, domainadmin = udm.create_user(position=position, groups=groups)
    users.append((domainadmin, "domainadmin"))

    utils.wait_for_replication_and_postrun()
    for user, userType in users:
        client = Client(host, user, "univention")
        print("usertype={!r}".format(userType))
        modules = client.umc_get("modules").data["modules"]
        modules = [(x["id"], x.get("flavor")) for x in modules]
        print("modules = {!r}".format(modules))
        checkModules(modules, userType, serverRole, singleMaster)
