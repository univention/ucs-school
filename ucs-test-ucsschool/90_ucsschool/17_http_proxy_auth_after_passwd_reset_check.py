#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: http_proxy_auth_after_passwd_reset_check
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave, memberserver]
## versions:
##  4.0-0: skip
##  4.1-4: fixed
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [univention-samba4, ucs-school-webproxy]


from functools import wraps

import pycurl

import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu
from univention.config_registry import handler_set, handler_unset
from univention.testing import utils
from univention.testing.ucsschool.simplecurl import SimpleCurl
from univention.testing.umc import Client


class WrongStatusError(Exception):
    pass


def retry_auth(func):
    #  retry to avoid errors due to slow replication
    @wraps(func)
    def decorated(*args):
        utils.retry_on_error(lambda: func(*args), exceptions=(WrongStatusError), retry_count=8, delay=2)

    return decorated


def resetPasswd(host, userdn, flavor, nextLogin):
    print("Resetting password for (%r)" % (userdn,))
    newpassword = uts.random_string()
    options = {"userDN": userdn, "newPassword": newpassword, "nextLogin": nextLogin}
    connection = Client(host)
    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw
    connection.authenticate(admin, passwd)
    assert connection.umc_command("schoolusers/password/reset", options, flavor).result
    utils.wait_for_listener_replication()
    return newpassword


@retry_auth
def authProxy(host, url, name, passwd, authTyp, expected_response):
    auth_text = "basic authentication" if authTyp == 1 else "NTLM authentication"
    print("Performing auth %r check" % (auth_text,))
    curl = SimpleCurl(proxy=host, username=name, password=passwd, auth=authTyp)
    result = curl.response(url)
    if result != expected_response:
        raise WrongStatusError(
            "Proxy %s fails and returns %s, while expected  to return %s"
            % (auth_text, result, expected_response)
        )


def test_http_proxy_auth_after_password_reset_check(restart_services, schedule_restart_services, ucr):
    schedule_restart_services("squid")
    url = "http://www.univention.de"
    host = "%s.%s" % (ucr.get("hostname"), ucr.get("domainname"))
    handler_set(
        [
            "squid/basicauth=yes",
            "squid/basicauth/children=1",
            "squid/ntlmauth=yes",
            "squid/ntlmauth/children=1",
        ]
    )
    handler_unset(["squid/ntlmauth/keepalive"])
    restart_services("squid")
    with utu.UCSTestSchool() as schoolenv:
        school, oudn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
        stu, studn = schoolenv.create_user(school)
        utils.wait_for()

        print("check student auth with initial state")
        authProxy(host, url, stu, "univention", pycurl.HTTPAUTH_BASIC, 200)
        authProxy(host, url, stu, "univention", pycurl.HTTPAUTH_NTLM, 200)

        print("resetting student user password")
        newpasswd = resetPasswd(host, studn, "student", False)
        utils.wait_for()

        print("check student auth with the old password (old password cached)")
        # The old password is cached for 2 hours with basic auth
        # See: squid.conf "auth_param basic credentialsttl"
        authProxy(host, url, stu, "univention", pycurl.HTTPAUTH_BASIC, 200)
        # The old password is cached for 1 minute with ntlm auth
        # See: ucr "squid/ntlmauth/cache/timeout"
        authProxy(host, url, stu, "univention", pycurl.HTTPAUTH_NTLM, 200)

        print("check student auth with the new password")
        authProxy(host, url, stu, newpasswd, pycurl.HTTPAUTH_BASIC, 200)
        authProxy(host, url, stu, newpasswd, pycurl.HTTPAUTH_NTLM, 200)

        print("check student auth with the old password (cache cleared)")
        # Using the new password has cleared the credential cache
        authProxy(host, url, stu, "univention", pycurl.HTTPAUTH_BASIC, 407)
        authProxy(host, url, stu, "univention", pycurl.HTTPAUTH_NTLM, 407)

        tea, teadn = schoolenv.create_user(school, is_teacher=True)
        utils.wait_for()

        print("check teacher auth with initial state")
        authProxy(host, url, tea, "univention", pycurl.HTTPAUTH_BASIC, 200)
        authProxy(host, url, tea, "univention", pycurl.HTTPAUTH_NTLM, 200)

        print("resetting teacher user password")
        newpasswd = resetPasswd(host, teadn, "teacher", False)
        utils.wait_for()

        print("check teacher auth with the old password (old password cached)")
        # The old password is cached for 2 hours with basic auth
        # See: squid.conf "auth_param basic credentialsttl"
        authProxy(host, url, tea, "univention", pycurl.HTTPAUTH_BASIC, 200)
        # The old password is cached for 1 minute with ntlm auth
        # See: ucr "squid/ntlmauth/cache/timeout"
        authProxy(host, url, tea, "univention", pycurl.HTTPAUTH_NTLM, 200)

        print("check teacher auth with the new password")
        authProxy(host, url, tea, newpasswd, pycurl.HTTPAUTH_BASIC, 200)
        authProxy(host, url, tea, newpasswd, pycurl.HTTPAUTH_NTLM, 200)

        print("check teacher auth with the old password (cache cleared)")
        # Using the new password has cleared the credential cache
        authProxy(host, url, tea, "univention", pycurl.HTTPAUTH_BASIC, 407)
        authProxy(host, url, tea, "univention", pycurl.HTTPAUTH_NTLM, 407)
