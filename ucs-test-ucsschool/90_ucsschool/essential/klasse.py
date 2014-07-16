"""
.. module:: Klasse
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.lib.umc_connection import UMCConnection
import univention.testing.ucr as ucr_test
from univention.testing.ucsschool import UCSTestSchool


class Klasse():

	"""Contains the needed functuality for classes in an already created OU,
	By default they are randomly formed except the OU, should be provided\n
	:param school: name of the ou
	:type school: str
	:param umcConnection:
	:type umcConnection: UMC connection object
	:param ucr:
	:type ucr: UCR object
	:param name: name of the class to be created later
	:type name: str
	:param description: description of the class to be created later
	:type description: str
	"""

	# Initialization (Random by default)
	def __init__(self,
				 school,
				 umcConnection=None,
				 ucr=None,
				 name=None,
				 description=None):
		self.school = school
		self.name = name if name else uts.random_string()
		self.description = description if description else uts.random_string()
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		if umcConnection:
			self.umcConnection = umcConnection
		else:
			self.ucr = ucr_test.UCSTestConfigRegistry()
			self.ucr.load()
			host = self.ucr.get('ldap/master')
			self.umcConnection = UMCConnection(host)
			account = utils.UCSTestDomainAdminCredentials()
			admin = account.username
			passwd = account.bindpw
			self.umcConnection.auth(admin, passwd)

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace_back):
		self.ucr.revert_to_original_registry()

	def create(self):
		"""Creates object class"""
		flavor = 'schoolwizards/classes'
		param =	[
				{
					'object':{
						'name': self.name,
						'school': self.school,
						'description': self.description,
						},
					'options': None
					}
				]
		print 'Creating class %s in school %s' % (
				self.name,
				self.school)
		print 'param = %s' % (param,)
		reqResult = self.umcConnection.request(
				'schoolwizards/classes/add',
				param,
				flavor)
		if not reqResult[0]:
			utils.fail('Unable to create class (%r)' % (param,))

	# create list of random classes returns list of class objects
	def createList(self, count):
		"""Create a list of classes inside the specific ou
		with random names and description\n
		:param count: number of wanted classes
		:type count: int
		:returns: [klasse_object]
		"""
		print 'Creating classesList'
		cList = []
		for i in xrange(count):
			c = self.__class__(self.school, self.umcConnection, ucr=self.ucr)
			c.create()
			cList.append(c)
		return cList

	def query(self):
		"""get the list of existing classes in the school"""
		flavor = 'schoolwizards/classes'
		param =	{
				'school': self.school,
				'filter': ""
				}
		reqResult = self.umcConnection.request(
				'schoolwizards/classes/query',param,flavor)
		return reqResult

	def check_query(self, classes_names):
		q = self.query()
		k = [x['name'] for x in q]
		if set(classes_names) != set(k):
			utils.fail('Classes from query do not match the existing classes, found (%r), expected (%r)' % (
				k, classes_names))

	def dn(self):
		 return 'cn=%s-%s,cn=klassen,cn=schueler,cn=groups,%s' % (
				 self.school, self.name, UCSTestSchool().get_ou_base_dn(self.school))


	def remove(self):
		"""Remove class"""
		flavor = 'schoolwizards/classes'
		param =	[
				{
					'object':{
						'$dn$': self.dn(),
						'school': self.school
						},
					'options': None
					}
				]
		reqResult = self.umcConnection.request(
				'schoolwizards/classes/remove',param,flavor)
		if not reqResult[0]:
			utils.fail('Unable to remove class (%s)' % self.name)


	def edit(self, new_attributes):
		"""Edit object class"""
		flavor = 'schoolwizards/classes'
		param =	[
				{
					'object':{
						'$dn$': self.dn(),
						'name': new_attributes['name'],
						'school': self.school,
						'description': new_attributes['description']
						},
					'options': None
					}
				]
		print 'Editing class %s in school %s' % (
				self.name,
				self.school)
		print 'param = %s' % (param,)
		reqResult = self.umcConnection.request(
				'schoolwizards/classes/put',
				param,
				flavor)
		if not reqResult[0]:
			utils.fail('Unable to edit class (%s) with the parameters (%r)' % (self.name , param))
		else:
			self.name = new_attributes['name']
			self.description = new_attributes['description']

	def check_existence(self, should_exist):
		utils.verify_ldap_object(self.dn(), should_exist=should_exist)
