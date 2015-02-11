from univention.lib.umc_connection import UMCConnection
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool as utu
import univention.testing.utils as utils

class FailQuery(Exception):
	pass

class FailPut(Exception):
	pass

class FailGet(Exception):
	pass

class FailAdd(Exception):
	pass

class FailCheckPut(Exception):
	pass

class FailCheckGet(Exception):
	pass

class FailCheckQuery(Exception):
	pass

class FailRemove(Exception):
	pass

class ComputerRoom(object):
	def __init__(
			self,
			school,
			name=None,
			description=None,
			host_members=[]):
		self.school = school
		self.name = name if name else uts.random_name()
		self.description = description if description else uts.random_name()
		self.host_members = host_members if host_members else []
		self.ucr = ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
		host = self.ucr.get('hostname')
		self.umc_connection = UMCConnection(host)
		account = utils.UCSTestDomainAdminCredentials()
		admin = account.username
		passwd = account.bindpw
		self.umc_connection.auth(admin, passwd)

	def dn(self):
		return 'cn=%s-%s,cn=raeume,cn=groups,%s' % (
				self.school, self.name, utu.UCSTestSchool().get_ou_base_dn(self.school))

	def add(self, should_pass=True):
		param = [
			{
				'object':
				{
					'school': self.school,
					'name': self.name,
					'description': self.description,
					'computers': self.host_members,
					},
				'options': None
				}
			]
		print 'Adding school room %s with UMCP:%s' % (
			self.name,
			'schoolrooms/add')
		print 'param = %r' % (param,)
		reqResult = self.umc_connection.request('schoolrooms/add', param)
		utils.wait_for_replication()
		if reqResult[0] and should_pass:
			print 'School room created successfully: %s' % (self.name,)
		else:
			if should_pass:
				raise FailAdd('Unable to add school room (%r)' % (param,))
			else:
				print 'School room (%r) addition failed as expected.' % (self.name,)

	def verify_ldap(self, must_exist=True):
		utils.verify_ldap_object(self.dn(), should_exist=must_exist)

	def get(self, should_exist=True):
		"""gets school room via UMCP\n
		:param should_exist: True if the school room is expected to be found
		:type should_exist: bool"""
		print 'Calling %s for %s' % (
			'schoolrooms/get',
			self.dn())
		reqResult = self.umc_connection.request(
			'schoolrooms/get', [self.dn()])
		if bool(reqResult[0]['name']) != should_exist:
			raise FailGet('Unexpected fetching result for school room (%r)' % (self.dn()))
		else:
			return reqResult[0]

	def check_get(self, expected_attrs):
		"""checks if the result of get command matches the
		expected attributes.
		"""
		current_attrs = self.get()
		if current_attrs != expected_attrs:
			raise FailCheckGet('The current attrbutes (%r) do not match the expected ones (%r)' % (
				current_attrs, expected_attrs))

	def query(self):
		"""Get all school rooms via UMCP\n
		:returns: [str] list of school rooms names
		"""
		print 'Calling %s = get all school rooms' % ('schoolrooms/query')
		try:
			rooms = self.umc_connection.request(
					'schoolrooms/query', {'school': self.school, 'pattern': ''})
			return [x['name'] for x in rooms]
		except FailQuery:
			raise

	def check_query(self, rooms):
		current_rooms = self.query()
		if not set(rooms).issubset(set(current_rooms)):
			raise FailCheckQuery('Rooms query result: %r, expected to contain at least:%r' % (current_rooms, rooms))

	def put(self, new_attributes):
		"""Modify school room via UMCP\n
		with no args passed this only reset the school room properties\n
		:param new_attributes:
		:type new_attributes: dict
		"""
		new_name = new_attributes.get('name') if new_attributes.get('name') else self.name
		new_description = new_attributes.get('description') if new_attributes.get('description') else self.description
		new_host_members = new_attributes.get('computers') if new_attributes.get('computers') else self.host_members

		param = [
			{
				'object':
				{
					'school': self.school,
					'name': new_name,
					'description': new_description,
					'computers': new_host_members,
					'$dn$': self.dn(),
					},
				'options': None
				}
			]
		print 'Modifying school room %s with UMCP:%s' % (
			self.dn(),
			'schoolrooms/put')
		print 'param = %r' % (param,)
		reqResult = self.umc_connection.request('schoolrooms/put', param)
		if not reqResult:
			raise FailPut('Unable to modify school room (%r)' % (param,))
		else:
			self.name = new_name
			self.description = new_description
			self.host_members = new_host_members
			utils.wait_for_replication()

	def check_put(self, new_attributes):
		new_attributes.update({'school': self.school, '$dn$': self.dn(), 'objectType': 'groups/group', 'hosts': new_attributes.get('computers')})
		self.put(new_attributes)
		current_attributes = self.get(True)
		new_attributes.update({'name': self.name, '$dn$': self.dn()})
		# new_attributes.update({'name': '%s-%s' % (self.school, self.name), '$dn$': self.dn()}) #FIXME workaround for Bug #35618
		if current_attributes != new_attributes:
			raise FailCheckPut('Modifying room %s was not successful\ncurrent attributes= %r\nexpected attributes= %r' %(
				self.name, current_attributes, new_attributes))

	def remove(self):
		"""removes school room via UMCP"""
		print 'Calling %s for %s' % (
			'schoolrooms/remove',
			self.dn())
		options = [{'object': [self.dn()], 'options': None}]
		reqResult = self.umc_connection.request(
			'schoolrooms/remove',
			options)
		utils.wait_for_replication()
		if not reqResult[0]['success']:
			raise FailRemove('Unable to remove school room (%r)' % (self.dn(),))
