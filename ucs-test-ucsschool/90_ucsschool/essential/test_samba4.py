from sys import exit
from os import getenv
from time import sleep
from httplib import HTTPException
from samba.param import LoadParm
from subprocess import Popen, PIPE

from ucsschool.lib import schoolldap
from univention.testing import utils

from univention.testing.codes import TestCodes
from univention.config_registry import ConfigRegistry
from univention.testing.ucsschool import UMCConnection


class TestSamba4(object):

	def __init__(self):
		"""
		Test class constructor
		"""
		self.UCR = ConfigRegistry()
		self.UMCConnection = None

		self.admin_username = ''
		self.admin_password = ''

		self.ldap_master = ''

		self.gpo_reference = ''

	def return_code_result_skip(self):
		"""
		Stops the test returning the code 77 (RESULT_SKIP).
		"""
		exit(TestCodes.REASON_INSTALL)

	def remove_samba_warnings(self, input_str):
		"""
		Removes the Samba Warning/Note from the given input_str.
		"""
		# ignoring following messages (Bug #37362):
		input_str = input_str.replace('WARNING: No path in service IPC$ - making it unavailable!', '')
		return input_str.replace('NOTE: Service IPC$ is flagged unavailable.', '').strip()

	def create_and_run_process(self, cmd,
										stdin=None, std_input=None,
										shell=False, stdout=PIPE):
		"""
		Creates a process as a Popen instance with a given 'cmd'
		and executes it. When stdin is needed, it can be provided with kwargs.
		To write to a file an istance can be provided to stdout.
		"""
		print '\n create_and_run_process(%r, shell=%r)' % (cmd, shell)
		proc = Popen(cmd,
						stdin=stdin, stdout=stdout, stderr=PIPE,
						shell=shell, close_fds=True)

		stdout, stderr = proc.communicate(input=std_input)

		if stderr:
			stderr = self.remove_samba_warnings(stderr)
		if stdout:
			stdout = self.remove_samba_warnings(stdout)

		return stdout, stderr

	def start_stop_service(self, service, action):
		"""
		Starts, stops or restarts the given 'service' depending on the given
		'action' is 'start', 'stop', 'restart' respectively.
		"""
		if action in ("start", "stop", "restart"):
			cmd = ("service", service, action)
			print "\nExecuting command:", cmd

			stdout, stderr = self.create_and_run_process(cmd)
			if stderr:
				utils.fail("An error occured during %sing the '%s' service: %s"
									% (action, service, stderr))

			stdout = stdout.strip()
			if not stdout:
				utils.fail("The %s command did not produce any output to "
									"stdout, while a confirmation was expected"
									% action)
			print stdout
		else:
			print("\nUnknown state '%s' is given for the service "
						"'%s', accepted 'start' to start it 'stop' to stop or "
						"'restart' to restart" % (action, service))

	def dc_master_has_samba4(self):
		"""
		Returns 'True' when DC-Master has Samba4 according to "service=Samba 4"
		"""
		if not self.ldap_master:
			self.ldap_master = self.UCR.get('ldap/master')

		if self.ldap_master in self.get_udm_list_dcs('domaincontroller_master',
														with_samba4=True):
			return True

	def is_a_school_branch_site(self, host_dn):
		"""
		Returns True if the given 'host_dn' is located in the
		School branch site.
		"""
		if schoolldap.SchoolSearchBase.getOU(host_dn):
			return True

	def grep_for_key(self, grep_in, key):
		"""
		Runs grep on given 'grep_in' with a given 'key'. Returns the output.
		"""
		stdout, stderr = self.create_and_run_process(("grep", key),
														PIPE,
														grep_in)
		if stderr:
			utils.fail("An error occured while running a grep with a "
								"keyword '%s':\n'%s'" % (key, stderr))
		return stdout

	def sed_for_key(self, input, key):
		"""
		Runs sed on given 'input' with a given 'key'. Returns the output.
		"""
		cmd = ("sed", "-n", "s/%s//p" % (key,))
		stdout, stderr = self.create_and_run_process(cmd, PIPE, input)
		if stderr:
			utils.fail("An error occured while running a sed command "
								"'%s':\n'%s'" % (" ".join(cmd), stderr))
		return stdout

	def get_udm_list_dcs(self, dc_type, with_samba4=True):
		"""
		Runs the "udm computers/'dc_type' list" and returns the output.
		If 'with_samba4' is 'True' returns only those running Samba 4.
		"""
		if dc_type not in ('domaincontroller_master',
									'domaincontroller_backup',
									'domaincontroller_slave'):

			print "\nThe given DC type '%s' is unknown" % dc_type
			self.return_code_result_skip()

		cmd = ("udm", "computers/" + dc_type, "list")
		if with_samba4:
			cmd += ("--filter", "service=Samba 4")

		stdout, stderr = self.create_and_run_process(cmd)
		if stderr:
			utils.fail("An error occured while running a '%s' command to "
								"find all '%s' in the domain:\n'%s'"
								% (" ".join(cmd), dc_type, stderr))
		return stdout

	def get_udm_list_dc_slaves_with_samba4(self):
		"""
		Returns the output of "udm computers/domaincontroller_slave list
		--filter service=Samba 4" command.
		"""
		return self.get_udm_list_dcs("domaincontroller_slave")

	def select_school_ou(self, schoolname_only=False):
		"""
		Returns the first found School OU from the list of DC-Slaves in domain.
		"""
		print "\nSelecting the School OU for the test"

		sed_stdout = self.sed_for_key(self.get_udm_list_dc_slaves_with_samba4(), "^DN: ")
		ous = [schoolldap.SchoolSearchBase.getOUDN(x) for x in sed_stdout.split()]
		ous = [schoolldap.SchoolSearchBase.getOU(ou) if schoolname_only else ou for ou in ous if ou]

		print "\nselect_school_ou: SchoolSearchBase found these OUs: %s" % (ous,)
		try:
			return ous[0]
		except IndexError:
			print "\nselect_school_ou: split: %s" % (sed_stdout.split(),)
			utils.fail("Could not find the DN in the udm list output, thus "
								"cannot select the School OU to use as a container")

	def get_samba_sam_ldb_path(self):
		"""
		Returns the 'sam.ldb' path using samba conf or defaults.
		"""
		print("\nObtaining the Samba configuration to determine "
					"Samba private path")
		smb_conf_path = getenv("SMB_CONF_PATH")
		SambaLP = LoadParm()

		if smb_conf_path:
			SambaLP.load(smb_conf_path)
		else:
			SambaLP.load_default()

		return SambaLP.private_path('sam.ldb')

	def get_ucr_test_credentials(self):
		"""
		Loads the UCR to get credentials for the test.
		"""
		print("\nObtaining Administrator username and password "
					"for the test from the UCR")
		try:
			self.UCR.load()

			self.admin_username = self.UCR['tests/domainadmin/account']
			# extracting the 'uid' value of the administrator username string:
			self.admin_username = self.admin_username.split(',')[0][len('uid='):]
			self.admin_password = self.UCR['tests/domainadmin/pwd']
		except KeyError as exc:
			print("\nAn exception while trying to read data from the UCR for "
						"the test: '%s'. Skipping the test." % exc)
			self.return_code_result_skip()

	def create_umc_connection_authenticate(self):
		"""
		Creates UMC connection and authenticates to DC-Master with the test
		user credentials.
		"""
		if not self.ldap_master:
			self.ldap_master = self.UCR.get('ldap/master')

		try:
			self.UMCConnection = UMCConnection(self.ldap_master)
			self.UMCConnection.auth(self.admin_username, self.admin_password)
		except HTTPException as exc:
			print("An HTTPException occured while trying to authenticate "
						"to UMC: %r" % exc)
			print "Waiting 10 seconds and making another attempt"
			sleep(10)
			self.UMCConnection.auth(self.admin_username, self.admin_password)
		except Exception as exc:
			utils.fail("Failed to authenticate, hostname '%s' : %s" %
								(self.ldap_master, exc))

	def delete_samba_gpo(self):
		"""
		Deletes the Group Policy Object using the 'samba-tool gpo del'.
		"""
		print("\nRemoving previously created Group Policy Object (GPO) with "
					"a reference: %s" % self.gpo_reference)

		cmd = ("samba-tool", "gpo", "del", self.gpo_reference,
						"--username=" + self.admin_username,
						"--password=" + self.admin_password)

		stdout, stderr = self.create_and_run_process(cmd)
		if stderr:
			print "\nExecuting cmd:", cmd
			print("\nAn error message while removing the GPO using "
						"'samba-tool':\n%s" % stderr)

		print "\nSamba-tool produced the following output:\n", stdout
