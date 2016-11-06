"""
.. module:: user
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
import univention.testing.utils as utils
from univention.testing.ucsschool import UMCConnection
import univention.testing.ucr as ucr_test
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
	:param school_classes: dictionary of school -> list of names of the class which contain the user
	:type school_classes: dict
	"""

	def __init__(
			self,
			school,
			role,
			school_classes,
			mode='A',
			username=None,
			firstname=None,
			lastname=None,
			password=None,
			mail=None):
		super(User, self).__init__(school, role)

		if username:
			self.username = username
			self.dn = self.make_dn()
		if firstname:
			self.firstname = firstname
		if lastname:
			self.lastname = lastname
		if mail:
			self.mail = mail
		if school_classes:
			self.school_classes = school_classes
		self.typ = 'teachersAndStaff' if self.role == 'teacher_staff' else self.role
		self.mode = mode

		utils.wait_for_replication()
		self.ucr = ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
		host = self.ucr.get('ldap/master')
		self.umc_connection = UMCConnection(host)
		account = utils.UCSTestDomainAdminCredentials()
		admin = account.username
		passwd = account.bindpw
		self.password = password if password else passwd
		self.umc_connection.auth(admin, passwd)

	def append_random_groups(self):
		pass

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace_back):
		self.ucr.revert_to_original_registry()

	def create(self):
		"""Creates object user"""
		flavor = 'schoolwizards/users'
		param = [{
			'object': {
				'school': self.school,
				'school_classes': self.school_classes,
				'email': self.mail,
				'name': self.username,
				'type': self.typ,
				'firstname': self.firstname,
				'lastname': self.lastname,
				'password': self.password
			},
			'options': None
		}]
		print 'Creating user %s' % (self.username,)
		print 'param = %s' % (param,)
		reqResult = self.umc_connection.request(
				'schoolwizards/users/add', param, flavor)
		if not reqResult[0]:
			raise CreateFail('Unable to create user (%r)' % (param,))
		else:
			utils.wait_for_replication()

	def get(self):
		"""Get user"""
		flavor = 'schoolwizards/users'
		param = [{
			'object': {
				'$dn$': self.dn,
				'school': self.school
		}}]
		reqResult = self.umc_connection.request(
				'schoolwizards/users/get', param, flavor)
		if not reqResult[0]:
			raise GetFail('Unable to get user (%s)' % self.username)
		else:
			return reqResult[0]

	def check_get(self, expected_attrs={}):
		info = {
				'$dn$': self.dn,
				'display_name': ' '.join([self.firstname, self.lastname]),
				'name': self.username,
				'firstname': self.firstname,
				'lastname': self.lastname,
				'type_name': self.type_name(),
				'school': self.school,
				'schools': [self.school],
				'disabled': 'none',
				'birthday': None,
				'password': None,
				'type': self.typ,
				'email': self.mail,
				'objectType': 'users/user',
				'school_classes': {},
		}
		if self.is_student() or self.is_teacher() or self.is_teacher_staff():
			info.update({'school_classes': self.school_classes})

		if expected_attrs:
			info.update(expected_attrs)

		get_result = self.get()
		# Type_name is only used for display, Ignored
		info['type_name'] = get_result['type_name']
		if get_result != info:
			diff = []
			for key in (set(get_result.keys()) | set(info.keys())):
				if get_result.get(key) != info.get(key):
					diff.append('%s: Got: %r; expected: %r' % (key, get_result.get(key), info.get(key)))
			raise GetCheckFail('Failed get request for user %s:\n%s' % (self.username, '\n'.join(diff)))

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
		param = {
			'school': self.school,
			'type': 'all',
			'filter': ""
		}
		reqResult = self.umc_connection.request(
				'schoolwizards/users/query', param, flavor)
		return reqResult

	def check_query(self, users_dn):
		q = self.query()
		k = [x['$dn$'] for x in q]
		if not set(users_dn).issubset(set(k)):
			raise QueryCheckFail('users from query do not contain the existing users, found (%r), expected (%r)' % (
				k, users_dn))

	def remove(self):
		"""Remove user"""
		print 'Removing User (%s)' % self.username
		flavor = 'schoolwizards/users'
		param = [{
			'object': {
				'school': self.school,
				'$dn$': self.dn,
			},
			'options': None
		}]
		reqResult = self.umc_connection.request(
				'schoolwizards/users/remove', param, flavor)
		if not reqResult[0]:
			raise RemoveFail('Unable to remove user (%s)' % self.username)
		else:
			self.set_mode_to_delete()

	def edit(self, new_attributes):
		"""Edit object user"""
		flavor = 'schoolwizards/users'
		param = [{
			'object': {
				'school': self.school,
				'schools': [self.school],
				'school_classes': new_attributes.get('school_classes', self.school_classes),
				'email': new_attributes.get('email') if new_attributes.get('email') else self.mail,
				'name': self.username,
				'type': self.typ,
				'firstname': new_attributes.get('firstname') if new_attributes.get('firstname') else self.firstname,
				'lastname': new_attributes.get('lastname') if new_attributes.get('lastname') else self.lastname,
				'password': new_attributes.get('password') if new_attributes.get('password') else self.password,
				'$dn$': self.dn,
			},
			'options': None
		}]
		print 'Editing user %s' % (self.username,)
		print 'param = %s' % (param,)
		reqResult = self.umc_connection.request(
				'schoolwizards/users/put',
				param,
				flavor)
		if not reqResult[0]:
			raise EditFail('Unable to edit user (%s) with the parameters (%r)' % (self.username, param))
		else:
			self.set_mode_to_modify()
			self.school_classes = new_attributes.get('school_classes', self.school_classes)
			self.mail = new_attributes.get('email') if new_attributes.get('email') else self.mail
			self.firstname = new_attributes.get('firstname') if new_attributes.get('firstname') else self.firstname
			self.lastname = new_attributes.get('lastname') if new_attributes.get('lastname') else self.lastname
			self.password = new_attributes.get('password') if new_attributes.get('password') else self.password
