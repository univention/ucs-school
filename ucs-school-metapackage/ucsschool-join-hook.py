#!/usr/bin/python
#

import optparse
import logging
import subprocess
import sys
import os
import json
from collections import namedtuple
from ldap.filter import filter_format
import univention.uldap
from univention.config_registry import ConfigRegistry
from univention.lib.package_manager import PackageManager

log = logging.getLogger(__name__)
ucr = ConfigRegistry()
ucr.load()

StdoutStderr = namedtuple('StdoutStderr', 'stdout stderr')
SchoolMembership = namedtuple('school_membership', 'is_edu_school_member is_admin_school_member')

def get_lo(options):
	log.info('Connecting to LDAP as %r ...', options.binddn)
	try:
		lo = univention.admin.uldap.access(
			host=options.master_fqdn,
			port=int(ucr.get('ldap/master/port', '7389')),
			base=ucr.get('ldap/base'),
			binddn=options.binddn,
			bindpw=options.bindpw)
	except univention.admin.uexceptions.authFail:
		log.error('username or password is incorrect')
		sys.exit(5)
	return lo


def get_school_membership(options):  # type: (Any) -> SchoolMembership
	filter_s = filter_format('(&(cn=univentionGroup)(uniqueMember=%s))', (ucr.get('ldap/hostdn'),))
	grp_dn_list = options.lo.searchDn(filter=filter_s)
	is_edu_school_member = False
	is_admin_school_member = False
	for grp_dn in grp_dn_list:
		# is grp_dn in list of global school groups?
		if grp_dn in (
				'cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')),
				'cn=Member-Edukativnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')),
				):
			log.debug('host is in group %s', grp_dn)
			is_edu_school_member = True
		if grp_dn in (
				'cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')),
				'cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')),
				):
			log.debug('host is in group %s', grp_dn)
			is_admin_school_member = True
		# is dn in list of OU specific school groups?
		if not grp_dn.startswith('cn=OU'):
			continue
		for suffix in (
				'-DC-Edukativnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')),
				'-Member-Edukativnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')),
				):
			if grp_dn.endswith(suffix):
				log.debug('host is in group %s', grp_dn)
				is_edu_school_member = True
		for suffix in (
				'-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')),
				'-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}'.format(ucr.get('ldap/base')),
				):
			if grp_dn.endswith(suffix):
				log.debug('host is in group %s', grp_dn)
				is_admin_school_member = True
	return SchoolMembership(is_edu_school_member, is_admin_school_member)


def determine_role_packages(options):
	if options.server_role in ('domaincontroller_master',):
		return []
	if options.server_role in ('domaincontroller_backup',):
		return ['ucs-school-backup']
	if options.server_role in ('domaincontroller_slave',):
		membership = get_school_membership(options)
		if membership.is_edu_school_member:
			return ['ucs-school-slave']
		elif membership.is_admin_school_member:
			return ['ucs-school-nonedu-slave']
		else:
			return ['ucs-school-central-slave']
	if options.server_role in ('memberserver',):
		return []
	log.warn('System role %r not found!', options.server_role)
	return []


def call_cmd(options, cmd, on_master=False):  # type: (Any, Union[str, List[str]], Optional[bool]) -> StdoutStderr
	if on_master:
		assert isinstance(cmd, str)
		cmd = ['univention-ssh', '/etc/machine.secret', '{}$@{}'.format(ucr.get('hostname'), options.master_fqdn), cmd]
	else:
		assert isinstance(cmd, (list, tuple))
	proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = proc.communicate()
	if proc.returncode:
		log.error('%s returned with exitcode %s:\n%s\n%s', ' '.join(cmd), proc.returncode, stderr, stdout)
		sys.exit(1)
	return StdoutStderr(stdout, stderr)

def pre_joinscript_hook(options):
	package_manager = PackageManager(lock=False, always_noninteractive=True)

	# check if UCS@school app is installed/configured/included,
	# if not, then install the same version used by domaincontroller_master
	result = call_cmd(options, ['univention-app', 'info', '--as-json'], on_master=False)
	local_status = json.loads(result.stdout)
	ucsschool_installed = any(x.startswith('ucsschool=') for x in local_status.get('installed', []))
	if not ucsschool_installed:
		result = call_cmd(options, 'ucr get version/version', on_master=True)
		master_version = result.stdout.strip()
		result = call_cmd(options, ['ucr', 'get', 'version/version'], on_master=False)
		local_version = result.stdout.strip()
		app_string = 'ucsschool'
		if master_version == local_version:
			result = call_cmd(options, 'univention-app info --as-json', on_master=True)
			master_app_info = json.loads(result.stdout)
			# master_app_info:  {"compat": "4.3-1 errata0", "upgradable": [], "ucs": "4.3-1 errata0", "installed": ["ucsschool=4.3 v5"]}

			for app_entry in master_app_info.get('installed', []):
				app_name, app_version = app_entry.split('=', 1)
				if app_name == 'ucsschool':
					app_string = '%s=%s' % (app_string, app_version)
					break
			else:
				log.error(
					'UCS@school does not seem to be installed on %s! Cannot get app version of UCS@school on DC master!',
					options.master_fqdn)
				sys.exit(1)

		log.info('Installing %s ...', app_string)
		cmd = [
			'univention-app',
			'install',
			app_string,
			'--skip-check must_have_valid_license',
			'--do-not-call-join-scripts'
		]
		returncode = subprocess.call(cmd)
		if returncode:
			log.error('%s failed with exit code %s!', ' '.join(cmd), returncode)
			sys.exit(1)

	# if not all packages are installed, then try to install them again
	pkg_list = determine_role_packages(options)
	if not all(package_manager.is_installed(pkg_name) for pkg_name in pkg_list):
		subprocess.call(['univention-install', '--force-yes', '--yes'] + pkg_list)


def main():
	global log
	global lo

	parser = optparse.OptionParser()
	parser.add_option('--server-role', dest='server_role', default=None, action='store', help='server role of this system')
	parser.add_option('--master', dest='master_fqdn', action='store', default=None, help='FQDN of the UCS master domaincontroller')
	parser.add_option('--binddn', dest='binddn', action='binddn', default=None, help='LDAP binddn')
	parser.add_option('--bindpwdfile', dest='bindpwdfile', action='store', default=None, help='path to password file')
	parser.add_option('--type', dest='hook_type', action='store', default=None, help='join hook type (currently only "pre-joinscript" supported)')
	parser.add_option('-v', '--verbose', action='count', default=2, help='Increase verbosity')
	(options, args) = parser.parse_args()

	if not options.server_role:
		parser.error('Please specify a server role')
	if not options.master:
		parser.error('Please specify a FQDN for the master domaincontroller')
	if not options.binddn:
		parser.error('Please specify a LDAP binddn')
	if not options.bindpwdfile:
		parser.error('Please specify a path to a file with a LDAP password')
	if not os.path.isfile(options.bindpwdfile):
		parser.error('The given path for --bindpwdfile is not valid')
	if not options.hook_type:
		parser.error('Please specify a hook type')
	if options.hook_type in ('pre-join', 'post-joinscript'):
		parser.error('The specified hook type is not supported by this script')

	options.bindpw = open(options.bindpwdfile, 'r').read()

	LEVELS = [logging.FATAL, logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
	try:
		level = LEVELS[options.verbose]
	except IndexError:
		level = LEVELS[-1]
	logging.basicConfig(stream=sys.stderr, level=level)

	log = logging.getLogger(__name__)
	options.lo = get_lo(options)

	pre_joinscript_hook(options)

if __name__ == '__main__':
	main()
