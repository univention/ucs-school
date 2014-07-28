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
from essential.importusers import Person

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


class User(Person):

	"""Contains the needed functuality for users in the UMC module schoolwizards/users.\n
	:param school: school name of the user
	:type school: str
	:param role: role of the user
	:type role: str ['student', 'teacher', 'staff', 'teacherAndStaff']
	:param school_class: name of the class which contain the user
	:type school_class: str
	"""

	def __init__(self, school, role, school_class):
		Person.__init__(self, school, role)
		self.classes = [school_class] if school_class else []
		self.typ = 'teachersAndStaff' if self.role == 'teacher_staff' else self.role
		self.school_class = school_class
		self.ucr = ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
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
						'email': self.mail,
						'name': self.username,
						'type': self.typ,
						'firstname': self.firstname,
						'lastname': self.lastname,
						'password': self.password
						},
					'options': None
					}
				]
		print 'Creating user %s' % (self.username,)
		print 'param = %s' % (param,)
		reqResult = self.umc_connection.request(
				'schoolwizards/users/add', param, flavor)
		if not reqResult[0]:
			raise CreateFail('Unable to create user (%r)' % (param,))

	def get(self):
		"""Get user"""
		flavor = 'schoolwizards/users'
		param =	[
				{
					'object':{
						'$dn$': self.dn,
						'school': self.school
						}
					}
				]
		reqResult = self.umc_connection.request(
				'schoolwizards/users/get',param,flavor)
		if not reqResult[0]:
			raise GetFail('Unable to get user (%s)' % self.username)
		else:
			return reqResult[0]

	def check_get(self):
		info = {
				'$dn$': self.dn,
				'display_name': ' '.join([self.firstname,self.lastname]),
				'name': self.username,
				'firstname': self.firstname,
				'lastname': self.lastname,
				'type_name': self.type_name(),
				'school': self.school,
				'disabled' : 'none',
				'birthday': None,
				'password': None,
				'type': self.typ,
				'email': self.mail,
				'objectType': 'users/user'
				}
		if self.is_student():
			info.update({'school_class': self.school_class})
		if self.is_teacher():
			info.update({'school_class': self.school_class})
		if self.is_teacher_staff():
			info.update({'school_class': self.school_class})
		get_result = self.get()
		# Type_name is only used for display, Ignored
		info['type_name'] = get_result['type_name']
		if get_result != info:
			raise GetCheckFail('Failed get request for user %s. Returned result: %r. Expected result: %r' % (
				self.username, get_result, info))

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

	def remove(self):
		"""Remove user"""
		print 'Removing User (%s)' % self.username
		flavor = 'schoolwizards/users'
		param =	[
				{
					'object':{
						'school': self.school,
						'$dn$': self.dn,
						},
					'options': None
					}
				]
		reqResult = self.umc_connection.request(
				'schoolwizards/users/remove',param,flavor)
		if not reqResult[0]:
			raise RemoveFail('Unable to remove user (%s)' % self.username)
		else:
			self.set_mode_to_delete()


	def edit(self, new_attributes):
		"""Edit object user"""
		flavor = 'schoolwizards/users'
		param =	[
				{
					'object':{
						'school': self.school,
						'school_class': new_attributes.get('school_class') if new_attributes.get('school_class') else self.school_class,
						'email': new_attributes.get('email') if new_attributes.get('email') else self.mail,
						'name': self.username,
						'type': self.typ,
						'firstname': new_attributes.get('firstname') if new_attributes.get('firstname') else self.firstname,
						'lastname': new_attributes.get('lastname') if new_attributes.get('lastname') else self.lastname,
						'password': new_attributes.get('password') if new_attributes.get('password') else self.password,
						'$dn$':  self.dn,
						},
					'options': None
					}
				]
		print 'Editing user %s' % (self.username,)
		print 'param = %s' % (param,)
		reqResult = self.umc_connection.request(
				'schoolwizards/users/put',
				param,
				flavor)
		if not reqResult[0]:
			raise EditFail('Unable to edit user (%s) with the parameters (%r)' % (self.username , param))
		else:
			self.set_mode_to_modify()
			self.school_class = new_attributes['school_class']
			self.classes = [self.school_class]
			self.mail = new_attributes['email']
			self.firstname = new_attributes['firstname']
			self.lastname = new_attributes['lastname']
			self.password = new_attributes['password']
