#!/usr/share/ucs-test/runner python
## desc: Test S4 SRV record maintainance
## roles: [domaincontroller_slave]
## tags: [apptest]
## exposure: dangerous
## packages:
##    - ucs-school-s4-branch-site
##    - univention-samba | univention-samba4

import os
import sys
sys.dont_write_bytecode = True
import subprocess
import time
from univention.testing.codes import TestCodes
import univention.testing.utils as testing_utils
from univention import testing
import univention.testing.ucr as testing_ucr
import univention.testing.udm as testing_udm
from univention.admin.uldap import explodeDn
from ucsschool.lib.schoolldap import get_all_local_searchbases, set_credentials
import univention.testing.strings as uts
import univention.config_registry

try:
	from univention.testing.ucs_samba import wait_for_drs_replication
except ImportError:
	def wait_for_drs_replication(ldap_filter, attrs=None):
		pass

### Initialize globals
ucr = testing_ucr.UCSTestConfigRegistry()
ucr.load()
TESTS_DOMAINADMIN_ACCOUNT = ucr.get('tests/domainadmin/account')
if TESTS_DOMAINADMIN_ACCOUNT:
	TESTS_DOMAINADMIN = explodeDn(TESTS_DOMAINADMIN_ACCOUNT, 1)[0]
TESTS_DOMAINADMIN_PWD = ucr.get('tests/domainadmin/pwd')
set_credentials(TESTS_DOMAINADMIN_ACCOUNT, TESTS_DOMAINADMIN_PWD)

listener_name = "ucsschool-s4-branch-site"

LISTENER_BASEDIR = "/usr/lib/univention-directory-listener"
HOOKS_BASEDIR = os.path.join(LISTENER_BASEDIR, "hooks")
LISTENER_HOOKS_BASEDIR = os.path.join(HOOKS_BASEDIR, "%s.d" % (listener_name,))

module_template = '''
__package__='' 	# workaround for PEP 366
import univention.debug as ud
import univention.config_registry
import listener

ud.debug(ud.LISTENER, ud.ERROR, "%(modulename)s load")

def handler(dn, new, old, command):
	ud.debug(ud.LISTENER, ud.ERROR, "%(modulename)s handler %(secret)s called")
	if "%(modulename)s" == "01_hook":
		ud.debug(ud.LISTENER, ud.ERROR, " ".join((dn, new, old, unknown)))	## SHOULD FAIL
	else:
		ud.debug(ud.LISTENER, ud.ERROR, " ".join((dn, str(new), str(old), command)))

def postrun():
	ud.debug(ud.LISTENER, ud.ERROR, "%(modulename)s postrun %(secret)s called")
'''

class Test():
	
	@classmethod
	def setup_hook_file(cls, filename, secret_str):
		modulename = filename[:-3].replace('-', '_')
		filepath = os.path.join(LISTENER_HOOKS_BASEDIR, filename)
		with open(filepath, 'w') as f:
			f.write(module_template % {'modulename': modulename, 'secret': secret_str})

	def __enter__(self):
		self.secret_str = uts.random_name()
		Test.setup_hook_file("02_hook.py", self.secret_str)
		Test.setup_hook_file("01_hook.py", "_dummy_")
		return self

	def __exit__(self, type, value, traceback):
		os.unlink(os.path.join(LISTENER_HOOKS_BASEDIR, "01_hook.py"))
		os.unlink(os.path.join(LISTENER_HOOKS_BASEDIR, "02_hook.py"))
		cmd = ["/etc/init.d/univention-directory-listener", "restart"]
		p1 = subprocess.Popen(cmd)
		p1.wait()

	def run(self):
		status = 100

		test_fqdn_list = []
		with testing_udm.UCSTestUDM() as udm:
			for searchbase in get_all_local_searchbases():
				test_hostname = uts.random_name()
				dn = udm.create_object("computers/domaincontroller_slave",
					name = test_hostname,
					position = "cn=dc,cn=server,cn=computers,%s" % (searchbase.schoolDN,),
					domain = ucr.get('domainname'),
					service = ("Samba 4", "UCS@school"),
					groups = ("cn=DC-Edukativnetz,cn=ucsschool,cn=groups,%(ldap/base)s" % ucr)
					)

				test_fqdn = ".".join((test_hostname, ucr.get('domainname')))
				test_fqdn_list.append(test_fqdn)

				testing_utils.wait_for_replication_and_postrun()

				## verify that the test DC is present in the UCR variables
				ucr2 = univention.config_registry.ConfigRegistry()
				ucr2.load()
				test_srv_record = '_kerberos._tcp'
				ucr_var = 'connector/s4/mapping/dns/srv_record/%s.%s/location' % (test_srv_record, ucr.get('domainname'))
				test_value = ucr2.get(ucr_var, '')
				if test_value.find(test_fqdn) == -1:
					testing_utils.fail(log_message="%s not found in %s" % (test_fqdn, ucr_var))

				## verify that the test DC is present in DNS/Samba4
				time.sleep(3)
				p1 = subprocess.Popen(['host', '-t', 'srv', test_srv_record], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
				(stdout, stderr) = p1.communicate()

				if stdout.find(test_fqdn) == -1:
					testing_utils.fail(log_message="%s not found in DNS SRV record %s" % (test_fqdn, test_srv_record))

			## restart listener to load the test hooks before the test DCs get removed
			cmd = ["/etc/init.d/univention-directory-listener", "restart"]
			p1 = subprocess.Popen(cmd)
			p1.wait()

		## ok wait for postrun
		testing_utils.wait_for_replication_and_postrun()
		time.sleep(1)

		## verify that the test DCs are removed from DNS/Samba4
		p1 = subprocess.Popen(['host', '-t', 'srv', '_kerberos._tcp'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		(stdout, stderr) = p1.communicate()
		for test_fqdn in test_fqdn_list:
			if stdout.find(test_fqdn) != -1:
				testing_utils.fail(log_message="%s still found in DNS SRV record %s" % (test_fqdn, test_srv_record))

		## verify that the "Verwaltung" DCs are not in DNS/Samba4
		default_verwaltungs_dc_name = ucr.get("hostname") + "v"
		if stdout.find(default_verwaltungs_dc_name) != -1:
			testing_utils.fail(log_message="%s present in DNS SRV record %s" % (default_verwaltungs_dc_name, test_srv_record))

		## verify that the local DC is still in DNS/Samba4
		local_fqdn = ".".join((ucr.get("hostname"),ucr.get("domainname")))
		if stdout.find(local_fqdn) == -1:
			testing_utils.fail(log_message="%s not present in DNS SRV record %s" % (local_fqdn, test_srv_record))


		## verify that the test DCs are removed from the UCR variable
		ucr2 = univention.config_registry.ConfigRegistry()
		ucr2.load()
		test_srv_record = '_kerberos._tcp'
		ucr_var = 'connector/s4/mapping/dns/srv_record/%s.%s/location' % (test_srv_record, ucr.get('domainname'))
		test_value = ucr2.get(ucr_var, '')
		for test_fqdn in test_fqdn_list:
			if test_value.find(test_fqdn) != -1:
				testing_utils.fail(log_message="%s still found in UCR variable %s" % (test_fqdn, ucr_var))

		## verify that the "Verwaltung" DCs are not in the UCR variable
		if test_value.find(test_hostname) != -1:
			testing_utils.fail(log_message="%s found in UCR variable %s" % (test_hostname, ucr_var))

		## verify that the local DC is still in the UCR variable
		if test_value.find(local_fqdn) == -1:
			testing_utils.fail(log_message="%s not present in UCR variable %s" % (local_fqdn, ucr_var))

		## check that the listener hooks have been run:
		for attr in ("handler", "postrun"):
			search_string = "%s %s called" % (attr, self.secret_str)
			cmd = ["grep", "-q", search_string, "/var/log/univention/listener.log"]
			p1 = subprocess.Popen(cmd, shell=False, close_fds=True)
			p1.wait()
			if p1.returncode:
				testing_utils.fail(log_message="hook not called for '%s()'" % (attr,))

		return status


if __name__ == '__main__':

	with Test() as test:
		rc = test.run()

	sys.exit(rc)

# vim: set filetype=py
