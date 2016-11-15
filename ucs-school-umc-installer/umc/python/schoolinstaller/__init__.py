#!/usr/bin/python2.7
#
# Univention Management Console
#  This installation wizard guides the installation of UCS@school in the domain
#
# Copyright 2013-2016 Univention GmbH
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

import threading
import os.path
import os
import socket
import re
import tempfile
import glob
import subprocess
import traceback
import urllib
import filecmp
import fcntl
import errno
from httplib import HTTPException

import notifier
import notifier.threads
import dns.resolver
import dns.exception
import ldap

from univention.lib.package_manager import PackageManager
from univention.lib.umc_connection import UMCConnection
from univention.admin.uexceptions import noObject
from univention.management.console.base import Base, UMC_Error
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.ldap import get_machine_connection
from univention.management.console.modules.decorators import simple_response, sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, ChoicesSanitizer

from ucsschool.lib.models import School, SchoolDCSlave

from univention.lib.i18n import Translation

_ = Translation('ucs-school-umc-installer').translate
os.umask(0o022)  # switch back to default umask

RE_FQDN = re.compile('^[a-z]([a-z0-9-]*[a-z0-9])*\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*$')
RE_HOSTNAME = re.compile('^[a-z]([a-z0-9-]*[a-z0-9])*(\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*)?$')  # keep in sync with schoolinstaller.js widgets.master.regExp
RE_HOSTNAME_OR_EMPTY = re.compile('^([a-z]([a-z0-9-]*[a-z0-9])*(\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*)?)?$')
RE_OU = re.compile('^[a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?$')
RE_OU_OR_EMPTY = re.compile('^([a-zA-Z0-9](([a-zA-Z0-9_]*)([a-zA-Z0-9]$))?)?$')

CMD_ENABLE_EXEC = ['/usr/share/univention-updater/enable-apache2-umc', '--no-restart']
CMD_DISABLE_EXEC = '/usr/share/univention-updater/disable-apache2-umc'

CERTIFICATE_PATH = '/etc/univention/ssl/ucsCA/CAcert.pem'

# class SetupSanitizer(StringSanitizer):
#
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
		if not value:
			return ''
		try:
			return socket.getfqdn(value)
		except socket.gaierror:
			# invalid FQDN
			self.raise_validation_error(_('The entered FQDN is not a valid value'))


class SchoolInstallerError(UMC_Error):
	pass


def get_master_dns_lookup():
	# DNS lookup for the DC master entry
	try:
		query = '_domaincontroller_master._tcp.%s.' % ucr.get('domainname')
		resolver = dns.resolver.Resolver()
		resolver.lifetime = 6.0
		result = resolver.query(query, 'SRV')
		if result:
			return result[0].target.canonicalize().split(1)[0].to_text()
	except dns.resolver.NXDOMAIN:
		MODULE.error('Error to perform a DNS query for service record: %s' % (query,))
	except dns.resolver.NoAnswer:
		MODULE.error('Got non authoritative answer in DNS query for service record: %s' % (query,))
	except dns.resolver.Timeout:
		MODULE.error('DNS query for service record of %s timed out.' % (query,))
	except dns.exception.DNSException as exc:
		MODULE.error('DNSException during query for %s: %s' % (query, exc))
	return ''


def umc(username, password, master, path='', options=None, flavor=None, command='command'):
	connection = UMCConnection(master, username, password, error_handler=MODULE.warn)
	MODULE.info('Executing on %r: %r %r flavor=%r options=%r' % (master, command, path, flavor, options))
	return connection.request(path or '', options, flavor, command=command)


def create_ou_local(ou, display_name):
	'''Calls create_ou locally as user root (only on master).'''
	if not display_name:
		MODULE.warn('create_ou_local(): display name is undefined - using OU name as display name')
		display_name = ou

	# call create_ou
	cmd = ['/usr/share/ucs-school-import/scripts/create_ou', '--displayName', display_name, ou]
	MODULE.info('Executing: %s' % ' '.join(cmd))
	process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()

	# check for errors
	if process.returncode != 0:
		raise SchoolInstallerError('Failed to execute create_ou: %s\n%s%s' % (cmd, stderr, stdout))


def create_ou_remote(master, username, password, ou, display_name, educational_slave, administrative_slave=None):
	"""Create a school OU via the UMC interface."""
	options = {'name': ou, 'display_name': display_name, 'dc_name': educational_slave}
	if administrative_slave:
		options['dc_name_administrative'] = administrative_slave
	try:
		umc(username, password, master, 'schoolwizards/schools/create', [{'object': options}], 'schoolwizards/schools')
	except (EnvironmentError, HTTPException) as exc:
		raise SchoolInstallerError('Failed creating OU: %s' % (exc,))


def system_join(username, password, info_handler, error_handler, step_handler):
	# make sure we got the correct server role
	server_role = ucr.get('server/role')
	assert server_role in ('domaincontroller_slave', 'domaincontroller_backup', 'domaincontroller_master')

	# get the number of join scripts
	n_joinscripts = len(glob.glob('/usr/lib/univention-install/*.inst'))
	steps_per_script = 100.0 / n_joinscripts

	# disable UMC/apache restart
	MODULE.info('disabling UMC and apache server restart')
	subprocess.call(CMD_DISABLE_EXEC)

	try:
		with tempfile.NamedTemporaryFile() as password_file:
			password_file.write('%s' % password)
			password_file.flush()

			# regular expressions for output parsing
			error_pattern = re.compile('^\* Message:\s*(?P<message>.*)\s*$')
			joinscript_pattern = re.compile('(Configure|Running)\s+(?P<script>.*)\.inst.*$')
			info_pattern = re.compile('^(?P<message>.*?)\s*:?\s*\x1b.*$')

			# call to univention-join
			process = None
			if server_role == 'domaincontroller_slave':
				# DC slave -> complete re-join
				MODULE.process('Performing system join...')
				process = subprocess.Popen(['/usr/sbin/univention-join', '-dcaccount', username, '-dcpwd', password_file.name], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			else:
				# DC backup/master -> only run join scripts
				MODULE.process('Executing join scripts ...')
				process = subprocess.Popen(['/usr/sbin/univention-run-join-scripts', '-dcaccount', username, '-dcpwd', password_file.name], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

			failed_join_scripts = []

			def parse(line):
				MODULE.process(repr(line.strip()).strip('"\''))

				# parse output... first check for errors
				m = error_pattern.match(line)
				if m:
					error_handler(_('Software packages have been installed, however, the system join could not be completed: %s. More details can be found in the log file /var/log/univention/join.log. Please retry the join process via the UMC module "Domain join" after resolving any conflicting issues.') % m.groupdict().get('message'))
					return

				# check for currently called join script
				m = joinscript_pattern.match(line)
				if m:
					info_handler(_('Executing join script %s') % m.groupdict().get('script'))
					step_handler(steps_per_script)
					if 'failed' in line:
						failed_join_scripts.append(m.groupdict().get('script'))
					return

				# check for other information
				m = info_pattern.match(line)
				if m:
					info_handler(m.groupdict().get('message'))
					return

			# make stdout file descriptor of the process non-blocking
			fd = process.stdout.fileno()
			fl = fcntl.fcntl(fd, fcntl.F_GETFL)
			fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

			unfinished_line = ''
			while True:
				# get the next line
				try:
					line = process.stdout.read()
				except IOError as exc:
					if exc.errno == errno.EAGAIN:
						continue
					raise

				if not line:
					break  # no more text from stdout

				unfinished_line = '' if line.endswith('\n') else '%s%s' % (unfinished_line, line.rsplit('\n', 1)[-1])
				for line in line.splitlines():
					parse(line)
				if unfinished_line:
					parse(unfinished_line)

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
			elif failed_join_scripts:
				MODULE.warn('The following join scripts could not be executed: %s' % failed_join_scripts)
				error_handler(_('Software packages have been installed successfully, however, some join scripts could not be executed. More details can be found in the log file /var/log/univention/join.log. Please retry to execute the join scripts via the UMC module "Domain join" after resolving any conflicting issues.'))
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

	def add_steps(self, steps=1):
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
		self.original_certificate_file = None

	def error_handling(self, etype, exc, etraceback):
		if isinstance(exc, SchoolInstallerError):
			# restore the original certificate... this is done at any error before the system join
			self.restore_original_certificate()

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
		elif self.package_manager.is_installed('ucs-school-slave') or self.package_manager.is_installed('ucs-school-nonedu-slave') or self.package_manager.is_installed('ucs-school-master'):
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
			'hostname': ucr.get('hostname'),
		}

	@simple_response
	def progress(self):
		return self.progress_state.poll()

	@sanitize(
		schoolOU=StringSanitizer(required=True, regex_pattern=RE_OU),
	)
	def get_schoolinfo(self, request):
		school = request.options['schoolOU']

		server_role = ucr.get('server/role')
		if server_role == 'domaincontroller_master':
			self.finished(request.id, self._get_schoolinfo(school))
			return

		if server_role == 'domaincontroller_backup':
			# use the credentials of the currently authenticated user on a backup system
			self.require_password()
			request.options['master'] = ucr.get('ldap/master')
			request.options['username'] = self.username
			request.options['password'] = self.password

		self.get_schoolinfo_slave(request)

	@sanitize(
		master=HostSanitizer(required=True, regex_pattern=RE_HOSTNAME),  # TODO: add regex error message; Bug #42955
		username=StringSanitizer(required=True, minimum=1),
		password=StringSanitizer(required=True, minimum=1),
		schoolOU=StringSanitizer(required=True, regex_pattern=RE_OU),  # TODO: add regex error message
	)
	@simple_response
	def get_schoolinfo_slave(self, username, password, master, schoolOU):
		return self._get_schoolinfo_from_master(username, password, master, schoolOU)

	def _get_schoolinfo_from_master(self, username, password, master, school):
		try:
			try:
				return umc(username, password, master, 'schoolinstaller/get/schoolinfo', {'master': None, 'username': None, 'password': None, 'schoolOU': school})
			except NotImplementedError:
				raise HTTPException(_('Make sure ucs-school-umc-installer is installed on the DC Master and all join scripts are executed.'))
		except HTTPException as exc:
			raise SchoolInstallerError(_('Could not connect to the DC Master %s: %s') % (master, exc))  # TODO: set status, message, result

	def _get_schoolinfo(self, school_ou):
		"""
		Fetches LDAP information from master about specified OU.
		This function assumes that the given arguments have already been validated!
		"""

		try:
			lo, po = get_machine_connection(write=True)
			school = School.from_dn(School(name=school_ou).dn, None, lo)
		except noObject:
			exists = False
			class_share_server = None
			home_share_server = None
			educational_slaves = []
			administrative_slaves = []
		except ldap.SERVER_DOWN:
			raise  # handled via UMC
		except ldap.LDAPError as exc:
			MODULE.warn('LDAP error during receiving school info: %s' % (exc,))
			raise UMC_Error(_('The LDAP connection to the master system failed.'))
		else:
			exists = True
			class_share_server = school.class_share_file_server
			home_share_server = school.home_share_file_server
			educational_slaves = [SchoolDCSlave.from_dn(dn, None, lo).name for dn in school.educational_servers]
			administrative_slaves = [SchoolDCSlave.from_dn(dn, None, lo).name for dn in school.administrative_servers]

		school_version = None
		for package, version in (('ucs-school-singlemaster', 'singlemaster'), ('ucs-school-slave', 'multiserver'), ('ucs-school-master', 'multiserver')):
			package = self.package_manager.get_package(package)
			if package and package.is_installed:
				school_version = version
				break

		return {
			'exists': exists,
			'school': school_ou,
			'school_version': school_version,
			'classShareServer': class_share_server,
			'homeShareServer': home_share_server,
			'educational_slaves': educational_slaves,
			'administrative_slaves': administrative_slaves,
		}

	@sanitize(
		username=StringSanitizer(required=True),
		password=StringSanitizer(required=True),
		master=HostSanitizer(required=True, regex_pattern=RE_HOSTNAME_OR_EMPTY),
		samba=ChoicesSanitizer(['3', '4']),
		schoolOU=StringSanitizer(required=True, regex_pattern=RE_OU_OR_EMPTY, allow_none=True),
		setup=ChoicesSanitizer(['multiserver', 'singlemaster']),
		server_type=ChoicesSanitizer(['educational', 'administrative']),
		nameEduServer=StringSanitizer(regex_pattern=RE_HOSTNAME_OR_EMPTY),  # javascript wizard page always passes value to backend, even if empty
	)
	def install(self, request):
		# get all arguments
		username = request.options.get('username')
		password = request.options.get('password')
		master = request.options.get('master')
		samba = request.options.get('samba')
		school_ou = request.options.get('schoolOU')
		educational_slave = request.options.get('nameEduServer')
		ou_display_name = request.options.get('OUdisplayname', school_ou)  # use school OU name as fallback
		server_type = request.options.get('server_type')
		setup = request.options.get('setup')
		server_role = ucr.get('server/role')
		joined = os.path.exists('/var/univention-join/joined')

		if server_role != 'domaincontroller_slave':
			# use the credentials of the currently authenticated user on a master/backup system
			self.require_password()
			username = self.username
			password = self.password
			master = '%s.%s' % (ucr.get('hostname'), ucr.get('domainname'))
		if server_role == 'domaincontroller_backup':
			master = ucr.get('ldap/master')

		self.original_certificate_file = None

		# check for valid school OU
		if ((setup == 'singlemaster' and server_role == 'domaincontroller_master') or server_role == 'domaincontroller_slave') and not RE_OU.match(school_ou):
			raise SchoolInstallerError(_('The specified school OU is not valid.'))

		# check for valid server role
		if server_role not in ('domaincontroller_master', 'domaincontroller_backup', 'domaincontroller_slave'):
			raise SchoolInstallerError(_('Invalid server role! UCS@school can only be installed on the system roles master domain controller, backup domain controller, or slave domain controller.'))

		if server_role == 'domaincontroller_slave' and not server_type:
			raise SchoolInstallerError(_('Server type has to be set for domain controller slave'))

		if server_role == 'domaincontroller_slave' and server_type == 'administrative' and not educational_slave:
			raise SchoolInstallerError(_('The name of an educational server has to be specified if the system shall be configured as administrative server.'))

		if server_role == 'domaincontroller_slave' and server_type == 'administrative' and educational_slave.lower() == ucr.get('hostname').lower():
			raise SchoolInstallerError(_('The name of the educational server may not be equal to the name of the administrative slave.'))

		if server_role == 'domaincontroller_slave':
			# on slave systems, download the certificate from the master in order
			# to be able to build up secure connections
			self.original_certificate_file = self.retrieve_root_certificate(master)

		if server_role != 'domaincontroller_master':
			# check for a compatible environment on the DC master

			schoolinfo = self._get_schoolinfo_from_master(username, password, master, school_ou)
			school_version = schoolinfo['school_version']
			if not school_version:
				raise SchoolInstallerError(_('Please install UCS@school on the master domain controller system. Cannot proceed installation on this system.'))
			if server_role == 'domaincontroller_slave' and school_version != 'multiserver':
				raise SchoolInstallerError(_('The master domain controller is not configured for a UCS@school multi server environment. Cannot proceed installation on this system.'))
			if server_role == 'domaincontroller_backup' and school_version != setup:
				raise SchoolInstallerError(_('The UCS@school master domain controller needs to be configured similarly to this backup system. Please choose the correct environment type for this system.'))
			if server_role == 'domaincontroller_backup' and not joined:
				raise SchoolInstallerError(_('In order to install UCS@school on a backup domain controller, the system needs to be joined first.'))

		# everything ok, try to acquire the lock for the package installation
		lock_aquired = self.package_manager.lock(raise_on_fail=False)
		if not lock_aquired:
			MODULE.warn('Could not aquire lock for package manager')
			raise SchoolInstallerError(_('Cannot get lock for installation process. Another package manager seems to block the operation.'))

		# see which packages we need to install
		MODULE.process('performing UCS@school installation')
		packages_to_install = []
		installed_samba_version = self.get_samba_version()
		if server_role == 'domaincontroller_slave':
			# slave
			# Please note that the UCS installer only installs univention-samba. To install UCS@school on a Samba 3 system,
			# the packages "univention-samba-slave-pdc" AND "ucs-school-slave" have to be installed together or consecutively
			# in that order. Otherwise ucs-school-slave always installs samba 4.
			if samba == '3':
				packages_to_install.extend(['univention-samba', 'univention-samba-slave-pdc'])
			elif samba == '4':
				packages_to_install.extend(['univention-samba4', 'univention-s4-connector'])
			elif installed_samba_version == 3:  # safety fallback if samba is unset
				packages_to_install.extend(['univention-samba', 'univention-samba-slave-pdc'])
			elif installed_samba_version == 4:  # safety fallback if samba is unset
				packages_to_install.extend(['univention-samba4', 'univention-s4-connector'])
			if server_type == 'educational':
				packages_to_install.append('ucs-school-slave')
			else:
				packages_to_install.append('ucs-school-nonedu-slave')
		else:  # master or backup
			if setup == 'singlemaster':
				if installed_samba_version:
					pass  # do not install samba a second time
				elif samba == '3':
					packages_to_install.append('univention-samba')
				else:  # -> samba4
					packages_to_install.extend(['univention-samba4', 'univention-s4-connector'])
				packages_to_install.append('ucs-school-singlemaster')
			elif setup == 'multiserver':
				packages_to_install.append('ucs-school-master')
			else:
				raise SchoolInstallerError(_('Invalid UCS@school configuration.'))
		MODULE.info('Packages to be installed: %s' % ', '.join(packages_to_install))

		# reset the current installation progress
		steps = 100  # installation -> 100
		if server_role != 'domaincontroller_backup' and not (server_role == 'domaincontroller_master' and setup == 'multiserver'):
			steps += 10  # create_ou -> 10
		if server_role == 'domaincontroller_slave':
			steps += 10  # move_slave_into_ou -> 10
		steps += 100  # system_join -> 100 steps

		progress_state = self.progress_state
		progress_state.reset(steps)
		progress_state.component = _('Installation of UCS@school packages')
		self.package_manager.reset_status()

		def _thread(_self, packages):
			MODULE.process('Starting package installation')
			with _self.package_manager.locked(reset_status=True, set_finished=True), _self.package_manager.no_umc_restart(exclude_apache=True):
				_self.package_manager.update()
				if not _self.package_manager.install(*packages):
					raise SchoolInstallerError(_('Failed to install packages.'))

			if server_role != 'domaincontroller_backup' and not (server_role == 'domaincontroller_master' and setup == 'multiserver'):
				# create the school OU (not on backup and not on master w/multi server environment)
				MODULE.info('Starting creation of LDAP school OU structure...')
				progress_state.component = _('Creation of LDAP school structure')
				progress_state.info = ''
				try:
					if server_role == 'domaincontroller_slave':
						_educational_slave = ucr.get('hostname') if server_type == 'educational' else educational_slave
						administrative_slave = None if server_type == 'educational' else ucr.get('hostname')
						create_ou_remote(master, username, password, school_ou, ou_display_name, _educational_slave, administrative_slave)
					elif server_role == 'domaincontroller_master':
						create_ou_local(school_ou, ou_display_name)
				except SchoolInstallerError as exc:
					MODULE.error(str(exc))
					raise SchoolInstallerError(_(
						'The UCS@school software packages have been installed, however, a school OU could not be created and consequently a re-join of the system has not been performed. '
						'Please create a new school OU structure using the UMC module "Add school" on the master and perform a domain join on this machine via the UMC module "Domain join".'
					))

				progress_state.add_steps(10)

			if server_role == 'domaincontroller_slave':
				# make sure that the slave is correctly moved below its OU
				MODULE.info('Trying to move the slave entry in the right OU structure...')
				result = umc(username, password, master, 'schoolwizards/schools/move_dc', {'schooldc': ucr.get('hostname'), 'schoolou': school_ou}, 'schoolwizards/schools')
				if not result.get('success'):
					MODULE.warn('Could not successfully move the slave DC into its correct OU structure:\n%s' % result.get('message'))
					raise SchoolInstallerError(_('Validating the LDAP school OU structure failed. It seems that the current slave system has already been assigned to a different school or that the specified school OU name is already in use.'))

			# system join on a slave system
			progress_state.component = _('Domain join')
			if server_role == 'domaincontroller_slave':
				progress_state.info = _('Preparing domain join...')
				MODULE.process('Starting system join...')
			else:  # run join scripts on DC backup/master
				progress_state.info = _('Executing join scripts...')
				MODULE.process('Running join scripts...')
			system_join(
				username, password,
				info_handler=self.progress_state.info_handler,
				step_handler=self.progress_state.add_steps,
				error_handler=self.progress_state.error_handler,
			)

		def _finished(thread, result):
			MODULE.info('Finished installation')
			progress_state.info = _('finished...')
			if isinstance(result, SchoolInstallerError):
				MODULE.warn('Error during installation: %s' % (result,))
				self.restore_original_certificate()
				progress_state.error_handler(str(result))
			elif isinstance(result, BaseException):
				self.restore_original_certificate()
				msg = ''.join(traceback.format_exception(*thread.exc_info))
				MODULE.error('Exception during installation: %s' % msg)
				progress_state.error_handler(_('An unexpected error occurred during installation: %s') % result)
			progress_state.finish()

		# launch thread
		thread = notifier.threads.Simple('ucsschool-install', notifier.Callback(_thread, self, packages_to_install), notifier.Callback(_finished))
		thread.run()

		# finish request
		self.finished(request.id, None)

	def retrieve_root_certificate(self, master):
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

		original_certificate_file = None
		# download the certificate from the DC master
		certificate_uri = 'http://%s/ucs-root-ca.crt' % (master,)
		MODULE.info('Downloading root certificate from: %s' % (master,))
		try:
			certificate_file, headers = urllib.urlretrieve(certificate_uri)

			if not filecmp.cmp(CERTIFICATE_PATH, certificate_file):
				# we need to update the certificate file...
				# save the original file first and make sure we do not override any existing file
				count = 1
				original_certificate_file = CERTIFICATE_PATH + '.orig'
				while os.path.exists(original_certificate_file):
					count += 1
					original_certificate_file = CERTIFICATE_PATH + '.orig%s' % count
				os.rename(CERTIFICATE_PATH, original_certificate_file)
				MODULE.info('Backing up old root certificate as: %s' % original_certificate_file)

				# place the downloaded certificate at the original position
				os.rename(certificate_file, CERTIFICATE_PATH)
				os.chmod(CERTIFICATE_PATH, 0o644)
		except EnvironmentError as exc:
			# print warning and ignore error
			MODULE.warn('Could not download root certificate [%s], error ignored: %s' % (certificate_uri, exc))
			self.original_certificate_file = original_certificate_file
			self.restore_original_certificate()

		return original_certificate_file

	def restore_original_certificate(self):
		# try to restore the original certificate file
		if self.original_certificate_file and os.path.exists(self.original_certificate_file):
			try:
				MODULE.info('Restoring original root certificate.')
				os.rename(self.original_certificate_file, CERTIFICATE_PATH)
			except EnvironmentError as exc:
				MODULE.warn('Could not restore original root certificate: %s' % (exc,))
			self.original_certificate_file = None
