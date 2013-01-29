#!/usr/bin/python2.6
#
# Univention Management Console
#  This installation wizard guides the installation of UCS@school in the domain
#
# Copyright 2013 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

# standard library
import threading
import os.path
import socket
import re
import tempfile
import glob

# related third party
import notifier
import notifier.threads
import dns.resolver
#import ldap.filter
import paramiko

# univention
#from univention.lib import escape_value
from univention.lib.package_manager import PackageManager
from univention.management.console.modules import Base
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, MappingSanitizer, ChoicesSanitizer
import univention.uldap

from univention.lib.i18n import Translation

_ = Translation( 'ucs-school-umc-installer' ).translate
ucr.load()

fqdn_pattern     = '^[a-z]([a-z0-9-]*[a-z0-9])*\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*$'
hostname_pattern = '^[a-z]([a-z0-9-]*[a-z0-9])*(\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*)?$'
ou_pattern       = '^(([a-zA-Z0-9_]*)([a-zA-Z0-9]))?$'

#class SetupSanitizer(StringSanitizer):
#	def _sanitize(self, value, name, further_args):
#		ucr.load()
#		server_role = ucr.get('server/role')
#		if value == 'singlemaster':
#			if server_role == 'domaincontroller_master' or server_role == 'domaincontroller_backup':
#				return 'ucs-school-singlemaster'
#			self.raise_validation_error(_('Single master setup not allowed on server role "%s"') % server_role)
#		if value == 'multiserver':
#			if server_role == 'domaincontroller_master' or server_role == 'domaincontroller_backup':
#				return 'ucs-school-master'
#			elif server_role == 'domaincontroller_slave':
#				return 'ucs-school-slave'
#			self.raise_validation_error(_('Multiserver setup not allowed on server role "%s"') % server_role)
#		self.raise_validation_error(_('Value "%s" not allowed') % value)

class HostSanitizer(StringSanitizer):
	def _sanitize(self, value, name, further_args):
		value = super(HostSanitizer, self)._sanitize(value, name, further_args)
		try:
			return socket.getfqdn(value)
		except socket.gaierror:
			# invalid FQDN
			self.raise_validation_error(_('The entered FQDN is not a valid value'))

def get_ldap_connection(host, binddn, bindpw):
	return univention.uldap.access(host, port=int(ucr.get('ldap/master/port', '7389')), binddn=binddn, bindpw=bindpw)

def create_ou(master, ou, slave, username, password):
	"""create a OU
	"""
	success = True
	with tempfile.NamedTemporaryFile() as passwordFile:
		# write password to temporary file
		passwordFile.write('%s\n' % password)

		# remote UMC call
		process = subprocess.Popen(['/usr/sbin/umc-command', '-U', username, '-y', passwordFile.name, '-s', master, 'schoolwizard/schools/create', '-o' ,'name=%s' % ou, '-o', 'schooldc=%s' % slave ], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		res = process.communicate()

		# check for errors
		if process.returncode != 0:
			# error case
			MODULE.warn('Could not create OU on %s as %s: %s%s' % (master, username, res[1], res[0]))
			success = False

	return success

	#CREATE_OU_EXEC = '/usr/share/ucs-school-import/scripts/create_ou'
	#cmd = ' '.join([CREATE_OU_EXEC, master, ou, slave])
	#MODULE.process('executing on %s: %s' % (master, cmd))

	## build up SSH connection
	#ssh = paramiko.SSHClient()
	#ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	#ssh.load_system_host_keys()
	#ssh.connect(master, username=username, password=password)

	## execute command and process output
	#stdin, stdout, stderr = ssh.exec_command(cmd)
	#stdout = [ i.strip() for i in stdout ]
	#stderr = [ i.strip() for i in stdout ]
	#MODULE.info('stdout: %s' % '\n'.join(stdout))
	#if stderr:
	#	MODULE.warn('ERROR: %s' % '\n'.join(stderr))

# dummy function that does nothing
def _dummyFunc(*args):
	pass

def system_join(username, password, info_handler = _dummyFunc, error_handler = _dummyFunc, step_handler = _dummyFunc):
	# get the number of join scripts
	nJoinScripts = len(glob.glob('/usr/lib/univention-install/*.inst'))
	stepsPerScript = 100.0 / nJoinScripts

	with tempfile.NamedTemporaryFile() as passwordFile:
		passwordFile.write('%s\n' % password)

		# regular expressions for output parsing
		regError = re.compile('^\* Message:\s*(?P<message>.*)\s*$')
		regJoinScript = re.compile('Configure\s+(?P<script>.*)\.inst.*$')
		regInfo = re.compile('^(?P<message>.*)\s*done\s*$', re.IGNORECASE)

		# call to univention-join
		process = subprocess.Popen(['/usr/share/univention-join/univention-join', '-dcaccount', username, '-dcpwd', passwordFile.name], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		while True:
			# get the next line
			line = process.stdout.readline()
			if not line:
				# no more text from stdout
				break

			# parse output... first check for errors
			m = regError.match(line)
			if m:
				error_handler(m.groupdict.get('message'))
				continue

			# check for currently called join script
			m = regJoinScript.match(line)
			if m:
				info_handler(_('Executing join script %s') % m.groupdict.get('script'))
				step_handler(stepsPerScript)
				continue

			# check for other information
			m = regInfo.match(line)
			if m:
				info_handler(m.groupdict.get('message'))
				continue

		# get all remaining output
		stdout, stderr = process.communicate()
		if stderr:
			# write stderr into the log file
			MODULE.warn('stderr from univention-join: %s' % stderr)

		# check for errors
		if process.returncode != 0:
			# error case
			MODULE.warn('Could not create OU on %s as %s: %s%s' % (master, username, res[1], res[0]))
			success = False


class Progress(object):
	def __init__(self, max_steps=100):
		self.reset(max_steps)

	def reset(self, max_steps=100):
		self.max_steps = max_steps
		self.finished = False
		self.steps = 0
		self.component = _('Initializing')
		self.info = ''
		self.errors = []

	def poll(self):
		return dict(
			finished=self.finished,
			steps=float(self.steps) / self.max_steps,
			component=self.component,
			info=self.info,
			errors=self.errors,
		)

	def finish(self):
		self.finished = True

	def info_handler(self, info):
		MODULE.process(info)
		self.info = info

	def error_handler(self, err):
		MODULE.warn(err)
		self.errors.append(err)

	def step_handler(self, steps):
		self.steps = steps

	def add_steps(self, steps = 1):
		self.steps += steps

class Instance(Base):
	def init(self):
		self._finishedLock = threading.Lock()
		self._errors = []
		self.progress_state = Progress()
		self.package_manager = PackageManager(
			info_handler=self.progress_state.info_handler,
			step_handler=self.progress_state.step_handler,
			error_handler=self.progress_state.error_handler,
			lock=False,
			always_noninteractive=True,
		)

	def get_samba_version(self):
		'''Returns 3 or 4 for Samba4 or Samba3 installation, respectively, and returns None otherwise.'''
		if self.package_manager.is_installed('univention-samba4'):
			return 4
		elif self.package_manager.is_installed('univention-samba'):
			return 3
		return None

	def get_ucs_school_version(self):
		'''Returns 'singlemaster', 'multiserver', or None'''
		if self.package_manager.is_installed('ucs-school-singlemaster'):
			return 'singlemaster'
		elif self.package_manager.is_installed('ucs-school-slave') or self.package_manager.is_installed('ucs-school-master'):
			return 'multiserver'
		return None

	def get_remote_ucs_school_version(self, username, password, master):
		'''Verify that the correct UCS@school version (singlemaster, multiserver) is
		installed on the master system.'''
		MODULE.info('building up ssh connection to %s as user %s' % (master, username))
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.load_system_host_keys()
		ssh.connect(master, username=username, password=password)

		# check the installed packages on the master system
		regStatusInstalled = re.compile(r'^Status\s*:.*installed.*')
		installedPackages = []
		for ipackage in ('ucs-school-singlemaster', 'ucs-school-slave', 'ucs-school-master'):
			# get 'dpkg --status' output
			stdin, stdout, stderr = ssh.exec_command("/usr/bin/dpkg --status %s" % ipackage)

			# match: "Status: install ok installed"
			# TODO: double check regular expression
			res = [ i for i in stdout if regStatusInstalled.match(i) ]
			if res:
				installedPackages.append(ipackage)

		if 'ucs-school-singlemaster' in installedPackages:
			return 'singlemaster'
		if 'ucs-school-slave' in installedPackages or 'ucs-school-master' in installedPackages:
			return 'multiserver'

	def get_master_dns_lookup(self):
		# DNS lookup for the DC master entry
		result = dns.resolver.query('_domaincontroller_master._tcp', 'SRV')
		if result:
			return result[0].target.canonicalize().split(1)[0].to_text()
		return ''

	@simple_response
	def query(self, **kwargs):
		"""Returns a dictionary of initial values for the form."""
		ucr.load()

		return {
			'server_role': ucr.get('server/role'),
			'joined': os.path.exists('/var/univention-join/joined'),
			'samba': self.get_samba_version(),
			'ucsschool': self.get_ucs_school_version(),
			'guessed_master': self.get_master_dns_lookup(),
		}

### currently not used
#	def getDN(self, username, password, master):
#		"""Returns the usernames DN and masters FQDN"""
#		ssh = paramiko.SSHClient()
#		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#		ssh.load_system_host_keys()
#		ssh.connect(master, username=username, password=password)
#
#		# try to get the DN of the user account
#		username = ldap.filter.escape_filter_chars(username)
#		stdin, dn, stderr = ssh.exec_command("/usr/sbin/udm users/user list --filter uid='%s' --logfile /dev/null | sed -ne 's|^DN: ||p'" % escape_value(username))
#
#		if not dn.strip():
#			dn = None
#
#		return dn

### currently not used
#	@sanitize(username=StringSanitizer(required=True, use_asterisks=False), password=StringSanitizer(required=True), master=HostSanitizer(required=True, regex_pattern=fqdn_pattern), allow_other_keys=False)
#	@simple_response
#	def samba(self, username, password, master):
#		"""Returns 'samba3' if the Samba3 is installed on the master system, else 'samab4'"""
#		try:
#			lo = get_ldap_connection(master, username, password)
#		except:
#			pass # TODO
#
#		# search for samba4 service object
#		if lo.search(filter='(&(objectClass=univentionServiceObject)(name=Samba 3))'):
#			return 'samba3'
#		elif lo.search(filter='(&(objectClass=univentionServiceObject)(name=Samba 4))'):
#			return 'samba4'
#		return 'samba4' # fallback, no samba installed

	@simple_response
	def progress(self):
		return self.progress_state.poll()

	@sanitize(
		username=StringSanitizer(required=True),
		password=StringSanitizer(required=True),
		master=HostSanitizer(required=True, regex_pattern=hostname_pattern),
		samba=ChoicesSanitizer(['3', '4']),
		schoolOU=StringSanitizer(required=True, regex_pattern=ou_pattern),
		setup=ChoicesSanitizer(['multiserver', 'singlemaster']),
	)
	def install(self, request):
		# get all arguments
		username = request.options.get('username')
		password = request.options.get('password')
		master = request.options.get('master')
		samba = request.options.get('samba')
		schoolOU = request.options.get('schoolOU')
		setup = request.options.get('setup')
		serverRole = ucr.get('server/role')

		# ensure that the setup is ok
		MODULE.process('performing UCS@school installation')
		error = None
		try:
			if not (serverRole == 'domaincontroller_master' or serverRole == 'domaincontroller_backup' or serverRole == 'domaincontroller_slave'):
				error = _('Invalid server role! UCS@school can only be installed on the system roles DC master, DC backup, or DC slave.')
			elif serverRole == 'domaincontroller_slave':
				# check for a compatible setup on the DC master
				schoolVersion = self.get_remote_ucs_school_version(username, password, master)
				if not schoolVersion:
					error = _('Please install UCS@school on the DC master system. Cannot proceed installation on this system.')
				if schoolVersion != 'multiserver':
					error = _('The UCS@school DC master system is not configured as a multi server setup. Cannot proceed installation on this system.')
		except socket.gaierror as e:
			MODULE.warn('Could not connect to master system %s: %s' % (master, e))
			error = _('Cannot connect to the DC master system %s. Please make sure that the system is reachable. If not this could due to wrong DNS nameserver settings.') % master
		except paramiko.SSHException as e:
			MODULE.warn('Could not connect to master system %s: %s' % (master, e))
			error = _('Cannot connect to the DC master system %s. It seems that the specified domain credentials are not valid.') % master

		if not error:
			# everything ok, try to acquire the lock for the package installation
			lock_aquired = self.package_manager.lock(raise_on_fail=False)
			if not lock_aquired:
				MODULE.warn('Could not aquire lock for package manager')
				error = _('Cannot get lock for installation process. Another Package Manager seems to block the operation.')

		# see which packages we need to install
		installPackages = []
		if serverRole in ('domaincontroller_master', 'domaincontroller_backup'):
			if setup == 'singlemaster':
				installPackages.append('ucs-school-singlemaster')
				if samba == '3':
					installPackages.append('univention-samba')
				else:  # -> samba4
					installPackages.extend(['univention-samba4', 'univention-s4-connector'])
			elif setup == 'multiserver':
				installPackages.append('ucs-school-master')
			else:
				error = _('Invalid UCS@school configuration.')
		elif serverRole == 'domaincontroller_slave':
			installPackages.append('ucs-school-slave')
			if samba == '3':
				installPackages.extend(['univention-samba', 'univention-samba-slave-pdc'])
			else:  # -> samba4
				installPackages.extend(['univention-samba4', 'univention-s4-connector'])
		else:
			error = _('Invalid UCS@school configuration.')
		MODULE.info('Packages to be installed: %s' % ', '.join(installPackages))

		# start installation if configuration is ok
		if error:
			MODULE.error('Error installing UCS@school: %s' % error)
		else:
			# reset the current installation progress
			#FIXME: correct percentage + maximum steps
			progress_state = self.progress_state
			progress_state.reset(210)
			progress_state.component = _('Installation of UCS@school packages')
			#FIXME: correct to make a reset here?
			self.package_manager.reset_status()

			def _thread(_self, packages):
				# perform installation
				success = True
				MODULE.process('Starting package installation')
				with _self.package_manager.locked(reset_status=True, set_finished=True):
					with _self.package_manager.no_umc_restart(exclude_apache=True):
						success = _self.package_manager.install(*packages)

				MODULE.info('Result of package installation: success=%s' % success)

				# on a DC master, we are done
				if serverRole != 'domaincontroller_slave':
					return success

				# check for errors
				#FIXME: correct check for success?
				if not success:
					return success

				# create the school OU
				MODULE.info('Starting creation of LDAP school OU structure...')
				progress_state.component = _('Creation of LDAP school structore')
				progress_state.info = ''
				if create_ou(master, schoolOU, ucr.get('hostname'), username, password):
					MODULE.info('created school OU')

					# system join
					progress_state.add_steps(10)
					progress_state.component = _('Domain join')
					progress_state.info = _('Preparing domain join...')

					# create a new system join instance
					MODULE.process('Starting system join...')
					success = system_join(
						username, password,
						info_handler=self.progress_state.info_handler,
						step_handler=self.progress_state.add_steps,
						error_handler=self.progress_state.error_handler,
					)
				else:
					progress_state.error(_('The UCS@school software packages have been installed, however, a school OU could not be created and consequently a re-join of the system has not been performed. Please create a new school OU structure using the UMC module "Add school" on the master and perform a domain join on this machine via the UMC module "Domain join".' ))

			def _finished(thread, result):
				MODULE.info('Finished installation')
				progress_state.info = _('finished...')
				progress_state.finished()
				if isinstance(result, BaseException):
					MODULE.warn('Exception during installation: %s' % result)

			# launch thread
			thread = notifier.threads.Simple('ucsschool-install',
				notifier.Callback(_thread, self, installPackages), _finished)
			thread.run()

		# finish the request
		result = {'success' : error is None, 'error' : error}
		self.finished(request.id, result)


