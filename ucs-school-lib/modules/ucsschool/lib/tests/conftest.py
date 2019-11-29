import json
import random
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pytest
from faker import Faker
from univention.admin.client import UDM
from univention.admin.modules import ConnectionData

REMOTE_CODE_MODULE_NAME = "remote_code"
REMOTE_CODE_FILE_PATH = Path(__file__).parent / f"{REMOTE_CODE_MODULE_NAME}.py"

fake = Faker()


@pytest.fixture(scope="module")
def run_cmd() -> Callable[[List[str]], Tuple[str, int]]:
	def _func(cmd):  # type: (List[str]) -> Tuple[str, int]
		print("Running command:\n{}".format(cmd))
		process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()
		print('Exit code {!r}.'.format(process.returncode))
		print('Stdout: {}'.format(stdout.strip()))
		print('Stderr: {}'.format(stderr.strip()))
		return stdout.strip().decode(), process.returncode
	return _func


@pytest.fixture(scope="module")
def lo_udm():  # type: () -> UDM
	return UDM.http(
		uri=ConnectionData.uri(),
		username=ConnectionData.ldap_machine_account_username(),
		password=ConnectionData.machine_password()
	)


@pytest.fixture(scope="module")
def scp_code(run_cmd):  # type: (Callable) -> Tuple[str, int]
	server = ConnectionData.ldap_server_name()
	return run_cmd(["scp", str(REMOTE_CODE_FILE_PATH), "root@{}:/tmp".format(server)])


@pytest.fixture(scope="module")
def send_cmd_through_ssh(run_cmd):  # type: (Callable) -> Callable[[str], Tuple[str, int]]
	def _func(cmd: str) -> Tuple[str, int]:
		server = ConnectionData.ldap_server_name()
		return run_cmd(["ssh", "root@{}".format(server), cmd])
	return _func


@pytest.fixture
def school_class_attrs():  # type: () -> Dict[str, str]
	def _func():  # type: () -> Dict[str, str]
		return {
			"name": fake.name().replace(" ", ".").lower(),
			"school": "DEMOSCHOOL",
			"description": fake.text(max_nb_chars=50),
			"users": [
				"uid={}.{},{}".format(fake.first_name(), fake.last_name(), ConnectionData.ldap_base()),
				"uid={}.{},{}".format(fake.first_name(), fake.last_name(), ConnectionData.ldap_base()),
			],
		}
	return _func()


@pytest.fixture
def new_school_class_via_ssh(scp_code, send_cmd_through_ssh, school_class_attrs) -> Tuple[str, Dict[str, str]]:
	def _func() -> Tuple[str, Dict[str, str]]:
		cmd = 'cd /tmp; python -c "from {module} import create_school_class; create_school_class({kwargs})"'.format(
			module=REMOTE_CODE_MODULE_NAME,
			kwargs=", ".join(["{}={!r}".format(k, v) for k, v in school_class_attrs.items()])
		)
		dn, returncode = send_cmd_through_ssh(cmd)
		assert returncode == 0
		print("new_school_class_via_ssh() DN: {!r}".format(dn))
		return dn, school_class_attrs
	return _func()


@pytest.fixture
def get_school_class_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[Dict[str, Any], int]]:
	def _func(dn: str) -> Tuple[Dict[str, Any], int]:
		cmd = 'cd /tmp; python -c "from {module} import school_class_to_dict; school_class_to_dict({kwargs})"'.format(
			module=REMOTE_CODE_MODULE_NAME,
			kwargs=repr(dn)
		)
		result, returncode = send_cmd_through_ssh(cmd)
		result_d = json.loads(result)
		return result_d, returncode
	return _func


@pytest.fixture
def school_class_exists_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[bool, int]]:
	def _func(dn: str) -> Tuple[bool, int]:
		cmd = 'cd /tmp; python -c "from {module} import school_class_exits; school_class_exits({kwargs})"'.format(
			module=REMOTE_CODE_MODULE_NAME,
			kwargs=repr(dn)
		)
		result, returncode = send_cmd_through_ssh(cmd)
		if result == "True":
			result_b = True
		elif result == "False":
			result_b = False
		else:
			raise RuntimeError("Unknown result from school_class_exists_via_ssh({!r}): {!r}".format(dn, result))
		return result_b, returncode
	return _func


@pytest.fixture
def remove_class_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[str, int]]:
	def _func(dn: str) -> Tuple[str, int]:
		cmd = 'cd /tmp; python -c "from {module} import remove_school_class; remove_school_class({kwargs})"'.format(
			module=REMOTE_CODE_MODULE_NAME,
			kwargs=repr(dn)
		)
		result, returncode = send_cmd_through_ssh(cmd)
		return result, returncode
	return _func


@pytest.fixture
def user_attrs():  # type: () -> Dict[str, str]
	# TODO: support specifying role
	def _func():  # type: () -> Dict[str, str]
		user_cls = random.choice(("Staff", "Student", "Teacher", "TeachersAndStaff"))  # "ExamStudent" ?
		res = {
			"name": fake.name().replace(" ", ".").lower(),
			"school": "DEMOSCHOOL",
			"firstname": fake.first_name(),
			"lastname": fake.last_name(),
			'birthday': fake.date_of_birth(minimum_age=6, maximum_age=65).strftime("%Y-%m-%d"),
			'email': None,
			'password': None,
			'disabled': False,
			"user_cls": user_cls,
		}
		if user_cls == "Staff":
			res["school_classes"] = {}
		else:
			res["school_classes"] = {
				'DEMOSCHOOL': [f'DEMOSCHOOL-{fake.first_name()}', f'DEMOSCHOOL-{fake.first_name()}'],
			}
		return res
	return _func()


@pytest.fixture
def new_user_via_ssh(scp_code, send_cmd_through_ssh, user_attrs) -> Tuple[str, Dict[str, str]]:
	# TODO: support multiple roles
	def _func() -> Tuple[str, Dict[str, str]]:
		cmd = 'cd /tmp; python -c "from {module} import create_user; create_user({kwargs})"'.format(
			module=REMOTE_CODE_MODULE_NAME,
			kwargs=", ".join(["{}={!r}".format(k, v) for k, v in user_attrs.items()])
		)
		dn, returncode = send_cmd_through_ssh(cmd)
		assert returncode == 0
		print("new_user_via_ssh() DN: {!r}".format(dn))
		return dn, user_attrs
	return _func()


@pytest.fixture
def remove_user_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[str, int]]:
	def _func(dn: str) -> Tuple[str, int]:
		cmd = 'cd /tmp; python -c "from {module} import remove_user; remove_user({kwargs})"'.format(
			module=REMOTE_CODE_MODULE_NAME,
			kwargs=repr(dn)
		)
		result, returncode = send_cmd_through_ssh(cmd)
		return result, returncode
	return _func


@pytest.fixture
def get_user_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[Dict[str, Any], int]]:
	def _func(dn: str) -> Tuple[Dict[str, Any], int]:
		cmd = 'cd /tmp; python -c "from {module} import user_to_dict; user_to_dict({kwargs})"'.format(
			module=REMOTE_CODE_MODULE_NAME,
			kwargs=repr(dn)
		)
		result, returncode = send_cmd_through_ssh(cmd)
		result_d = json.loads(result)
		return result_d, returncode
	return _func


@pytest.fixture
def user_exists_via_ssh(send_cmd_through_ssh) -> Callable[[str], Tuple[bool, int]]:
	def _func(dn: str) -> Tuple[bool, int]:
		cmd = 'cd /tmp; python -c "from {module} import user_exits; user_exits({kwargs})"'.format(
			module=REMOTE_CODE_MODULE_NAME,
			kwargs=repr(dn)
		)
		result, returncode = send_cmd_through_ssh(cmd)
		if result == "True":
			result_b = True
		elif result == "False":
			result_b = False
		else:
			raise RuntimeError("Unknown result from user_exists_via_ssh({!r}): {!r}".format(dn, result))
		return result_b, returncode
	return _func
