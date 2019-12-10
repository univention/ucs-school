import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest
from faker import Faker
from univention.config_registry import ConfigRegistry

from udm_rest_client import UDM, NoObject as UdmNoObject

APP_ID = "ucsschool-kelvin"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = APP_BASE_PATH / "conf"
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"
UCS_SSL_CA_CERT = "/usr/local/share/ca-certificates/ucs.crt"

fake = Faker()


@lru_cache(maxsize=1)
def ucr() -> ConfigRegistry:
    ucr = ConfigRegistry()
    ucr.load()
    return ucr


@lru_cache(maxsize=32)
def env_or_ucr(key: str) -> str:
    try:
        return os.environ[key.replace("/", "_").upper()]
    except KeyError:
        return ucr()[key]


@pytest.fixture(scope="session")
def ldap_base():
    return env_or_ucr("ldap/base")


@pytest.fixture(scope="session")
def udm_kwargs() -> Dict[str, Any]:
    with open(CN_ADMIN_PASSWORD_FILE, "r") as fp:
        cn_admin_password = fp.read().strip()
    host = env_or_ucr("ldap/master")
    return {
        "username": "cn=admin",
        "password": cn_admin_password,
        "url": f"https://{host}/univention/udm/",
        "ssl_ca_cert": UCS_SSL_CA_CERT,
    }


@pytest.fixture
def school_class_attrs(ldap_base):
    def _func() -> Dict[str, str]:
        return {
            "name": fake.user_name(),
            "school": "DEMOSCHOOL",
            "description": fake.text(max_nb_chars=50),
            "users": [
                f"uid={fake.user_name()},cn=users,{ldap_base}",
                f"uid={fake.user_name()},cn=users,{ldap_base}",
            ],
        }

    return _func


@pytest.fixture
async def new_school_class(udm_kwargs, ldap_base, school_class_attrs):
    created_school_classes = []
    created_school_shares = []

    async def _func() -> Tuple[str, Dict[str, str]]:
        async with UDM(**udm_kwargs) as udm:
            sc_attrs = school_class_attrs()
            grp_obj = await udm.get("groups/group").new()
            grp_obj.position = f"cn=klassen,cn=schueler,cn=groups,ou={sc_attrs['school']},{ldap_base}"
            grp_obj.props.name = (
                f"{sc_attrs['school']}-{sc_attrs['name']}"
            )
            grp_obj.props.description = sc_attrs["description"]
            grp_obj.props.users = sc_attrs["users"]
            await grp_obj.save()
            created_school_classes.append(grp_obj.dn)
            print("Created new SchoolClass: {!r}".format(grp_obj))

            share_obj = await udm.get("shares/share").new()
            share_obj.position = (
                f"cn=klassen,cn=shares,ou={sc_attrs['school']},{ldap_base}"
            )
            share_obj.props.name = grp_obj.props.name
            share_obj.props.host = (
                f"{sc_attrs['school']}.{env_or_ucr('domainname')}"
            )
            share_obj.props.owner = 0
            share_obj.props.group = 0
            share_obj.props.path = f"/home/tmp/{grp_obj.props.name}"
            share_obj.props.directorymode = "0770"
            await share_obj.save()
            created_school_shares.append(share_obj.dn)
            print("Created new ClassShare: {!r}".format(share_obj))

        return grp_obj.dn, sc_attrs

    yield _func

    async with UDM(**udm_kwargs) as udm:
        grp_mod = udm.get("groups/group")
        for dn in created_school_classes:
            try:
                grp_obj = await grp_mod.get(dn)
            except UdmNoObject:
                print(f"SchoolClass {dn!r} does not exist (anymore).")
                continue
            await grp_obj.delete()
            print(f"Deleted SchoolClass {dn!r}.")
        share_mod = udm.get("shares/share")
        for dn in created_school_shares:
            try:
                share_obj = await share_mod.get(dn)
            except UdmNoObject:
                print(f"ClassShare {dn!r} does not exist (anymore).")
                continue
            await share_obj.delete()
            print(f"Deleted ClassShare {dn!r}.")


# @pytest.fixture
# def get_school_class_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[Dict[str, Any], int]]:
# 	def _func(dn: str) -> Tuple[Dict[str, Any], int]:
# 		cmd = 'cd /tmp; python -c "from {module} import school_class_to_dict; school_class_to_dict({kwargs})"'.format(
# 			module=REMOTE_CODE_MODULE_NAME,
# 			kwargs=repr(dn)
# 		)
# 		result, returncode = send_cmd_through_ssh(cmd)
# 		result_d = json.loads(result)
# 		return result_d, returncode
# 	return _func
#
#
# @pytest.fixture
# def school_class_exists_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[bool, int]]:
# 	def _func(dn: str) -> Tuple[bool, int]:
# 		cmd = 'cd /tmp; python -c "from {module} import school_class_exits; school_class_exits({kwargs})"'.format(
# 			module=REMOTE_CODE_MODULE_NAME,
# 			kwargs=repr(dn)
# 		)
# 		result, returncode = send_cmd_through_ssh(cmd)
# 		if result == "True":
# 			result_b = True
# 		elif result == "False":
# 			result_b = False
# 		else:
# 			raise RuntimeError("Unknown result from school_class_exists_via_ssh({!r}): {!r}".format(dn, result))
# 		return result_b, returncode
# 	return _func
#
#
# @pytest.fixture
# def remove_class_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[str, int]]:
# 	def _func(dn: str) -> Tuple[str, int]:
# 		cmd = 'cd /tmp; python -c "from {module} import remove_school_class; remove_school_class({kwargs})"'.format(
# 			module=REMOTE_CODE_MODULE_NAME,
# 			kwargs=repr(dn)
# 		)
# 		result, returncode = send_cmd_through_ssh(cmd)
# 		return result, returncode
# 	return _func
#
#
# @pytest.fixture
# def user_attrs():  # type: () -> Dict[str, str]
# 	# TODO: support specifying role
# 	def _func():  # type: () -> Dict[str, str]
# 		user_cls = random.choice(("Staff", "Student", "Teacher", "TeachersAndStaff"))  # "ExamStudent" ?
# 		res = {
# 			"name": fake.name().replace(" ", ".").lower(),
# 			"school": "DEMOSCHOOL",
# 			"firstname": fake.first_name(),
# 			"lastname": fake.last_name(),
# 			'birthday': fake.date_of_birth(minimum_age=6, maximum_age=65).strftime("%Y-%m-%d"),
# 			'email': None,
# 			'password': None,
# 			'disabled': False,
# 			"user_cls": user_cls,
# 		}
# 		if user_cls == "Staff":
# 			res["school_classes"] = {}
# 		else:
# 			res["school_classes"] = {
# 				'DEMOSCHOOL': [f'DEMOSCHOOL-{fake.first_name()}', f'DEMOSCHOOL-{fake.first_name()}'],
# 			}
# 		return res
# 	return _func()
#
#
# @pytest.fixture
# def new_user_via_ssh(scp_code, send_cmd_through_ssh, user_attrs) -> Tuple[str, Dict[str, str]]:
# 	# TODO: support multiple roles
# 	def _func() -> Tuple[str, Dict[str, str]]:
# 		cmd = 'cd /tmp; python -c "from {module} import create_user; create_user({kwargs})"'.format(
# 			module=REMOTE_CODE_MODULE_NAME,
# 			kwargs=", ".join(["{}={!r}".format(k, v) for k, v in user_attrs.items()])
# 		)
# 		dn, returncode = send_cmd_through_ssh(cmd)
# 		assert returncode == 0
# 		print("new_user_via_ssh() DN: {!r}".format(dn))
# 		return dn, user_attrs
# 	return _func()
#
#
# @pytest.fixture
# def remove_user_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[str, int]]:
# 	def _func(dn: str) -> Tuple[str, int]:
# 		cmd = 'cd /tmp; python -c "from {module} import remove_user; remove_user({kwargs})"'.format(
# 			module=REMOTE_CODE_MODULE_NAME,
# 			kwargs=repr(dn)
# 		)
# 		result, returncode = send_cmd_through_ssh(cmd)
# 		return result, returncode
# 	return _func
#
#
# @pytest.fixture
# def get_user_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[Dict[str, Any], int]]:
# 	def _func(dn: str) -> Tuple[Dict[str, Any], int]:
# 		cmd = 'cd /tmp; python -c "from {module} import user_to_dict; user_to_dict({kwargs})"'.format(
# 			module=REMOTE_CODE_MODULE_NAME,
# 			kwargs=repr(dn)
# 		)
# 		result, returncode = send_cmd_through_ssh(cmd)
# 		result_d = json.loads(result)
# 		return result_d, returncode
# 	return _func
#
#
# @pytest.fixture
# def user_exists_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[bool, int]]:
# 	def _func(dn: str) -> Tuple[bool, int]:
# 		cmd = 'cd /tmp; python -c "from {module} import user_exits; user_exits({kwargs})"'.format(
# 			module=REMOTE_CODE_MODULE_NAME,
# 			kwargs=repr(dn)
# 		)
# 		result, returncode = send_cmd_through_ssh(cmd)
# 		if result == "True":
# 			result_b = True
# 		elif result == "False":
# 			result_b = False
# 		else:
# 			raise RuntimeError("Unknown result from user_exists_via_ssh({!r}): {!r}".format(dn, result))
# 		return result_b, returncode
# 	return _func
