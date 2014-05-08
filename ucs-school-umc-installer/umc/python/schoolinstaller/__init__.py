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
import os
import socket
import re
import tempfile
import glob
import subprocess
import traceback
import ast
import urllib
import filecmp

# related third party
import notifier
import notifier.threads
import dns.resolver
import paramiko

# univention
#from univention.lib import escape_value
from univention.lib.package_manager import PackageManager
from univention.management.console.modules import Base
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, ChoicesSanitizer
import univention.uldap
import univention.admin.uldap
import univention.admin.modules as udm_modules
udm_modules.update()
from ucsschool.lib.schoolldap import SchoolSearchBase

from univention.lib.i18n import Translation

_ = Translation( 'ucs-school-umc-installer' ).translate
ucr.load()
# switch back to default umask
os.umask(0022)

RE_FQDN     = re.compile('^[a-z]([a-z0-9-]*[a-z0-9])*\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*$')
RE_HOSTNAME = re.compile('^[a-z]([a-z0-9-]*[a-z0-9])*(\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*)?$')
RE_OU       = re.compile('^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$')

CMD_ENABLE_EXEC = ['/usr/share/univention-updater/enable-apache2-umc', '--no-restart']
CMD_DISABLE_EXEC = '/usr/share/univention-updater/disable-apache2-umc'

CERTIFICATE_PATH = '/etc/univention/ssl/ucsCA/CAcert.pem'

#class SetupSanitizer(StringSanitizer):
#	def _sanitize(self, value, name, further_args):
#		ucr.load()
#		server_role = ucr.get('server/role')
#		if value == 'singlemaster':
#			if server_role == 'domaincontroller_master' or server_role == 'domaincontroller_backup':
#				return 'ucs-school-singlemaster'
#			self.raise_validation_error(_('Single server environment not allowed on server role "%s"') % server_role)
#		if value == 'multiserver':
#			if server_role == 'domaincontroller_master' or server_role == 'domaincontroller_backup':
#				return 'ucs-school-master'
#			elif server_role == 'domaincontroller_slave':
#				return 'ucs-school-slave'
#			self.raise_validation_error(_('Multi server environment not allowed on server role "%s"') % server_role)
#		self.raise_validation_error(_('Value "%s" not allowed') % value)

class HostSanitizer(StringSanitizer):
	def _sanitize(self, value, name, further_args):
		value = super(HostSanitizer, self)._sanitize(value, name, further_args)
		try:
			return socket.getfqdn(value)
		except socket.gaierror:
			# invalid FQDN
			self.raise_validation_error(_('The entered FQDN is not a valid value'))

def get_ssh_connection(username, password, host):
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	ssh.load_system_host_keys()
	ssh.connect(host, username=username, password=password)
	return ssh

def move_slave_into_ou(master, username, password, ou, slave):
	'''Make sure that the slave object exists in the right OU.'''
	MODULE.info('Trying to move the slave entry in the right OU structure...''')
	result = umc(username, password, master, ['schoolwizards/schools/move_dc', '-o', 'schooldc=%s' % slave , '-o', 'schoolou=%s' % ou, '-f', 'schoolwizards/schools'])
	if not result.get('success'):
		MODULE.warn('Could not successfully move the slave DC into its correct OU structure:\n%s' % result.get('message'))
		return False
	return True

def get_remote_ucs_school_version(username, password, master):
	'''Verify that the correct UCS@school version (single server, multi server) is
	installed on the master system.'''
	MODULE.info('building up ssh connection to %s as user %s' % (master, username))
	ssh = get_ssh_connection(username, password, master)

	# check the installed packages on the master system
	regStatusInstalled = re.compile(r'^Status:.*\sinstalled$')
	installedPackages = []
	for ipackage in ('ucs-school-singlemaster', 'ucs-school-slave', 'ucs-school-master'):
		# get 'dpkg --status' output
		stdin, stdout, stderr = ssh.exec_command("/usr/bin/dpkg --status %s" % ipackage)

		# match: "Status: install ok installed"
		# TODO: double check regular expression
		res = [ i for i in stdout if regStatusInstalled.match(i) ]
		if res:
			installedPackages.append(ipackage)
		MODULE.info('package %s installed on the system? %s' % (ipackage, bool(res)))

	if 'ucs-school-singlemaster' in installedPackages:
		return 'singlemaster'
	if 'ucs-school-slave' in installedPackages or 'ucs-school-master' in installedPackages:
		return 'multiserver'

def get_master_dns_lookup():
	# DNS lookup for the DC master entry
	try:
		query = '_domaincontroller_master._tcp.%s.' % ucr.get('domainname')
		result = dns.resolver.query(query, 'SRV')
		if result:
			return result[0].target.canonicalize().split(1)[0].to_text()
	except dns.resolver.NXDOMAIN:
		MODULE.error('Error to perform a DNS query for service record: %s' % query)
	return ''

#def ou_exists(ou, username, password, master = None):
#	"""Indicates whether a specified OU already exists or not."""
#	with tempfile.NamedTemporaryFile() as passwordFile:
#		passwordFile.write('%s' % password)
#		passwordFile.flush()
#		credentials = [ '-U', username, '-y', passwordFile.name ]
#		if ucr.get('system/role') == 'domaincontroller_slave':
#			# on a slave, we need to access the master
#			credentials.extend(['-s', master])
#
#		# UMC call
#		cmd = ['/usr/sbin/umc-command'] + credentials + ['-f', 'container/ou', 'udm/query', '-o', 'objectProperty=None']
#		process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#		stdout, stderr = process.communicate()
#
#		# parse output
#		match = regUMCResult.match(stdout)
#
#		# check for errors
#		if process.returncode != 0 or not match:
#			# error case... should not happen
#			MODULE.error('Failed to launch UMC query:\n%s%s' % (stderr, stdout))
#			raise RuntimeError(_('Cannot query LDAP information.'))
#
#		# parse the result and filter out entries that match the specifed OU
#		result = ast.literal_eval(match.groupdict().get('result'))
#		result = [ ientry for ientry in res if ientry.get('$dn$') == 'ou=%s,%s' % (ou, ucr.get('ldap/base')) ]
#		return bool(result)

regUMCResult = re.compile(r'.*^\s*RESULT\s*:\s*(?P<result>.*)', re.MULTILINE | re.DOTALL)

def umc(username, password, master, options = [], requestType='command'):
	with tempfile.NamedTemporaryFile() as passwordFile:
		# write password to temp file
		passwordFile.write('%s' % password)
		passwordFile.flush()

		# UMC call
		cmd = ['/usr/sbin/umc-%s' % requestType, '-U', username, '-y', passwordFile.name, '-s', master]
		cmd += options
		MODULE.info('Executing: %s' % ' '.join(cmd))
		process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()

		# parse output
		match = regUMCResult.match(stdout)

		# check for errors
		if process.returncode != 0 or not match:
			# error case... should not happen
			MODULE.error('Failed to launch UMC query: %s\n%s%s' % (cmd, stderr, stdout))
			raise RuntimeError(_('Cannot connect to UMC server %s.') % master)

		# parse the result and filter for exact matches (UMC search for '*pattern*')
		return ast.literal_eval(match.groupdict().get('result'))

def get_user_dn(username, password, master):
	"""Get the LDAP DN for the given username."""
	result = umc(username, password, master, ['-f', 'users/user', 'udm/query', '-o', 'objectProperty=username', '-o', 'objectPropertyValue=%s' % username ])
	result = [ ientry for ientry in result if ientry.get('username') == username ]
	if not result:
		return None
	return result[0].get('$dn$')

def create_ou_local(ou, displayName):
	'''Calls create_ou locally as user root (only on master).'''
	if not displayName:
		MODULE.warn('create_ou_local(): display name is undefined - using OU name as display name')
		displayName = ou

	# call create_ou
	cmd = ['/usr/share/ucs-school-import/scripts/create_ou', '--displayName', displayName, ou]
	MODULE.info('Executing: %s' % ' '.join(cmd))
	process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()

	# check for errors
	if process.returncode != 0:
		# error case... should not happen
		MODULE.error('Failed to execute create_ou: %s\n%s%s' % (cmd, stderr, stdout))
		return False
	return True

def create_ou_remote(master, username, password, ou, display_name, educational_slave, administrative_slave=None):
	"""Create a school OU via the UMC interface."""
	try:
		opts = [{'object' : {'name' : ou, 'display_name' : display_name, 'dc_name_educational' : educational_slave}}]
		if administrative_slave:
			opts[0]['object']['dc_name_administrative'] = administrative_slave
		umc(username, password, master, ['schoolwizards/schools/create', '-e', '-o', repr(opts), '-f', 'schoolwizards/schools'])
	except RuntimeError:
		return False
	return True

def get_ucr_master(username, password, master, *ucrVariables):
	'''Read the LDAP base from the master system via UMC.'''
	options = ['ucr', '-l']
	for ivar in ucrVariables:
		options += ['-o', ivar]
	return umc(username, password, master, options, 'get')

def restoreOrigCertificate(certOrigFile):
	# try to restore the original certificate file
	if certOrigFile and os.path.exists(certOrigFile):
		try:
			MODULE.info('Restoring original root certificate.')
			os.rename(certOrigFile, CERTIFICATE_PATH)
		except (IOError, OSError) as err:
			MODULE.warn('Could not restore original root certificate: %s' % err)
		certOrigFile = None

def retrieveRootCertificate(master):
	'''On a slave system, download the root certificate from the specified master
	and install it on the system. In this way it can be ensured that secure
	connections can be performed even though the system has not been joined yet.
	Returns the renamed original file if it has been renamed. Otherwise None is returned.'''
	if ucr.get('server/role') != 'domaincontroller_slave':
		# only do this on a slave system
		return

	# make sure the directory exists
	if not os.path.exists(os.path.dirname(CERTIFICATE_PATH)):
		os.makedirs(os.path.dirname(CERTIFICATE_PATH))
	try:
		# download the certificate from the DC master
		certURI = 'http://%s/ucs-root-ca.crt' % master
		certOrigFile = None
		MODULE.info('Downloading root certificate from: %s' % master)
		certDownloadedFile, headers = urllib.urlretrieve('http://%s/ucs-root-ca.crt' % master)

		if not filecmp.cmp(CERTIFICATE_PATH, certDownloadedFile):
			# we need to update the certificate file...
			# save the original file first and make sure we do not override any existing file
			count = 1
			certOrigFile = CERTIFICATE_PATH + '.orig'
			while os.path.exists(certOrigFile):
				count += 1
				certOrigFile = CERTIFICATE_PATH + '.orig%s' % count
			os.rename(CERTIFICATE_PATH, certOrigFile)
			MODULE.info('Backing up old root certificate as: %s' % certOrigFile)

			# place the downloaded certificate at the original position
			os.rename(certDownloadedFile, CERTIFICATE_PATH)
			os.chmod(CERTIFICATE_PATH, 0o644)
	except (IOError, OSError) as err:
		# print warning and ignore error
		MODULE.warn('Could not download root certificate [%s], error ignored: %s' % (certURI, err))
		restoreOrigCertificate(certOrigFile)

	return certOrigFile

# dummy function that does nothing
def _dummyFunc(*args):
	pass

def system_join(username, password, info_handler = _dummyFunc, error_handler = _dummyFunc, step_handler = _dummyFunc):
	# make sure we got the correct server role
	serverRole = ucr.get('server/role')
	assert serverRole in ('domaincontroller_slave', 'domaincontroller_backup', 'domaincontroller_master')

	# get the number of join scripts
	nJoinScripts = len(glob.glob('/usr/lib/univention-install/*.inst'))
	stepsPerScript = 100.0 / nJoinScripts

	# disable UMC/apache restart
	MODULE.info('disabling UMC and apache server restart')
	subprocess.call(CMD_DISABLE_EXEC)

	try:
		with tempfile.NamedTemporaryFile() as passwordFile:
			passwordFile.write('%s' % password)
			passwordFile.flush()

			# regular expressions for output parsing
			regError = re.compile('^\* Message:\s*(?P<message>.*)\s*$')
			regJoinScript = re.compile('(Configure|Running)\s+(?P<script>.*)\.inst.*$')
			regInfo = re.compile('^(?P<message>.*?)\s*:?\s*\x1b.*$')

			# call to univention-join
			process = None
			if serverRole == 'domaincontroller_slave':
				# DC slave -> complete re-join
				MODULE.process('Performing system join...')
				process = subprocess.Popen(['/usr/sbin/univention-join', '-dcaccount', username, '-dcpwd', passwordFile.name], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			else:
				# DC backup/master -> only run join scripts
				MODULE.process('Executing join scripts ...')
				process = subprocess.Popen(['/usr/sbin/univention-run-join-scripts', '-dcaccount', username, '-dcpwd', passwordFile.name], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

			failedJoinScripts = []
			while True:
				# get the next line
				line = process.stdout.readline()
				if not line:
					# no more text from stdout
					break
				MODULE.process(line.strip())

				# parse output... first check for errors
				m = regError.match(line)
				if m:
					error_handler(_('Software packages have been installed, however, the system join could not be completed: %s. More details can be found in the log file /var/log/univention/join.log. Please retry the join process via the UMC module "Domain join" after resolving any conflicting issues.') % m.groupdict().get('message'))
					continue

				# check for currently called join script
				m = regJoinScript.match(line)
				if m:
					info_handler(_('Executing join script %s') % m.groupdict().get('script'))
					step_handler(stepsPerScript)
					if 'failed' in line:
						failedJoinScripts.append(m.groupdict().get('script'))
					continue

				# check for other information
				m = regInfo.match(line)
				if m:
					info_handler(m.groupdict().get('message'))
					continue

			# get all remaining output
			stdout, stderr = process.communicate()
			if stderr:
				# write stderr into the log file
				MODULE.warn('stderr from univention-join: %s' % stderr)

			success = True
			# check for errors
			if process.returncode != 0:
				# error case
				MODULE.warn('Could not perform system join: %s%s' % (stdout, stderr))
				success = False
			elif failedJoinScripts:
				MODULE.warn('The following join scripts could not be executed: %s' % failedJoinScripts)
				error_handler(_('Software packages have been installed sucessfully, however, some join scripts could not be executed. More details can be found in the log file /var/log/univention/join.log. Please retry to execute the join scripts via the UMC module "Domain join" after resolving any conflicting issues.'))
				success = False
			return success
	finally:
		# make sure that UMC servers and apache can be restarted again
		MODULE.info('enabling UMC and apache server restart')
		subprocess.call(CMD_ENABLE_EXEC)

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
			steps=100 * float(self.steps) / self.max_steps,
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
		self.package_manager.set_max_steps(100.0)

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

	@simple_response
	def query(self, **kwargs):
		"""Returns a dictionary of initial values for the form."""
		ucr.load()

		return {
			'server_role': ucr.get('server/role'),
			'joined': os.path.exists('/var/univention-join/joined'),
			'samba': self.get_samba_version(),
			'ucsschool': self.get_ucs_school_version(),
			'guessed_master': get_master_dns_lookup(),
		}

	@simple_response
	def progress(self):
		return self.progress_state.poll()

	@sanitize(
		master=HostSanitizer(required=True, regex_pattern=RE_HOSTNAME),
		username=StringSanitizer(required=True),
		password=StringSanitizer(required=True),
		schoolOU=StringSanitizer(required=True),
	)
	def get_schoolinfo(self, request):
		username = request.options.get('username')
		password = request.options.get('password')
		master = request.options.get('master')
		schoolOU = request.options.get('schoolOU')

		serverRole = ucr.get('server/role')
		if serverRole != 'domaincontroller_slave':
			# use the credentials of the currently authenticated user on a master/backup system
			username = self._username
			password = self._password
			master = '%s.%s' % (ucr.get('hostname'), ucr.get('domainname'))
		if serverRole == 'domaincontroller_backup':
			master = ucr.get('ldap/master')

		# check for valid school OU
		if not RE_OU.match(schoolOU):
			result = {'success': False, 'error': _('The specified school OU is not valid.')}
		else:
			# get OU information
			result = self._get_schoolinfo(self, username, password, master, schoolOU)
		self.finished(request.id, result)

	def _get_schoolinfo(self, username, password, master, schoolOU):
		"""
		Fetches LDAP information from master about specified OU.
		This function assumes that the given arguments have already been validated!
		"""

		# try to query the LDAP base of the master
		try:
			ucrMaster = get_ucr_master(username, password, master, 'ldap/base', 'ldap/master/port')
		except RuntimeError as err:
			MODULE.warn('Could not query the LDAP base of the master system %s.' % master)
			return {'success': False, 'error': str(err)}

		values = {'exists': False,
				  'school': schoolOU,
				  'classShareServer': None,
				  'homeShareServer': None,
				  'educational_slaves': [],
				  'administrative_slaves': [],
				  }

		try:
			# get the userDN from the master
			userDN = get_user_dn(username, password, master)
			lo = univention.admin.uldap.access(host=master, base=ucrMaster.get('ldap/base'), port=int(ucrMaster.get('ldap/master/port', '7389')), binddn=userDN, bindpw=password)

			# initialize required UDM modules
			for module_name in ('computers/domaincontroller_slave', 'container/ou'):
				module = udm_modules.get(module_name)
				position = univention.admin.uldap.position(ucrMaster.get('ldap/base'))
				udm_modules.init(lo, position, module)

			# check if the OU already exists
			result = udm_modules.lookup('container/ou', None, lo, base=ucrMaster.get('ldap/base'), scope='sub', filter='(&(objectClass=ucsschoolOrganizationalUnit)(name=%s))' % schoolOU)
			if result:
				# OU already exists...
				values['exists'] = True
				values['classShareServer'] = result[0].get('ucsschoolClassShareFileServer')
				values['homeShareServer'] = result[0].get('ucsschoolHomeShareFileServer')
				# ...find all joined slave systems in the ou
				searchBase = SchoolSearchBase([schoolOU], ldapBase=ucrMaster.get('ldap/base'))
				slaves = udm_modules.lookup('computers/domaincontroller_slave', None, lo, base=searchBase.computers, scope='sub', filter='service=LDAP')

				# make sure that no joined DC slave is the main DC for this school
				for islave in slaves:
					islave.open()
					if searchBase.educationalDCGroup in islave['groups']:
						values['educational_slaves'].append(islave['name'])
					if searchBase.administrativeDCGroup in islave['groups']:
						values['administrative_slaves'].append(islave['name'])
		except univention.uldap.ldap.LDAPError as err:
			MODULE.warn('LDAP connection to %s failed: %s' % (master, err))
			return {'success': False, 'error': _('The LDAP connection to the master system %s failed.') % master}

		return {'success': True, 'schoolinfo': values}


	@sanitize(
		username=StringSanitizer(required=True),
		password=StringSanitizer(required=True),
		master=HostSanitizer(required=True, regex_pattern=RE_HOSTNAME),
		samba=ChoicesSanitizer(['3', '4']),
		schoolOU=StringSanitizer(required=True),
		setup=ChoicesSanitizer(['multiserver', 'singlemaster']),
		server_type=ChoicesSanitizer(['educational', 'administrative']),
		name_edu_server=HostSanitizer(regex_pattern=RE_HOSTNAME),
	)
	def install(self, request):
		# get all arguments
		username = request.options.get('username')
		password = request.options.get('password')
		master = request.options.get('master')
		samba = request.options.get('samba')
		schoolOU = request.options.get('schoolOU')
		educational_slave = request.options.get('name_edu_server')
		OUdisplayname = request.options.get('OUdisplayname', schoolOU)  # use school OU name as fallback
		server_type = request.options.get('server_type')
		setup = request.options.get('setup')
		serverRole = ucr.get('server/role')
		joined = os.path.exists('/var/univention-join/joined')

		if serverRole != 'domaincontroller_slave':
			# use the credentials of the currently authenticated user on a master/backup system
			username = self._username
			password = self._password
			master = '%s.%s' % (ucr.get('hostname'), ucr.get('domainname'))
		if serverRole == 'domaincontroller_backup':
			master = ucr.get('ldap/master')

		certOrigFile = None
		def _error(msg):
			# restore the original certificate... this is done at any error before the system join
			restoreOrigCertificate(certOrigFile)

			# finish the request with an error
			result = {'success' : False, 'error' : msg}
			self.finished(request.id, result)

		# check for valid school OU
		if ((setup == 'singlemaster' and serverRole == 'domaincontroller_master') or serverRole == 'domaincontroller_slave' ) and not RE_OU.match(schoolOU):
			_error(_('The specified school OU is not valid.'))
			return

		# check for valid server role
		if serverRole not in ('domaincontroller_master', 'domaincontroller_backup', 'domaincontroller_slave'):
			_error(_('Invalid server role! UCS@school can only be installed on the system roles master domain controller, backup domain controller, or slave domain controller.'))
			return

		if serverRole != 'domaincontroller_master':
			# check for a compatible environment on the DC master
			try:
				schoolVersion = get_remote_ucs_school_version(username, password, master)
				if not schoolVersion:
					_error(_('Please install UCS@school on the master domain controller system. Cannot proceed installation on this system.'))
					return
				if serverRole == 'domaincontroller_slave' and schoolVersion != 'multiserver':
					_error(_('The master domain controller is not configured for a UCS@school multi server environment. Cannot proceed installation on this system.'))
					return
				if serverRole == 'domaincontroller_backup' and schoolVersion != setup:
					_error(_('The UCS@school master domain controller needs to be configured similarly to this backup system. Please choose the correct environment type for this system.'))
					return
				if serverRole == 'domaincontroller_backup' and not joined:
					_error(_('In order to install UCS@school on a backup domain controller, the system needs to be joined first.'))
					return
			except socket.gaierror as e:
				MODULE.warn('Could not connect to master system %s: %s' % (master, e))
				_error(_('Cannot connect to the master domain controller system %s. Please make sure that the system is reachable. If not this could be due to wrong DNS nameserver settings.') % master)
				return
			except paramiko.SSHException as e:
				MODULE.warn('Could not connect to master system %s: %s' % (master, e))
				_error(_('Cannot connect to the master domain controller system %s. It seems that the specified domain credentials are not valid.') % master)
				return

		if serverRole == 'domaincontroller_slave':
			# on slave systems, download the certificate from the master in order
			# to be able to build up secure connections
			certOrigFile = retrieveRootCertificate(master)

			schoolinfo = self._get_schoolinfo(username, password, master, schoolOU)
			if not schoolinfo.get('success'):
				MODULE.error('Failed to get schoolinfo for school %r:\n%r' % (schoolOU, schoolinfo))
				_error(schoolinfo.get('msg', _('The LDAP connection to the master system %s failed.') % (master,)))
				return

		# everything ok, try to acquire the lock for the package installation
		lock_aquired = self.package_manager.lock(raise_on_fail=False)
		if not lock_aquired:
			MODULE.warn('Could not aquire lock for package manager')
			_error(_('Cannot get lock for installation process. Another package manager seems to block the operation.'))
			return

		# see which packages we need to install
		MODULE.process('performing UCS@school installation')
		installPackages = []
		sambaVersionInstalled = self.get_samba_version()
		if serverRole == 'domaincontroller_slave':
			# slave
			# Please note that the UCS installer only installs univention-samba. To install UCS@school on a Samba 3 system,
			# the packages "univention-samba-slave-pdc" AND "ucs-school-slave" have to be installed together or consecutively
			# in that order. Otherwise ucs-school-slave always installs samba 4.
			if samba == '3':
				installPackages.extend(['univention-samba', 'univention-samba-slave-pdc'])
			elif samba == '4':
				installPackages.extend(['univention-samba4', 'univention-s4-connector'])
			elif sambaVersionInstalled == 3:  # safety fallback if samba is unset
				installPackages.extend(['univention-samba', 'univention-samba-slave-pdc'])
			elif sambaVersionInstalled == 4:  # safety fallback if samba is unset
				installPackages.extend(['univention-samba4', 'univention-s4-connector'])
			if server_type == 'educational':
				installPackages.append('ucs-school-slave')
			else:
				installPackages.append('ucs-school-nonedu-slave')
		else:
			# master or backup
			if setup == 'singlemaster':
				if sambaVersionInstalled:
					# do not install samba a second time
					pass
				elif samba == '3':
					installPackages.append('univention-samba')
				else:  # -> samba4
					installPackages.extend(['univention-samba4', 'univention-s4-connector'])
				installPackages.append('ucs-school-singlemaster')
			elif setup == 'multiserver':
				installPackages.append('ucs-school-master')
			else:
				_error(_('Invalid UCS@school configuration.'))
				return
		MODULE.info('Packages to be installed: %s' % ', '.join(installPackages))

		# reset the current installation progress
		steps = 100  # installation -> 100
		if serverRole != 'domaincontroller_backup' and not (serverRole == 'domaincontroller_master' and setup == 'multiserver'):
			steps += 10  # create_ou -> 10
		if serverRole == 'domaincontroller_slave':
			steps += 10  # move_slave_into_ou -> 10
		steps += 100  # system_join -> 100 steps

		progress_state = self.progress_state
		progress_state.reset(steps)
		progress_state.component = _('Installation of UCS@school packages')
		self.package_manager.reset_status()

		def _thread(_self, packages):
			# perform installation
			success = True
			MODULE.process('Starting package installation')
			with _self.package_manager.locked(reset_status=True, set_finished=True):
				with _self.package_manager.no_umc_restart(exclude_apache=True):
					success = _self.package_manager.install(*packages)
			MODULE.info('Result of package installation: success=%s' % success)

			# check for errors
			if not success:
				restoreOrigCertificate(certOrigFile)
				return success

			if serverRole != 'domaincontroller_backup' and not (serverRole == 'domaincontroller_master' and setup == 'multiserver'):
				# create the school OU (not on backup and not on master w/multi server environment)
				MODULE.info('Starting creation of LDAP school OU structure...')
				progress_state.component = _('Creation of LDAP school structure')
				progress_state.info = ''
				if serverRole == 'domaincontroller_slave':
					# create ou remotely on the slave
					if server_type == 'educational':
						success = create_ou_remote(master, username, password, schoolOU, OUdisplayname, ucr.get('hostname'))
					else:
						# create DC in administrative network
						success = create_ou_remote(master, username, password, schoolOU, OUdisplayname, educational_slave, ucr.get('hostname'))
				elif serverRole == 'domaincontroller_master':
					# create ou locally on the master
					success = create_ou_local(schoolOU, OUdisplayname)

				progress_state.add_steps(10)
				if success:
					MODULE.info('created school OU')
				else:
					MODULE.error('Could not create school OU')
					progress_state.error_handler(_('The UCS@school software packages have been installed, however, a school OU could not be created and consequently a re-join of the system has not been performed. Please create a new school OU structure using the UMC module "Add school" on the master and perform a domain join on this machine via the UMC module "Domain join".' ))
					restoreOrigCertificate(certOrigFile)
					return success

			if serverRole == 'domaincontroller_slave':
				# make sure that the slave is correctly moved below its OU
				if not move_slave_into_ou(master, username, password, schoolOU, ucr.get('hostname')):
					# error case
					progress_state.error_handler(_('Validating the LDAP school OU structure failed. It seems that the current slave system has already been assigned to a different school or that the specified school OU name is already in use.'))
					restoreOrigCertificate(certOrigFile)
					return False

			# system join on a slave system
			progress_state.component = _('Domain join')
			if serverRole == 'domaincontroller_slave':
				progress_state.info = _('Preparing domain join...')
				MODULE.process('Starting system join...')
			else:  # run join scripts on DC backup/master
				progress_state.info = _('Executing join scripts...')
				MODULE.process('Running join scripts...')
			success = system_join(
				username, password,
				info_handler=self.progress_state.info_handler,
				step_handler=self.progress_state.add_steps,
				error_handler=self.progress_state.error_handler,
			)

			return success

		def _finished(thread, result):
			MODULE.info('Finished installation')
			progress_state.info = _('finished...')
			progress_state.finish()
			if isinstance(result, BaseException):
				msg = '%s\n%s: %s\n' % ( ''.join( traceback.format_tb( thread.exc_info[ 2 ] ) ), thread.exc_info[ 0 ].__name__, str( thread.exc_info[ 1 ] ) )
				MODULE.warn('Exception during installation: %s' % msg)
				progress_state.error_handler(_('An unexpected error occurred during installation: %s') % result)

		# launch thread
		thread = notifier.threads.Simple('ucsschool-install',
			notifier.Callback(_thread, self, installPackages),
			notifier.Callback(_finished)
		)
		thread.run()

		# finish request
		self.finished(request.id, { 'success': True })

