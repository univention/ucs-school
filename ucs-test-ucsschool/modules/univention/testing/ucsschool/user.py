"""
.. module:: user
    :platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""

from __future__ import print_function

import contextlib
from typing import Any, Dict  # noqa: F401

import univention.testing.ucr as ucr_test
from ucsschool.lib.roles import create_ucsschool_role_string, role_staff, role_student, role_teacher
from univention.lib.umc import BadRequest
from univention.testing import utils
from univention.testing.ucsschool.importusers import Person
from univention.testing.umc import Client


class User(Person):
    """
    Contains the needed functuality for users in the UMC module schoolwizards/users.\n
    :param school: school name of the user
    :type school: str
    :param role: role of the user
    :type role: str ['student', 'teacher', 'staff', 'teacherAndStaff']
    :param school_classes: dictionary of school -> list of names of the class which contain the user
    :type school_classes: dict
    :param workgroups: dictionary of school -> list of names of the workgroups which contain the user
    :type workgroups: dict
    """

    def __init__(
        self,
        school,
        role,
        school_classes,
        workgroups=None,
        mode="A",
        username=None,
        firstname=None,
        lastname=None,
        password=None,
        mail=None,
        expiration_date=None,
        schools=None,
        connection=None,
        birthday=None,
    ):
        super(User, self).__init__(school, role)

        if username:
            self.username = username
            self.dn = self.make_dn()
        if firstname:
            self.firstname = firstname
        if lastname:
            self.lastname = lastname
        if mail:
            self.mail = mail
        if expiration_date:
            self.expiration_date = expiration_date
        if school_classes:
            self.school_classes = school_classes
        self.schools = schools or [self.school]
        self.typ = "teachersAndStaff" if self.role == "teacher_staff" else self.role
        self.mode = mode
        self.birthday = birthday
        self.workgroups = workgroups or {}

        utils.wait_for_replication()
        self.ucr = ucr_test.UCSTestConfigRegistry()
        self.ucr.load()
        self.client = connection or Client.get_test_connection(self.ucr.get("ldap/master"))
        account = utils.UCSTestDomainAdminCredentials()
        passwd = account.bindpw
        self.password = password or passwd

    def append_random_groups(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, trace_back):
        self.ucr.revert_to_original_registry()

    def create(self):
        """Creates object user"""
        flavor = "schoolwizards/users"
        param = [
            {
                "object": {
                    "school": self.school,
                    "schools": self.schools,
                    "school_classes": self.school_classes,
                    "workgroups": self.workgroups,
                    "email": self.mail,
                    "expiration_date": self.expiration_date,
                    "name": self.username,
                    "type": self.typ,
                    "firstname": self.firstname,
                    "lastname": self.lastname,
                    "password": self.password,
                },
                "options": None,
            }
        ]
        print("#### Creating user %s" % (self.username,))
        print("#### param = %s" % (param,))
        reqResult = self.client.umc_command("schoolwizards/users/add", param, flavor).result
        assert reqResult[0] is True, "Unable to create user (%r): %r" % (param, reqResult[0])
        utils.wait_for_replication()

    def get(self):  # type: () -> Dict[str, Any]
        """Get user"""
        flavor = "schoolwizards/users"
        param = [{"object": {"$dn$": self.dn, "school": self.school}}]
        try:
            reqResult = self.client.umc_command("schoolwizards/users/get", param, flavor).result
        except BadRequest as exc:
            if exc.status == 400:
                reqResult = [""]
            else:
                raise
        assert reqResult[0], "Unable to get user (%s): %r" % (self.username, reqResult[0])
        return reqResult[0]

    def check_get(self, expected_attrs=None):
        info = {
            "$dn$": self.dn,
            "display_name": " ".join([self.firstname, self.lastname]),
            "name": self.username,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "type_name": self.type_name(),
            "school": self.school,
            "schools": set(self.schools),
            "disabled": "0",
            "birthday": None,
            "password": None,
            "type": self.typ,
            "email": self.mail,
            "expiration_date": self.expiration_date,
            "objectType": "users/user",
            "school_classes": {},
            "workgroups": self.workgroups,
            "ucsschool_roles": set(self.ucsschool_roles),
        }
        if self.is_student() or self.is_teacher() or self.is_teacher_staff():
            info["school_classes"] = self.school_classes

        if expected_attrs:
            info.update(expected_attrs)

        get_result = self.get()
        # Type_name is only used for display, Ignored
        info["type_name"] = get_result["type_name"]
        # ignore order
        get_result["schools"] = set(get_result["schools"])
        get_result["ucsschool_roles"] = set(get_result["ucsschool_roles"])
        diff = []
        if get_result != info:
            for key in set(get_result.keys()) | set(info.keys()):
                result_value = get_result.get(key)
                info_value = info.get(key)
                if key in ("school_classes", "workgroups"):
                    result_value = {k: set(v) for k, v in result_value.items()}
                    info_value = {k: set(v) for k, v in info_value.items()}
                if result_value != info_value:
                    diff.append("%s: Got:\n%r; expected:\n%r" % (key, result_value, info_value))
        assert get_result == info, "Failed get request for user %s:\n%s" % (
            self.username,
            "\n".join(diff),
        )

    @property
    def ucsschool_roles(self):
        roles = {
            "staff": [role_staff],
            "student": [role_student],
            "teacher": [role_teacher],
            "teacherAndStaff": [role_staff, role_teacher],
            "teachersAndStaff": [role_staff, role_teacher],  # TODO: fix inconsistency
        }
        ret = []
        for school in set([self.school] + self.schools):
            ret.extend([create_ucsschool_role_string(role, school) for role in roles[self.typ]])
        return ret

    def type_name(self):
        if self.typ == "student":
            return "Student"
        elif self.typ == "teacher":
            return "Teacher"
        elif self.typ == "staff":
            return "Staff"
        elif self.typ in ("teacherAndStaff", "teachersAndStaff"):  # TODO: fix inconsistency
            return "Teacher and Staff"

    def query(self):
        """get the list of existing users in the school"""
        flavor = "schoolwizards/users"
        param = {"school": self.school, "type": "all", "filter": ""}
        return self.client.umc_command("schoolwizards/users/query", param, flavor).result

    def check_query(self, users_dn):
        q = self.query()
        k = [x["$dn$"] for x in q]
        assert set(users_dn).issubset(
            set(k)
        ), "users from query do not contain the existing users, found (%r), expected (%r)" % (
            k,
            users_dn,
        )

    def remove(self, remove_from_school=None):
        """Remove user"""
        remove_from_school = remove_from_school or self.school
        print(
            "#### Removing User %r (%s) from school %r." % (self.username, self.dn, remove_from_school)
        )
        flavor = "schoolwizards/users"
        param = [
            {"object": {"remove_from_school": remove_from_school, "$dn$": self.dn}, "options": None}
        ]
        reqResult = self.client.umc_command("schoolwizards/users/remove", param, flavor).result
        assert reqResult[0], "Unable to remove user (%r): %r" % (self.username, reqResult[0])
        schools = self.schools[:]
        schools.remove(remove_from_school)
        if not schools:
            self.set_mode_to_delete()
        else:
            self.update(school=sorted(schools)[0], schools=schools, mode="M")
            with contextlib.suppress(KeyError):
                del self.school_classes[remove_from_school]
            with contextlib.suppress(KeyError):
                del self.workgroups[remove_from_school]

    def edit(self, new_attributes):
        """Edit object user"""
        flavor = "schoolwizards/users"
        object_props = {
            "school": self.school,
            "schools": self.schools,
            "email": new_attributes.get("email") or self.mail,
            "expiration_date": new_attributes.get("expiration_date") or self.expiration_date,
            "name": self.username,
            "type": self.typ,
            "firstname": new_attributes.get("firstname") or self.firstname,
            "lastname": new_attributes.get("lastname") or self.lastname,
            "password": new_attributes.get("password") or self.password,
            "$dn$": self.dn,
            "workgroups": new_attributes.get("workgroups") or self.workgroups,
        }
        if self.typ not in ("teacher", "staff", "teacherAndStaff"):
            object_props["school_classes"] = new_attributes.get("school_classes", self.school_classes)

        param = [{"object": object_props, "options": None}]
        print("#### Editing user %s" % (self.username,))
        print("#### param = %s" % (param,))
        reqResult = self.client.umc_command("schoolwizards/users/put", param, flavor).result
        assert reqResult[0] is True, "Unable to edit user (%s) with the parameters (%r) : %r" % (
            self.username,
            param,
            reqResult[0],
        )
        self.set_mode_to_modify()
        self.school_classes = new_attributes.get("school_classes", self.school_classes)
        self.workgroups = new_attributes.get("workgroups", self.workgroups)
        self.mail = new_attributes.get("email") or self.mail
        self.expiration_date = new_attributes.get("expiration_date") or self.expiration_date
        self.firstname = new_attributes.get("firstname") or self.firstname
        self.lastname = new_attributes.get("lastname") or self.lastname
        self.password = new_attributes.get("password") or self.password
