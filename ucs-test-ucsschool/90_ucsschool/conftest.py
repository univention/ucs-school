try:
	from typing import List
except ImportError:
	pass
import pytest
from univention.testing import ucr as _ucr, udm as _udm, utils, umc, strings
import univention.testing.ucsschool.ucs_test_school as utu
from ucsschool.lib.authorization import Capability, ContextRole, RoleCapability


@pytest.fixture
def schoolenv():
	with utu.UCSTestSchool() as schoolenv:
		yield schoolenv


@pytest.fixture(scope="session")
def ucr():
	with _ucr.UCSTestConfigRegistry() as ucr:
		yield ucr


@pytest.fixture
def udm():
	with _udm.UCSTestUDM() as udm:
		yield udm


@pytest.fixture(scope="session")
def hostname(ucr):
	return ucr["hostname"]


@pytest.fixture(scope="session")
def ldap_base(ucr):
	return ucr["ldap/base"]


@pytest.fixture(scope="session")
def capability_create_class_list():  # type: () -> RoleCapability
	return RoleCapability.from_udm_role_prop([Capability.CREATE_CLASS_LIST.value])


@pytest.fixture(scope="session")
def capability_pw_reset_student():  # type: () -> RoleCapability
	return RoleCapability.from_udm_role_prop([Capability.PASSWORD_RESET.value, "student"])


@pytest.fixture(scope="session")
def context_role():
	def _func(role_name, capabilities, ou):
		# type: (str, List[RoleCapability], str) -> ContextRole
		return ContextRole(
			role_name,
			"ContextRole for {} at {}".format(role_name, ou),
			capabilities,
			ou,
			"school"
		)
	return _func
