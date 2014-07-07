
## -*- coding: utf-8 -*-
from essential.importcomputers import Windows, MacOS, IPManagedClient
from essential.internetrule import InternetRule
from ucsschool.lib.models import IPComputer as IPComputerLib
from ucsschool.lib.models import MacComputer as MacComputerLib
from ucsschool.lib.models import WindowsComputer as WindowsComputerLib
import essential.ucsschoo as utu
import re
import univention.testing.strings as uts
import univention.testing.utils as utils
import univention.lib.atjobs as ula
import datetime
import time
import copy
import subprocess
import tempfile
import univention.testing.ucr as ucr_test
from essential.simplecurl import SimpleCurl
from essential.workgroup import Workgroup

class ComputerImport(object):
	def __init__(self, school=None, nr_windows=1, nr_macos=0, nr_ipmanagedclient=0):
		self.school = school if school else uts.random_name()
		self.windows = []
		for i in range(0, nr_windows):
			self.windows.append(Windows(self.school))
		self.memberservers = []
		self.macos = []
		for i in range(0, nr_macos):
			self.macos.append(MacOS(self.school))
		self.ipmanagedclients = []
		for i in range(0, nr_ipmanagedclient):
			self.ipmanagedclients.append(IPManagedClient(self.school))

	def run_import(self, open_ldap_co):
		def _set_kwargs(computer):
			kwargs = {
					'school': computer.school,
					'name': computer.name,
					'ip_address': computer.ip,
					'mac_address': computer.mac,
					'type_name': computer.ctype,
					'inventory_number': computer.inventorynumbers,
					'zone': computer.zone,
			}
			return kwargs
		for computer in self.windows:
			kwargs = _set_kwargs(computer)
			WindowsComputerLib(**kwargs).create(open_ldap_co)
		for computer in self.macos:
			kwargs = _set_kwargs(computer)
			MacComputerLib(**kwargs).create(open_ldap_co)
		for computer in self.ipmanagedclients:
			kwargs = _set_kwargs(computer)
			IPComputerLib(**kwargs).create(open_ldap_co)

class Room(object):
	def __init__(self, school, name=None, dn=None, description=None, host_members=[]):
		self.school = school
		self.name = name if name else uts.random_name()
		self.dn = dn if dn else 'cn=%s-%s,cn=raeume,cn=groups,%s' % (
				school, self.name, utu.UCSTestSchool().get_ou_base_dn(school))
		self.description = description if description else uts.random_name()
		self.host_members = host_members

	def get_room_user(self, umc_connection):
		print 'Executing command: computerroom/rooms in school:', self.school
		reqResult = umc_connection.request('computerroom/rooms', {'school':self.school})
		return [x.get('user') for x in reqResult if x['label']==self.name][0]

	def check_room_user(self, umc_connection, expected_user):
		print 'Checking computer room(%s) users..........' % self.name
		current_user = self.get_room_user(umc_connection)
		print 'Room %s is in use by user %r' %(self.name, current_user)
		if current_user:
			user_id = re.search(r'\((\w+)\)', current_user).group(1)
		else:
			user_id = current_user
		if expected_user != user_id:
			utils.fail('Room in use by user %s, expected: %s' % (
				user_id, expected_user))

	def aquire_room(self, umc_connection):
		print 'Executing command: computerroom/room/acquire'
		reqResult = umc_connection.request(
				'computerroom/room/acquire', {'room': self.dn})
		return reqResult

	def checK_room_aquire(self, umc_connection, expected_answer):
		print 'Checking room aquire... (%s)' % self.name
		answer = self.aquire_room(umc_connection)['message']
		if answer == expected_answer:
			print 'Room %s is %s' %(self.name, answer)
		else:
			utils.fail('Unexpected room aquire result: %s' % (answer,))

	def get_room_computers(self, umc_connection):
		print 'Executing command: computerroom/query... (%s)' % self.name
		reqResult = umc_connection.request('computerroom/query', {'reload':False})
		return [x['name'] for x in reqResult]

	def check_room_computers(self, umc_connection, expected_computer_list):
		print 'Checking room computers........... (%s)' % self.name
		current_computers = self.get_room_computers(umc_connection)
		print 'Current computers in room %s are %r' % (self.name, current_computers)
		for i, computer in enumerate(sorted(current_computers)):
			if computer not in sorted(expected_computer_list)[i]:
				utils.fail('Computers found %r do not match the expected: %r' % (
					current_computers, expected_computer_list))

	def set_room_settings(self, umc_connection, new_settings):
		print 'Executing command: computerroom/settings/set'
		print 'new_settings = %r' % (new_settings,)
		reqResult = umc_connection.request('computerroom/settings/set', new_settings)
		return reqResult

	def get_room_settings(self, umc_connection):
		print 'Executing command: computerroom/settings/get'
		reqResult = umc_connection.request('computerroom/settings/get')
		return reqResult

	def check_room_settings(self, umc_connection, expected_settings):
		print 'Checking computerroom (%s) settings ...........' % self.name
		current_settings = self.get_room_settings(umc_connection)
		d = dict(expected_settings) # copy dictionary
		d['period'] = current_settings['period']
		if current_settings != d:
			utils.fail('Current settings (%r) do not match expected ones (%r)' % (
				current_settings, d))

	def get_internetRules(self, umc_connection):
		print 'Executing command: computerroom/internetrules'
		reqResult = umc_connection.request('computerroom/internetrules')
		return reqResult

	def check_internetRules(self, umc_connection):
		"""Check if the fetched internetrules match the already defined ones
		in define internet module.
		:param umc_connection: umc connection
		:type umc_connection: UMCConnection(uce.get('hostname'))
		"""
		rule = InternetRule()
		current_rules = rule.allRules()
		internetRules = self.get_internetRules(umc_connection)
		if (sorted(current_rules)!=sorted(internetRules)):
			utils.fail('Fetched internetrules %r, do not match the existing ones %r' % (
				internetRules, current_rules))

	def check_atjobs(self, period, expected_existance):
		for item in ula.list():
			if period == datetime.time.strftime(item.execTime.time(),'%H:%M'):
				exist = True
			else:
				exist = False
		if exist == expected_existance:
			print 'Atjob result at(%r) existance is expected (%r)' % (period, exist)
		else:
			utils.fail('Atjob result at(%r) existance is not expected (%r)' % (period, exist))

	def check_displayTime(self, umc_connection, period):
		displayed_period = self.get_room_settings(umc_connection)['period'][0:-3]
		if period == displayed_period:
			print 'Time dsiplayed (%r) is same as time at Atjobs (%r)' % (
				displayed_period, period)
		else:
			utils.fail('Time dsiplayed (%r) is different from time at Atjobs (%r)' % (
				displayed_period, period))

	def test_time_settings(self, umc_connection):
		self.aquire_room(umc_connection)
		settings = self.get_room_settings(umc_connection)
		period = datetime.time.strftime(
				(datetime.datetime.now() + datetime.timedelta(0,120)).time(), '%H:%M')
		new_settings = {
				'customRule':	'',
				'printMode':	'none',
				'internetRule': 'none',
				'shareMode':	'home',
				'period':		period
				}

		ula_length = len(ula.list())
		time_out = 30 # seconds
		self.set_room_settings(umc_connection, new_settings)
		for i in xrange(time_out, 0, -1):
			print i
			if len(ula.list()) > ula_length:
				break
			else:
				time.sleep(1)
				continue

		# Checking Atjobs list
		self.check_atjobs(period, True)

		#TODO FAILS because of Bug #35195
		self.check_displayTime(umc_connection, period)

		print '*** Waiting 2 mins for settings to expire.............'
		time.sleep(2 * 60 + 2)
		current_settings = self.get_room_settings(umc_connection)

		# Time field is not considered in the comparision
		current_settings['period'] = settings['period']
		if current_settings != settings:
			utils.fail('Current settings (%r) are not reset back after the time out, expected (%r)' % (
				current_settings, settings))

		# Checking Atjobs list
		self.check_atjobs(period, False)


	def check_home_read(self, user, ip_address, passwd='univention', expected_result=0):
		print '.... Check home read ....'
		cmd_read_home = ['smbclient', '//%(ip)s/%(username)s', '-U', '%(user)s', '-c', 'dir']
		read = run_commands(
				[cmd_read_home],
				{
					'ip':		ip_address,
					'username':	user,
					'user':		'{0}%{1}'.format(user,passwd)
					}
				)
		if read[0] != expected_result:
			utils.fail('Read home directory result (%r), expected (%r)' % (read[0], expected_result))

	def check_home_write(self, user, ip_address, passwd='univention', expected_result=0):
		print '.... Check home write ....'
		f = tempfile.NamedTemporaryFile(dir='/tmp')
		cmd_write_home = ['smbclient', '//%(ip)s/%(username)s', '-U', '%(user)s', '-c', 'put %(filename)s']
		write = run_commands(
				[cmd_write_home],
				{
					'ip':		ip_address,
					'username':	user,
					'user':		'{0}%{1}'.format(user,passwd),
					'filename': '%s %s' % (f.name, f.name.split('/')[-1])
					}
				)
		f.close()
		if write[0] != expected_result:
			utils.fail('Write to home directory result (%r), expected (%r)' % (write[0], expected_result))

	def check_marktplatz_read(self, user, ip_address, passwd='univention', expected_result=0):
		print '.... Check Marktplatz read ....'
		cmd_read_marktplatz = ['smbclient', '//%(ip)s/Marktplatz', '-U', '%(user)s', '-c', 'dir']
		read = run_commands(
				[cmd_read_marktplatz],
				{
					'ip':	ip_address,
					'user':	'{0}%{1}'.format(user,passwd)
					}
				)
		if read[0] != expected_result:
			utils.fail('Read Marktplatz directory result (%r), expected (%r)' % (read[0], expected_result))

	def check_marktplatz_write(self, user, ip_address, passwd='univention', expected_result=0):
		print '.... Check Marktplatz write ....'
		f = tempfile.NamedTemporaryFile(dir='/tmp')
		cmd_write_marktplatz = ['smbclient', '//%(ip)s/Marktplatz', '-U', '%(user)s', '-c', 'put %(filename)s']
		write = run_commands(
				[cmd_write_marktplatz],
				{
					'ip':		ip_address,
					'user':		'{0}%{1}'.format(user,passwd),
					'filename': '%s %s' % (f.name, f.name.split('/')[-1])
					}
				)
		f.close()
		if write[0] != expected_result:
			utils.fail('Write to Marktplatz directory result (%r), expected (%r)' % (write[0], expected_result))

	def check_share_access(self, user, ip_address, expected_home_result, expected_marktplatz_result):
		restart_samba()
		self.check_home_read(user, ip_address, expected_result=expected_home_result)
		self.check_home_write(user, ip_address, expected_result=expected_home_result)
		self.check_marktplatz_read(user, ip_address, expected_result=expected_marktplatz_result)
		self.check_marktplatz_write(user, ip_address, expected_result=expected_marktplatz_result)

	def test_share_access_settings(self, user, ip_address, umc_connection):
		self.aquire_room(umc_connection)
		print self.get_room_settings(umc_connection)

		self.check_share_access(user, ip_address, 0, 0)

		period = datetime.time.strftime(
			(datetime.datetime.now() + datetime.timedelta(0,120)).time(), '%H:%M')
		new_settings = {
				'customRule':	'',
				'printMode':	'none',
				'internetRule':	'none',
				'shareMode':	'home',
				'period':	period
				}
		self.set_room_settings(umc_connection, new_settings)

		self.check_share_access(user, ip_address, 0, 1)


	def check_smb_print(self, ip, printer, user, expected_result):
		print '-' * 60
		f = tempfile.NamedTemporaryFile(dir='/tmp')
		cmd_print = [
				'smbclient', '//%(ip)s/%(printer)s',
				'-U', '%(user)s',
				'-c', 'print %(filename)s'
				]
		result = run_commands(
				[cmd_print],{
					'ip':ip,
					'printer': printer,
					'user':'{0}%{1}'.format(user, 'univention'),
					'filename': f.name
					}
				)[0]
		f.close()
		if result != expected_result:
			utils.fail('smbclient print result (%r), expected (%r)' % (result, expected_result))

	def test_print_mode_settings(self, school, user, ip_address, umc_connection):
		ucr = ucr_test.UCSTestConfigRegistry()
		ucr.load()
		self.aquire_room(umc_connection)

		printer = uts.random_string()
		try:
			add_printer(
					printer,
					school,
					ucr.get('hostname'),
					ucr.get('domainname'),
					ucr.get('ldap/base')
					)
			period = datetime.time.strftime(
				(datetime.datetime.now() + datetime.timedelta(0,120)).time(), '%H:%M')
			new_settings = {
					'customRule':	'',
					'printMode':	'default',
					'internetRule': 'Kein Internet',
					'shareMode':	'all',
					'period':	period
					}
			self.set_room_settings(umc_connection, new_settings)
			restart_samba()
			self.check_smb_print(ip_address, printer, user, 1) #TODO FAILS because of Bug #35076
			self.check_smb_print(ip_address, 'PDFDrucker', user, 0)

			period = datetime.time.strftime(
				(datetime.datetime.now() + datetime.timedelta(0,180)).time(), '%H:%M')
			new_settings = {
					'customRule':	'',
					'printMode':	'all',
					'internetRule': 'Unbeschränkt',
					'shareMode':	'all',
					'period':		period
					}
			self.set_room_settings(umc_connection, new_settings)
			restart_samba()
			self.check_smb_print(ip_address, printer, user, 0)
			self.check_smb_print(ip_address, 'PDFDrucker', user, 0)

			period = datetime.time.strftime(
				(datetime.datetime.now() + datetime.timedelta(0,240)).time(), '%H:%M')
			new_settings = {
					'customRule':	'',
					'printMode':	'none',
					'internetRule': 'Kein Internet',
					'shareMode':	'all',
					'period':		period
					}
			self.set_room_settings(umc_connection, new_settings)
			restart_samba()
			self.check_smb_print(ip_address, printer, user, 1)
			self.check_smb_print(ip_address, 'PDFDrucker', user, 1)

		finally:
			remove_printer(printer, school, ucr.get('ldap/base'))

	def checK_internetrules(self, ucr, user, proxy, custom_domain, global_domains, expected_rule):
		# Getting the redirection page when blocked
		banPage = get_banpage(ucr)
		localCurl = SimpleCurl(proxy=proxy, username=user)

		rule_in_control = None
		if expected_rule=='Kein Internet' and localCurl.getPage('univention.de') == banPage:
			rule_in_control = expected_rule
		if expected_rule=='Unbeschränkt' and localCurl.getPage('gmx.de') != banPage:
			rule_in_control = expected_rule
		if expected_rule == 'custom' and localCurl.getPage(custom_domain) != banPage:
			rule_in_control = expected_rule
		if expected_rule == 'none':
			if all(localCurl.getPage(dom) != banPage for dom in  global_domains):
				rule_in_control = expected_rule

		localCurl.close()
		print 'RULE IN CONTROL = ', rule_in_control
		if rule_in_control != expected_rule:
			utils.fail('rule in control (%s) does not match the expected one (%s)' % (
				rule_in_control, expected_rule))

	def test_internetrules_settings(self, school,user, user_dn, ip_address, ucr, umc_connection):
		# Create new workgroup and assign new internet rule to it
		group = Workgroup(school, members=[user_dn])
		global_domains = ['univention.de', 'google.de']
		rule = InternetRule(typ='whitelist',domains=global_domains)
		rule.define()
		rule.assign(school, group.name, 'workgroup')

		self.check_internetRules(umc_connection)
		self.aquire_room(umc_connection)

		# testing loop
		t = 120
		rules = ['none', 'Kein Internet', 'Unbeschränkt', 'custom']
		for rule in rules:
			print '-' * 60
			period = datetime.time.strftime(
					(datetime.datetime.now() + datetime.timedelta(0,t)).time(), '%H:%M')
			t += 60
			new_settings = {
					'customRule':	'univention.de',
					'printMode':	'default',
					'internetRule':	rule,
					'shareMode':	'all',
					'period':	period
					}
			self.set_room_settings(umc_connection, new_settings)
			self.checK_internetrules(
					ucr,
					user,
					ip_address,
					'univention.de',
					global_domains,
					rule)
		group.remove()

	def test_all(self, school, user, user_dn, ip_address, ucr, umc_connection):
		self.test_time_settings(umc_connection)
		self.test_share_access_settings(user, ip_address, umc_connection)
		self.test_print_mode_settings(school, user, ip_address, umc_connection)
		self.test_internetrules_settings(school, user, user_dn, ip_address, ucr, umc_connection)

def get_banpage(ucr):
	# Getting the redirection page when blocked
	adminCurl = SimpleCurl(proxy=ucr.get('hostname'))
	redirUri = ucr.get('proxy/filter/redirecttarget')
	banPage = adminCurl.getPage(redirUri)
	adminCurl.close()
	return banPage

def run_commands(cmdlist, argdict):
	"""
	Start all commands in cmdlist and replace formatstrings with arguments in argdict.
	run_commands([['/bin/echo', '%(msg)s'], ['/bin/echo', 'World']], {'msg': 'Hello'})
	"""
	result_list = []
	for cmd in cmdlist:
		cmd = copy.deepcopy(cmd)
		for i, val in enumerate(cmd):
			cmd[i] = val % argdict
		print '*** %r' % cmd
		result = subprocess.call(cmd)
		result_list.append(result)
	return result_list

def restart_samba():
	print '.... Restarting Samba ....'
	cmd_restart_samba = ['/etc/init.d/samba', 'restart']
	run_commands([cmd_restart_samba],{})

def add_printer(name, school, hostname, domainname, ldap_base):
	cmd_add_printer = [
			'udm', 'shares/printer', 'create',
			'--position', 'cn=printers,ou=%(school)s,%(ldap_base)s',
			'--set', 'name=%(name)s',
			'--set', 'spoolHost=%(hostname)s.%(domainname)s',
			'--set', 'uri="file:// /tmp/%(name)s.printer"',
			'--set', 'model=None',
			'--binddn', 'uid=Administrator,cn=users,%(ldap_base)s',
			'--bindpwd', 'univention'
			]
	print run_commands(
			[cmd_add_printer],{
				'name':	name,
				'school': school,
				'hostname':	hostname,
				'domainname': domainname,
				'ldap_base': ldap_base
				}
			)

def remove_printer(name, school, ldap_base):
	cmd_remove_printer = [
			'udm', 'shares/printer', 'remove',
			'--dn', 'cn=%(name)s,cn=printers,ou=%(school)s,%(ldap_base)s'
			]
	print run_commands(
			[cmd_remove_printer],{
				'name':	name,
				'school': school,
				'ldap_base': ldap_base
				}
			)


class Computers(object):
	def __init__(self, open_ldap_co, school, nr_windows=1, nr_macos=0, nr_ipmanagedclient=0):
		self.open_ldap_co = open_ldap_co
		self.school = school
		self.nr_windows = nr_windows
		self.nr_macos = nr_macos
		self.nr_ipmanagedclient = nr_ipmanagedclient

	def create(self):
		computer_import = ComputerImport(
				self.school,
				nr_windows=self.nr_windows,
				nr_macos=self.nr_macos,
				nr_ipmanagedclient=self.nr_ipmanagedclient)

		print '********** Create computers'
		computer_import.run_import(self.open_ldap_co)

		created_computers = []
		for computer in computer_import.windows:
			created_computers.append(computer)
		for computer in computer_import.macos:
			created_computers.append(computer)
		for computer in computer_import.ipmanagedclients:
			created_computers.append(computer)

		return sorted(created_computers)

	def get_dns(self, computers):
		dns = []
		for computer in sorted(computers):
			dns.append(computer.dn)
		return dns

	def get_ips(self, computers):
		ips = []
		for computer in sorted(computers):
			ips.append(computer.ip)
		return ips

