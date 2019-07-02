#!/usr/share/ucs-test/runner python
## desc: Test the Samba SID allocation.
## bugs: [34221]
## roles:
## - domaincontroller_master
## - domaincontroller_backup
## - domaincontroller_slave
## packages: [univention-s4-connector, univention-samba4]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous

import re
import ldap
from sys import exit
from time import sleep

from univention.testing.ucsschool.test_samba4 import TestSamba4

import univention.testing.utils as utils
from univention.uldap import getMachineConnection
from univention.testing.udm import UCSTestUDM
from univention.testing.strings import random_username
from univention.testing.ucs_samba import wait_for_drs_replication


class TestS4SIDAllocation(TestSamba4):

	def __init__(self):
		"""
		Test class constructor.
		"""
		super(TestS4SIDAllocation, self).__init__()

		self.test_remotely = None
		self.LdapConnection = getMachineConnection(ldap_master=False)

	def start_stop_s4_connector_on_master(self, action):
		"""
		Makes a UMC request to DC-Master to stop or start the S4-Connector.
		"""
		print("\nMaking a UMC request to %s the S4-Connector service on the DC-Master\n" % action)
		assert self.client.umc_command('services/' + action, ['univention-s4-connector']).result.get('success'), 'Restarting S4-Connector service failed'

	def start_stop_s4_connector(self, connector_should_run):
		"""
		Starts or stops the S4 connector depending on given arg (True or False)
		also for the DC-Master via UMC if the 'self.test_remotely' is 'True'.
		"""
		if connector_should_run is True:
			if self.test_remotely:
				# start the service on DC-Master
				self.start_stop_s4_connector_on_master('start')
			# start service locally
			utils.start_s4connector()

		elif connector_should_run is False:
			if self.test_remotely:
				# stop the service on DC-Master
				self.start_stop_s4_connector_on_master('stop')
			# stop service locally
			utils.stop_s4connector()

		else:
			print("\nUnknown state '%s' is given for S4 connector, accepted 'True' to start or 'False' to stop." % connector_should_run)

	def s4_search(self, filter_string, attribute):
		"""
		Search in S4 LDAP via univention-s4-search
		"""

		print "\nLooking for %s using univention-s4search." % attribute
		cmd = ('univention-s4search', filter_string, attribute)

		print "Executing command:", cmd
		stdout, stderr = self.create_and_run_process(cmd)
		if stderr:
			utils.fail("An error occured while running univention-s4search: %r" % stderr)
		matches = re.findall("^%s: (.*)$" % attribute, stdout, re.MULTILINE)
		if not matches:
			utils.fail("The 'univention-s4search' did not produce any %s." % attribute)
		return matches[0]

	def get_sid_via_ldbsearch(self, user_dn, ldburl):
		"""
		Returns the 'objectSid' as stored in the given 'ldburl' for the given
		'user_dn'.
		"""
		user_dn = user_dn.replace('uid=', 'cn=', 1)

		print(
			"\nSearching for the 'objectSid' of the user with DN: '%s' in the database located at '%s' using "
			"'ldbsearch'" % (user_dn, ldburl))

		cmd = ('ldbsearch', '-H', ldburl, '--user=' + self.admin_username + '%' + self.admin_password, '-b', user_dn, 'objectSid')

		print "Executing command:", cmd
		stdout, stderr = self.create_and_run_process(cmd)
		if stderr:
			utils.fail("An error occured while performing a 'ldbsearch' for a user with DN '%s'. STDERR: '%s'" % (user_dn, stderr))

		object_sids = re.findall("^objectSid: (.*)$", stdout, re.MULTILINE)
		if not object_sids:
			return ""
		return object_sids[0]

	def get_sid_from_ldap(self, user_dn):
		"""
		Opens the uldap machine connection and returns the 'sambaSID' for the
		user with a given 'user_dn'.
		"""
		print("\nLooking for a 'sambaSID' of a user with a DN: '%s' in the LDAP" % user_dn)
		try:
			samba_sid = self.LdapConnection.get(user_dn)['sambaSID'][0]
			if not samba_sid:
				utils.fail("The 'sambaSID' is empty in the LDAP.")
		except (KeyError, IndexError) as exc:
			utils.fail("An error occured while trying to get the 'sambaSID' for the user with a DN '%s' from the LDAP: '%s'" % (user_dn, exc))

		return samba_sid

	def dc_master_has_s4(self):
		"""
		Returns 'True' if the DC-Master has S4 running or False otherwise.
		Looking in the LDAP for 'Samba 4' in DC-Master 'univentionService'-s.
		"""
		try:
			dc_master = self.ldap_master.replace(self.UCR['domainname'], '', 1)[:-1]
			dc_master_dn = ("cn=%s,cn=dc,cn=computers,%s" % (dc_master, self.UCR.get('ldap/base')))
			master_services = self.LdapConnection.get(dc_master_dn)['univentionService']

			if 'Samba 4' in master_services:
				print("\nThe DC-Master has Samba4 running, the test will also check the SID for the test user on the DC-Master")
				return True

		except KeyError as exc:
			utils.fail("An error occured while trying to get the DC-Master 'univentionServices': '%s'" % exc)

	def determine_test_scenario(self):
		"""
		Determines if the test should perform checks only locally, or
		if it should also check the 'SambaSID' on the remote DC.
		Creates the UMC connection to DC-Master when checks should
		also be performed there.
		"""
		if self.UCR.get('server/role') == 'domaincontroller_master':
			print "\nCurrent role is DC-Master, performing only local checks"
			self.test_remotely = False
		elif not self.dc_master_has_s4():
			print "\nThe DC-Master has no Samba4, performing only local checks"
			self.test_remotely = False
		else:
			self.test_remotely = True
			self.create_umc_connection_authenticate()

	def main(self):
		"""
		Tests that SambaSID allocation is correct.
		When run on DC-Master performs only local check;
		When run on DC-Backup or DC-Slave also performs the remote
		check on the DC-Master;
		Also checks the 'NextRID' allocation.
		"""
		self.get_ucr_test_credentials()

		UDM = UCSTestUDM()

		test_username = 'ucs_school_test_user_' + random_username(8)
		test_user_dn = ''

		try:
			self.ldap_master = self.UCR.get('ldap/master')

			# determine if test should take into account a remote DC:
			self.determine_test_scenario()

			# stop the S4-Connector:
			self.start_stop_s4_connector(False)

			# get 'rIDNextRID' from Samba4 before user creation:
			initial_next_rid = self.s4_search('(objectClass=rIDSet)', 'rIDNextRID')

			# create regular user for the test. this skips the drs replication
			# check, as the s4-connector was previously stopped.
			test_user_dn = UDM.create_user(password='univention',
			                               username=test_username,
			                               wait_for=False)[0]

			test_user_dn_exploded = ldap.dn.str2dn(test_user_dn)
			(_attr, test_user_cn, _flags) = test_user_dn_exploded[0][0]
			s4_user_filter = ldap.filter.filter_format("(cn=%s)", (test_user_cn,))

			# get 'rIDNextRID' after user is created and replicated
			next_rid_pre_sync = self.s4_search('(objectClass=rIDSet)', 'rIDNextRID')
			if next_rid_pre_sync != initial_next_rid:
				utils.fail(("The 'rIDNextRID' changed after user creation. Was: %s."
				            " Now: %s." % (initial_next_rid, next_rid_pre_sync)))

			print("\nComparing the SID for test user as stored in LDAP after sync:")
			# get SID from LDAP
			ldap_sid_pre_sync = self.get_sid_from_ldap(test_user_dn)

			# start the S4-Connector
			self.start_stop_s4_connector(True)
			wait_for_drs_replication(s4_user_filter)

			# get 'rIDNextRID' after user is created and replicated
			next_rid_post_sync = self.s4_search('(objectClass=rIDSet)', 'rIDNextRID')
			if next_rid_post_sync != initial_next_rid:
				utils.fail(("The 'rIDNextRID' changed after user sync. Was: %s."
				            " Now: %s." % (initial_next_rid, next_rid_post_sync)))

			# get SID from LDAP
			ldap_sid_post_sync = self.get_sid_from_ldap(test_user_dn)

			if ldap_sid_pre_sync != ldap_sid_post_sync:
				utils.fail(("The SID in the LDAP after S4 sync for the test user '%s'"
				            " is different from pre sync: '%s' vs. '%s' in Samba4 LDB."
				            % (test_username, ldap_sid_pre_sync, ldap_sid_post_sync)))

			# get SID from Samba4
			samba_sid = self.s4_search(s4_user_filter, "objectSid")

			if ldap_sid_pre_sync != samba_sid:
				utils.fail(("The SID in the LDAP and Samba4 for the test user '%s'"
				           " are different: '%s' vs. '%s' in Samba4 LDB."
				            % (test_username, ldap_sid_pre_sync, samba_sid)))

			# perform remote check when needed
			if self.test_remotely:
				print "\nComparing the SID on DC-Master with the local one:"

				uri = 'ldap://' + self.ldap_master
				for _ in range(5):  # poor man's replication check
					samba_sid_master = self.get_sid_via_ldbsearch(test_user_dn, uri)
					if samba_sid_master:
						break
					print "\nNot yet replicated to master. Sleep for 10 seconds and retry."
					sleep(10)

				# compare objectSid@locally vs. objectSid@Master
				if ldap_sid_pre_sync != samba_sid_master:
					utils.fail(("The SID in the LDAP and Samba4 on the DC-Master for"
					            " the test user '%s' are different: '%s' vs. '%s' in"
					            " Samba4 LDB." % (test_username, ldap_sid_pre_sync, samba_sid_master)))
		finally:
			if test_user_dn:
				print "\nRemoving the test user:", test_username
				UDM.remove_object('users/user', dn=test_user_dn)

			print "\nForcing S4 connector start to make sure it runs:"
			self.start_stop_s4_connector(True)


if __name__ == '__main__':
	TestSambaSIDAllocation = TestS4SIDAllocation()
	exit(TestSambaSIDAllocation.main())
