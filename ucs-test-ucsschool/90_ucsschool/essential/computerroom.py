
## -*- coding: utf-8 -*-
from essential.importcomputers import Windows, MacOS, IPManagedClient, random_mac, random_ip
from essential.internetrule import InternetRule
from essential.simplecurl import SimpleCurl
from essential.workgroup import Workgroup
from ucsschool.lib.models import IPComputer as IPComputerLib
from ucsschool.lib.models import MacComputer as MacComputerLib
from ucsschool.lib.models import WindowsComputer as WindowsComputerLib
from univention.lib.umc_connection import UMCConnection
import copy
import datetime
import httplib
import itertools
import os
import re
import subprocess
import tempfile
import time
import univention.lib.atjobs as ula
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool as utu
import univention.testing.utils as utils

class GetFail(Exception):
	pass

class GetCheckFail(Exception):
	pass

class CreateFail(Exception):
	pass

class QueryCheckFail(Exception):
	pass

class RemoveFail(Exception):
	pass

class EditFail(Exception):
	pass

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
		try:
			current_settings = self.get_room_settings(umc_connection)
			d = dict(expected_settings) # copy dictionary
			d['period'] = current_settings['period']
			d['customRule'] = current_settings['customRule']   #TODO Bug 35258 remove
			if current_settings != d:
				print 'FAIL: Current settings (%r) do not match expected ones (%r)' % (current_settings, d)
			# utils.fail('Current settings (%r) do not match expected ones (%r)' % (
				# current_settings, d))
		except httplib.HTTPException as e:
			if '[Errno 4] Unterbrechung' in str(e):
				print 'failed to check room (%s) settings, exception [Errno4]' % self.name
			else:
				print("Exception: '%s' '%s' '%r'" % (str(e), type(e), e))
				raise

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
		exist = False
		for item in ula.list():
			if period == datetime.time.strftime(item.execTime.time(),'%H:%M'):
				exist = True
				break
		if exist == expected_existance:
			print 'Atjob result at(%r) existance is expected (%r)' % (period, exist)
		else:
			print 'FAIL: Atjob result at(%r) existance is not expected (%r)' % (period, exist)
			# utils.fail('Atjob result at(%r) existance is not expected (%r)' % (period, exist))

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
			print 'FAIL .. Read home directory result (%r), expected (%r)' % (read[0], expected_result)
			# utils.fail('Read home directory result (%r), expected (%r)' % (read[0], expected_result))

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
			print 'FAIL .. Write to home directory result (%r), expected (%r)' % (write[0], expected_result)
			# utils.fail('Write to home directory result (%r), expected (%r)' % (write[0], expected_result))

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
			print 'FAIL .. Read Marktplatz directory result (%r), expected (%r)' % (read[0], expected_result)
			# utils.fail('Read Marktplatz directory result (%r), expected (%r)' % (read[0], expected_result))

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
			print 'FAIL .. Write to Marktplatz directory result (%r), expected (%r)' % (write[0], expected_result)
			# utils.fail('Write to Marktplatz directory result (%r), expected (%r)' % (write[0], expected_result))

	def check_share_access(self, user, ip_address, expected_home_result, expected_marktplatz_result):
		self.check_home_read(user, ip_address, expected_result=expected_home_result)
		self.check_home_write(user, ip_address, expected_result=expected_home_result)
		self.check_marktplatz_read(user, ip_address, expected_result=expected_marktplatz_result)
		self.check_marktplatz_write(user, ip_address, expected_result=expected_marktplatz_result)

	def check_share_behavior(self, user, ip_address, shareMode):
		if shareMode == 'all':
			self.check_share_access(user, ip_address, 0, 0)
		elif shareMode == 'home':
			self.check_share_access(user, ip_address, 0, 1)
		else:
			utils.fail('shareMode invalid value = (%s)' % shareMode)

	def test_share_access_settings(self, user, ip_address, umc_connection):
		self.aquire_room(umc_connection)
		print self.get_room_settings(umc_connection)

		# generate all the possible combinations for (rule, printmode, sharemode)
		white_page = 'univention.de'
		rules = ['none', 'Kein Internet', 'Unbeschränkt', 'custom']
		printmodes = ['default', 'all', 'none']
		sharemodes = ['all', 'home']
		settings = itertools.product(rules, printmodes, sharemodes)
		t = 120

		# Testing loop
		for i in xrange(24):
			period = datetime.time.strftime(
					(datetime.datetime.now() + datetime.timedelta(0,t)).time(), '%H:%M')
			t += 60
			rule, printMode, shareMode = next(settings)
			print
			print '***', i, '-(internetRule, printMode, shareMode) = (',\
					rule,',', printMode,',', shareMode, ')', '-' * 10
			new_settings = {
					'customRule':	white_page,
					'printMode':	printMode,
					'internetRule':	rule,
					'shareMode':	shareMode,
					'period':	period
					}
			self.aquire_room(umc_connection)
			self.set_room_settings(umc_connection, new_settings)
			# check if displayed values match
			self.check_room_settings(umc_connection, new_settings)
			self.check_share_behavior(user, ip_address, shareMode)

	def check_smb_print(self, ip, printer, user, expected_result):
		print 'Checking print mode', '.' * 40
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
			print 'FAIL .... smbclient print result (%r), expected (%r)' % (result, expected_result)
			# utils.fail('smbclient print result (%r), expected (%r)' % (result, expected_result))

	def check_print_behavior(self, user, ip_address, printer, printMode):
		if printMode == 'none':
			self.check_smb_print(ip_address, printer, user, 1)
			self.check_smb_print(ip_address, 'PDFDrucker', user, 1)
		elif printMode == 'default':
			self.check_smb_print(ip_address, printer, user, 0)
			self.check_smb_print(ip_address, 'PDFDrucker', user, 0)
		elif printMode == 'all':
			self.check_smb_print(ip_address, printer, user, 0)
			self.check_smb_print(ip_address, 'PDFDrucker', user, 0)
		else:
			utils.fail('printMode invalid value = (%s)' % printMode)

	def test_printMode_settings(self, school, user, ip_address, umc_connection, ucr):
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
			# generate all the possible combinations for (rule, printmode, sharemode)
			white_page = 'univention.de'
			rules = ['none', 'Kein Internet', 'Unbeschränkt', 'custom']
			printmodes = ['default', 'all', 'none']
			sharemodes = ['all', 'home']
			settings = itertools.product(rules, printmodes, sharemodes)

			t = 120
			# Testing loop
			for i in xrange(24):
				period = datetime.time.strftime(
						(datetime.datetime.now() + datetime.timedelta(0,t)).time(), '%H:%M')
				t += 60
				rule, printMode, shareMode = next(settings)
				print
				print '***', i, '-(internetRule, printMode, shareMode) = (',\
						rule,',', printMode,',', shareMode, ')', '-' * 10
				new_settings = {
						'customRule':	white_page,
						'printMode':	printMode,
						'internetRule':	rule,
						'shareMode':	shareMode,
						'period':	period
						}
				self.aquire_room(umc_connection)
				self.set_room_settings(umc_connection, new_settings)
				# check if displayed values match
				self.check_room_settings(umc_connection, new_settings)
				self.check_print_behavior(user, ip_address, printer, printMode)

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
			# utils.fail('rule in control (%s) does not match the expected one (%s)' % (
			# 	rule_in_control, expected_rule))
			print 'FAIL: rule in control (%s) does not match the expected one (%s)' % (rule_in_control, expected_rule)

	def test_internetrules_settings(self, school,user, user_dn, ip_address, ucr, umc_connection):
		try:
			# Create new workgroup and assign new internet rule to it
			group = Workgroup(school, members=[user_dn])
			global_domains = ['univention.de', 'google.de']
			rule = InternetRule(typ='whitelist',domains=global_domains)
			rule.define()
			rule.assign(school, group.name, 'workgroup')

			self.check_internetRules(umc_connection)
			self.aquire_room(umc_connection)

			# generate all the possible combinations for (rule, printmode, sharemode)
			white_page = 'univention.de'
			rules = ['none', 'Kein Internet', 'Unbeschränkt', 'custom']
			printmodes = ['default', 'all', 'none']
			sharemodes = ['all', 'home']
			settings = itertools.product(rules, printmodes, sharemodes)

			t = 120
			# Testing loop
			for i in xrange(24):
				period = datetime.time.strftime(
						(datetime.datetime.now() + datetime.timedelta(0,t)).time(), '%H:%M')
				t += 60
				rule, printMode, shareMode = next(settings)
				print
				print '***', i, '-(internetRule, printMode, shareMode) = (',\
						rule,',', printMode,',', shareMode, ')', '-' * 10
				new_settings = {
						'customRule':	white_page,
						'printMode':	printMode,
						'internetRule':	rule,
						'shareMode':	shareMode,
						'period':	period
						}
				self.aquire_room(umc_connection)
				self.set_room_settings(umc_connection, new_settings)
				# check if displayed values match
				self.check_room_settings(umc_connection, new_settings)
				self.checK_internetrules(
						ucr,
						user,
						ip_address,
						'univention.de',
						global_domains,
						rule)
		finally:
			group.remove()

	def test_settings(self, school, user, user_dn, ip_address, ucr, umc_connection):
		printer = uts.random_string()
		try:
			# Create new workgroup and assign new internet rule to it
			group = Workgroup(school, members=[user_dn])
			global_domains = ['univention.de', 'google.de']
			rule = InternetRule(typ='whitelist',domains=global_domains)
			rule.define()
			rule.assign(school, group.name, 'workgroup')

			self.check_internetRules(umc_connection)

			# Add new hardware printer
			add_printer(
					printer,
					school,
					ucr.get('hostname'),
					ucr.get('domainname'),
					ucr.get('ldap/base')
					)

			# generate all the possible combinations for (rule, printmode, sharemode)
			white_page = 'univention.de'
			rules = ['none', 'Kein Internet', 'Unbeschränkt', 'custom']
			printmodes = ['default', 'all', 'none']
			sharemodes = ['all', 'home']
			settings = itertools.product(rules, printmodes, sharemodes)

			t = 120
			# Testing loop
			for i in xrange(24):
				period = datetime.time.strftime(
						(datetime.datetime.now() + datetime.timedelta(0,t)).time(), '%H:%M')
				rule, printMode, shareMode = next(settings)
				print
				print '***', i, '-(internetRule, printMode, shareMode) = (',\
						rule,',', printMode,',', shareMode, ')', '-' * 10
				new_settings = {
						'customRule':	white_page,
						'printMode':	printMode,
						'internetRule':	rule,
						'shareMode':	shareMode,
						'period':	period
						}
				self.aquire_room(umc_connection)
				old_settings = self.get_room_settings(umc_connection)
				self.set_room_settings(umc_connection, new_settings)
				# check if displayed values match
				self.check_room_settings(umc_connection, new_settings)
				# old_period = old_settings['period']
				partial_old_settings = {
						'period' : old_settings['period'],
						'printMode': old_settings['printMode'],
						'shareMode': old_settings['shareMode'],
						'internetRule': old_settings['internetRule']
						}
				self.check_behavior(
						partial_old_settings,
						new_settings,
						user,
						ip_address,
						printer,
						white_page,
						global_domains,
						ucr)
				t += 60
		finally:
			group.remove()
			remove_printer(printer, school, ucr.get('ldap/base'))

	def check_behavior(
			self,
			partial_old_settings,
			new_settings,
			user,
			ip_address,
			printer,
			white_page,
			global_domains,
			ucr):
		# extract the new_settings
		period = new_settings['period']
		internetRule = new_settings['internetRule']
		printMode = new_settings['printMode']
		shareMode = new_settings['shareMode']

		# check atjobs
		partial_new_settings = {
				'period' : period,
				'printMode': printMode,
				'shareMode': shareMode,
				'internetRule': internetRule
				}
		# if there is no change in settings, no atjob is added
		print
		print '----------DEBUG-----------'
		print 'old=', partial_old_settings
		print 'new=', partial_new_settings
		if partial_old_settings != partial_new_settings:
			self.check_atjobs(period, True)
		else:
			self.check_atjobs(period, False)

		# check internetrules
		self.checK_internetrules(
				ucr,
				user,
				ip_address,
				white_page,
				global_domains,
				internetRule)

		# check share access
		self.check_share_behavior(user, ip_address, shareMode)

		# check print mode
		self.check_print_behavior(user, ip_address, printer, printMode)


def get_banpage(ucr):
	# Getting the redirection page when blocked
	adminCurl = SimpleCurl(proxy=ucr.get('hostname'))
	redirUri = ucr.get('proxy/filter/redirecttarget')
	banPage = adminCurl.getPage(redirUri)
	adminCurl.close()
	return banPage

def clean_folder(path):
	print 'Cleaning folder %r .....' % path
	for root, _ , filenames in os.walk(path):
		for f in filenames:
			file_path = os.path.join(root, f)
			os.remove(file_path)

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

def add_printer(name, school, hostname, domainname, ldap_base):
	#account = utils.UCSTestDomainAdminCredentials()
	#adminuid = account.binddn
	#passwd = account.bindpw
	# adminuid = 'uid=Administrator,cn=users,dc=najjar,dc=local'
	# passwd = 'univention'

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
				'ldap_base': ldap_base,
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
		return [x.dn for x in computers]

	def get_ips(self, computers):
		return [x.ip for x in computers]

	def get_hostnames(self, computers):
		return ['%s$' % x.name for x in computers]


def set_windows_pc_password(dn, password):
	cmd = ['udm', 'computers/windows', 'modify', '--dn' ,'%(dn)s', '--set', 'password=%(password)s']
	read = run_commands([cmd], {'dn':dn, 'password':password})
	return read

class UmcComputer(object):

	def __init__(
			self,
			school,
			typ,
			name=None,
			ip_address=None,
			subnet_mask=None,
			mac_address=None,
			inventory_number=None
			):
		self.school = school
		self.typ = typ
		self.name = name if name else uts.random_name()
		self.ip_address = ip_address if ip_address else random_ip()
		self.subnet_mask = subnet_mask if subnet_mask else '255.255.255.0'
		self.mac_address = mac_address.lower() if mac_address else random_mac()
		self.inventory_number = inventory_number if inventory_number else ''
		self.ucr = ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
		host = self.ucr.get('ldap/master')
		self.umc_connection = UMCConnection(host)
		account = utils.UCSTestDomainAdminCredentials()
		admin = account.username
		passwd = account.bindpw
		self.umc_connection.auth(admin, passwd)

	def create(self, should_succeed=True):
		"""Creates object Computer"""
		flavor = 'schoolwizards/computers'
		param = [
				{
					'object':{
						'school': self.school,
						'type': self.typ,
						'name': self.name,
						'ip_address': self.ip_address,
						'mac_address': self.mac_address.lower(),
						'subnet_mask': self.subnet_mask,
						'inventory_number': self.inventory_number
						},
					'options': None
					}
				]
		print 'Creating Computer %s' % (self.name,)
		print 'param = %s' % (param,)
		reqResult = self.umc_connection.request(
				'schoolwizards/computers/add', param, flavor)
		if reqResult[0] == should_succeed:
			utils.wait_for_replication()
		elif should_succeed in reqResult[0]['result']['message']:
			print 'Expected creation fail for computer (%r)\nReturn Message: %r' % (self.name,reqResult[0]['result']['message'])
		else:
			raise CreateFail('Unable to create computer (%r)\nRequest Result: %r' % (param,reqResult))

	def remove(self):
		"""Remove computer"""
		flavor = 'schoolwizards/computers'
		param = [
				{
					'object':{
						'$dn$': self.dn(),
						'school': self.school,
						},
					'options': None
					}
				]
		reqResult = self.umc_connection.request(
				'schoolwizards/computers/remove',param,flavor)
		if not reqResult[0]:
			raise RemoveFail('Unable to remove computer (%s)' % self.name)
		else:
			utils.wait_for_replication()

	def dn(self):
		return 'cn=%s,cn=computers,%s' % (self.name, utu.UCSTestSchool().get_ou_base_dn(self.school))

	def get(self):
		"""Get Computer"""
		flavor = 'schoolwizards/computers'
		param = [
				{
					'object':{
						'$dn$': self.dn(),
						'school': self.school
						}
					}
				]
		reqResult = self.umc_connection.request(
				'schoolwizards/computers/get',param,flavor)
		if not reqResult[0]:
			raise GetFail('Unable to get computer (%s)' % self.name)
		else:
			return reqResult[0]

	def check_get(self):
		info = {
				'$dn$': self.dn(),
				'school': self.school,
				'type': self.typ,
				'name': self.name,
				'ip_address': [self.ip_address],
				'mac_address': [self.mac_address.lower()],
				'subnet_mask': self.subnet_mask,
				'inventory_number': self.inventory_number,
				'zone': None,
				'type_name': self.type_name(),
				'objectType': 'computers/%s' % self.typ
				}
		get_result = self.get()
		if get_result != info:
			diff = set(x for x in get_result if get_result[x] != info[x])
			raise GetCheckFail(
					'Failed get request for computer %s.\nReturned result: %r.\nExpected result: %r,\nDifference = %r' % (
						self.name, get_result, info, diff))

	def type_name(self):
		if self.typ == 'windows':
			return 'Windows-System'
		elif self.typ == 'macos':
			return 'Mac OS X'
		elif self.typ == 'ipmanagedclient':
			return 'Gerät mit IP-Adresse'

	def edit(self, new_attributes):
		"""Edit object computer"""
		flavor = 'schoolwizards/computers'
		param = [
				{
					'object':{
						'$dn$': self.dn(),
						'name': self.name,
						'school': self.school,
						'type': self.typ,
						'ip_address': new_attributes.get('ip_address') if new_attributes.get('ip_address') else self.ip_address,
						'mac_address': new_attributes.get('mac_address').lower() if new_attributes.get('mac_address') else self.mac_address,
						'subnet_mask': new_attributes.get('subnet_mask') if new_attributes.get('subnet_mask') else self.subnet_mask,
						'inventory_number': new_attributes.get('inventory_number') if new_attributes.get('inventory_number') else self.inventory_number,
						},
					'options': None
					}
				]
		print 'Editing computer %s' % (self.name,)
		print 'param = %s' % (param,)
		reqResult = self.umc_connection.request(
				'schoolwizards/computers/put', param, flavor)
		if not reqResult[0]:
			raise EditFail('Unable to edit computer (%s) with the parameters (%r)' % (self.name , param))
		else:
			self.ip_address = new_attributes.get('ip_address')
			self.mac_address = new_attributes.get('mac_address').lower()
			self.subnet_mask = new_attributes.get('subnet_mask')
			self.inventory_number = new_attributes.get('inventory_number')
			utils.wait_for_replication()

	def query(self):
		"""get the list of existing computer in the school"""
		flavor = 'schoolwizards/computers'
		param = {
				'school': self.school,
				'filter': "",
				'type' : 'all'
				}
		reqResult = self.umc_connection.request(
				'schoolwizards/computers/query',param,flavor)
		return reqResult

	def check_query(self, computers):
		q = self.query()
		k = [x['name'] for x in q]
		if not set(computers).issubset(set(k)):
			raise QueryCheckFail('computers from query do not contain the existing computers, found (%r), expected (%r)' % (
				k, computers))

	def verify_ldap(self, should_exist):
		print 'verifying computer %s' % self.name
		utils.verify_ldap_object(self.dn(), should_exist=should_exist)
