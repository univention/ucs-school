"""
.. module:: user
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.lib.umc_connection import UMCConnection
import univention.testing.ucr as ucr_test
from univention.testing.ucsschool import UCSTestSchool

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


class User(object):

	"""Contains the needed functuality for users in the UMC module schoolwizards/users.
	By default they are randomly formed.\n
	:param umc_connection:
	:type umc_connection: UMC connection object
	:param ucr:
	:type ucr: UCR object
	:param name: name of the user to be created later
	:type name: str
	:param display_name: display_name of the user to be created later
	:type display_name: str
	"""

	# Initialization (Random by default)
	# types = ['student', 'teacher', 'staff', teacherAndStaff']
	def __init__(self,
				 school,
				 typ=None,
				 name=None,
				 firstname=None,
				 lastname=None,
				 school_class=None,
				 email=None,
				 password=None,
				 ucr=None,
				 umc_connection=None):
		self.school = school
		self.typ = typ if typ else 'student'
		self.password = password if password else 'univention'
		self.name = name if name else uts.random_string()
		self.firstname = firstname if firstname else uts.random_string()
		self.lastname = lastname if lastname else uts.random_string()
		self.email = email if email else '%s@%s.de' % (uts.random_string(), uts.random_string())
		self.school_class = school_class if school_class else uts.random_string()

		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
		if umc_connection:
			self.umc_connection = umc_connection
		else:
			host = self.ucr.get('ldap/master')
			self.umc_connection = UMCConnection(host)
			account = utils.UCSTestDomainAdminCredentials()
			admin = account.username
			passwd = account.bindpw
			self.umc_connection.auth(admin, passwd)

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace_back):
		self.ucr.revert_to_original_registry()

	def create(self):
		"""Creates object user"""
		flavor = 'schoolwizards/users'
		param =	[
				{
					'object':{
						'school': self.school,
						'school_class': self.school_class,
						'email': self.email,
						'name': self.name,
						'type': self.typ,
						'firstname': self.firstname,
						'lastname': self.lastname,
						'password': self.password
						},
					'options': None
					}
				]
		print 'Creating user %s' % (self.name,)
		print 'param = %s' % (param,)
		reqResult = self.umc_connection.request(
				'schoolwizards/users/add',
				param,
				flavor)
		if not reqResult[0]:
			raise CreateFail('Unable to create user (%r)' % (param,))

	# create list of random users returns list of user objects
	def createList(self, count):
		"""Create a list of users
		with random names and display_name\n
		:param count: number of wanted users
		:type count: int
		:returns: [school_object]
		"""
		print 'Creating schoolsList'
		cList = []
		for i in xrange(count):
			c = self.__school__(self.school, umc_connection=self.umc_connection, ucr=self.ucr)
			c.create()
			cList.append(c)
		return cList

	def get(self):
		"""Get user"""
		flavor = 'schoolwizards/users'
		param =	[
				{
					'object':{
						'$dn$': self.dn(),
						'school': self.school
						}
					}
				]
		reqResult = self.umc_connection.request(
				'schoolwizards/users/get',param,flavor)
		if not reqResult[0]:
			raise GetFail('Unable to get user (%s)' % self.name)
		else:
			return reqResult[0]

	def check_get(self):
		info = {
				'$dn$': self.dn(),
				'display_name': ' '.join([self.firstname,self.lastname]),
				'name': self.name,
				'firstname': self.firstname,
				'lastname': self.lastname,
				'type_name': self.type_name(),
				'school': self.school,
				'school_class': self.school_class,
				'disabled' : 'none',
				'birthday': None,
				'password': None,
				'type': self.typ,
				'email': self.email,
				'objectType': 'users/user'
				}
		get_result = self.get()
		# Type_name is only used for display, Ignored
		info['type_name'] = get_result['type_name']
		if get_result != info:
			raise GetCheckFail('Failed get request for user %s. Returned result: %r. Expected result: %r' % (
				self.name, get_result, info))

	def type_name(self):
		if self.typ == 'student':
			return 'Student'
		elif self.typ == 'teacher':
			return 'Teacher'
		elif self.typ == 'staff':
			return 'Staff'
		elif self.typ == 'teacherAndStaff':
			return 'Teacher and Staff'

	def query(self):
		"""get the list of existing users in the school"""
		flavor = 'schoolwizards/users'
		param =	{
				'school': self.school,
				'type': 'all',
				'filter': ""
				}
		reqResult = self.umc_connection.request(
				'schoolwizards/users/query',param,flavor)
		return reqResult

	def check_query(self, users):
		q = self.query()
		k = [x['firstname'] for x in q]
		if not set(users).issubset(set(k)):
			raise QueryCheckFail('users from query do not contain the existing users, found (%r), expected (%r)' % (
				k, users))

	def dn(self):
		if self.typ == 'student':
			return 'uid=%s,cn=schueler,cn=users,%s' % (self.name, UCSTestSchool().get_ou_base_dn(self.school))
		elif self.typ == 'teacher':
			return 'uid=%s,cn=lehrer,cn=users,%s' % (self.name, UCSTestSchool().get_ou_base_dn(self.school))
		elif self.typ == 'staff':
			return 'uid=%s,cn=mitarbeiter,cn=users,%s' % (self.name, UCSTestSchool().get_ou_base_dn(self.school))
		elif self.typ == 'teacherAndStaff':
			return 'uid=%s,cn=lehrer und mitarbeiter,cn=users,%s' % (self.name, UCSTestSchool().get_ou_base_dn(self.school))

	def remove(self):
		"""Remove user"""
		flavor = 'schoolwizards/users'
		param =	[
				{
					'object':{
						'school': self.school,
						'$dn$': self.dn(),
						},
					'options': None
					}
				]
		reqResult = self.umc_connection.request(
				'schoolwizards/users/remove',param,flavor)
		if not reqResult[0]:
			raise RemoveFail('Unable to remove user (%s)' % self.name)


	def edit(self, new_attributes):
		"""Edit object user"""
		flavor = 'schoolwizards/users'
		param =	[
				{
					'object':{
						'school': self.school,
						'school_class': new_attributes.get('school_class') if new_attributes.get('school_class') else self.school_class,
						'email': new_attributes.get('email') if new_attributes.get('email') else self.email,
						'name': self.name,
						'type': self.typ,
						'firstname': new_attributes.get('firstname') if new_attributes.get('firstname') else self.firstname,
						'lastname': new_attributes.get('lastname') if new_attributes.get('lastname') else self.lastname,
						'password': new_attributes.get('password') if new_attributes.get('password') else self.password,
						'$dn$':  self.dn(),
						},
					'options': None
					}
				]
		print 'Editing user %s' % (self.name,)
		print 'param = %s' % (param,)
		reqResult = self.umc_connection.request(
				'schoolwizards/users/put',
				param,
				flavor)
		if not reqResult[0]:
			raise EditFail('Unable to edit user (%s) with the parameters (%r)' % (self.name , param))
		else:
			self.school_class = new_attributes['school_class']
			self.email = new_attributes['email']
			self.firstname = new_attributes['firstname']
			self.lastname = new_attributes['lastname']
			self.password = new_attributes['password']

	def verify_ldap(self, should_exist):
		utils.verify_ldap_object(self.dn(), should_exist=should_exist)
