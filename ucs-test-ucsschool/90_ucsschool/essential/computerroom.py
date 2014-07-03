
from essential.importcomputers import Windows, MacOS, IPManagedClient
from essential.internetrule import InternetRule
from ucsschool.lib.models import IPComputer as IPComputerLib
from ucsschool.lib.models import MacComputer as MacComputerLib
from ucsschool.lib.models import WindowsComputer as WindowsComputerLib
import essential.ucsschoo as utu
import re
import univention.testing.strings as uts
import univention.testing.utils as utils

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

