import os

import pytest

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm as udm_test

try:
    from typing import Any, Dict, Optional, Tuple
    from ucsschool.lib.models.base import LoType
except ImportError:
    pass


@pytest.fixture(scope="session")
def random_username():
    return uts.random_username


@pytest.fixture(scope="session")
def ucr():
    """Instance of UCSTestConfigRegistry"""
    with ucr_test.UCSTestConfigRegistry() as ucr:
        yield ucr


@pytest.fixture(scope="session")
def fqdn(ucr):
    """hostname.domainname"""
    ret = os.environ.get("UCS_TEST_HOSTNAME")
    return ret or "{hostname}.{domainname}".format(**ucr)


@pytest.fixture(scope="session")
def admin_username(ucr):
    """Username of the Admin account"""
    ret = os.environ.get("UCS_TEST_ADMIN_USERNAME")
    if not ret:
        ret = ucr.get("tests/domainadmin/account")
        if ret:
            ret = ret.split(",")[0].split("=")[-1]
        else:
            ret = "Administrator"
    return ret


@pytest.fixture(scope="session")
def admin_password(ucr):
    """Password of the Admin account"""
    ret = os.environ.get("UCS_TEST_ADMIN_PASSWORD")
    return ret or ucr.get("tests/domainadmin/pwd", "univention")


@pytest.fixture
def schoolenv():
    with utu.UCSTestSchool() as _schoolenv:
        yield _schoolenv


@pytest.fixture
def create_ou(schoolenv, ucr_hostname):
    def _func(**kwargs):  # type: (**Any) -> Tuple[str, str]
        kwargs["name_edudc"] = kwargs.get("name_edudc") or ucr_hostname
        return schoolenv.create_ou(**kwargs)

    return _func


@pytest.fixture
def lo(schoolenv):
    return schoolenv.lo


@pytest.fixture(scope="session")
def udm_session():
    with udm_test.UCSTestUDM() as udm:
        yield udm


@pytest.fixture(scope="session")
def mail_domain(udm_session, ucr_domainname, ucr, ucr_ldap_base):
    if ucr_domainname not in ucr.get("mail/hosteddomains", "").split():
        udm_session.create_object(
            "mail/domain",
            set={"name": ucr_domainname},
            position="cn=domain,cn=mail,{}".format(ucr_ldap_base),
        )

    return ucr_domainname


@pytest.fixture(scope="session")
def ucr_domainname(ucr):
    return ucr["domainname"]


@pytest.fixture(scope="session")
def ucr_hostname(ucr):
    return ucr["hostname"]


@pytest.fixture(scope="session")
def ucr_is_singlemaster(ucr):
    return ucr.is_true("ucsschool/singlemaster", False)


@pytest.fixture(scope="session")
def ucr_ldap_base(ucr):
    return ucr["ldap/base"]


@pytest.fixture(scope="session")
def workgroup_ldap_attributes(mail_domain, random_username, ucr_ldap_base):
    def _func(ou):  # type: (str) -> Dict[str, Any]
        name = random_username()
        group_dn = "cn={0}-{1},cn=schueler,cn=groups,ou={0},{2}".format(ou, name, ucr_ldap_base)
        user_name = "demo_student"
        user_dn = "uid={},cn=schueler,cn=users,ou={},{}".format(user_name, ou, ucr_ldap_base)
        return {
            "cn": ["{}-{}".format(ou, name)],
            "description": ["{} {}".format(random_username(), random_username())],
            "mailPrimaryAddress": ["wg-{}@{}".format(name, mail_domain)],
            "memberUid": [user_name],
            "objectClass": ["sambaGroupMapping", "ucsschoolGroup"],
            "ucsschoolRole": ["workgroup:school:{}".format(ou)],
            "univentionAllowedEmailGroups": [group_dn],
            "univentionAllowedEmailUsers": [user_dn],
            "uniqueMember": [user_dn],
            "univentionObjectType": ["groups/group"],
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_school_attributes(workgroup_ldap_attributes):
    def _func(ou, ldap_attrs=None):  # type: (str, Optional[Dict[str, Any]]) -> Dict[str, Any]
        attrs = ldap_attrs or workgroup_ldap_attributes(ou)
        return {
            "name": attrs["cn"][0],
            "description": attrs["description"][0],
            "email": attrs["mailPrimaryAddress"][0],
            "allowed_email_senders_users": attrs["univentionAllowedEmailUsers"],
            "allowed_email_senders_groups": attrs["univentionAllowedEmailGroups"],
            "school": ou,
            "ucsschool_roles": attrs["ucsschoolRole"],
            "users": attrs["uniqueMember"],
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_share_ldap_attributes(random_username, ucr_domainname, ucr_hostname, ucr_ldap_base):
    def _func(ou):  # type: (str) -> Dict[str, Any]
        name = random_username()
        if ucr_is_singlemaster:
            share_host = "{}.{}".format(ucr_hostname, ucr_domainname)
        else:
            share_host = "dc{}-01.{}".format(ou, ucr_domainname)
        return {
            "cn": ["{}-{}".format(ou, name)],
            "objectClass": ["ucsschoolShare", "univentionShareSamba"],
            "ucsschoolRole": ["workgroup_share:school:{}".format(ou)],
            "univentionObjectType": ["shares/share"],
            "univentionShareDirectoryMode": ["0770"],
            "univentionShareHost": [share_host],
            "univentionSharePath": ["/home/{0}/groups/{0}-{1}".format(ou, name)],
            "univentionShareSambaBrowseable": "yes",
            "univentionShareSambaCreateMode": "0770",
            "univentionShareSambaDirectoryMode": "0770",
            "univentionShareSambaForceGroup": "+{}-{}".format(ou, name),
            "univentionShareSambaName": "{}-{}".format(ou, name),
            "univentionShareSambaNtAclSupport": "1",
            "univentionShareSambaWriteable": "yes",
        }

    return _func


@pytest.fixture(scope="session")
def workgroup_share_school_attributes(workgroup_share_ldap_attributes):
    def _func(ou, ldap_attrs=None):  # type: (str, Optional[Dict[str, Any]]) -> Dict[str, Any]
        attrs = ldap_attrs or workgroup_share_ldap_attributes(ou)
        return {
            "name": attrs["cn"][0],
            "school": ou,
            "ucsschool_roles": attrs["ucsschoolRole"],
        }

    return _func
