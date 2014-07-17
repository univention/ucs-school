"""
.. module:: School
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.lib.umc_connection import UMCConnection
import univention.testing.ucr as ucr_test
from univention.testing.ucsschool import UCSTestSchool


class School():

	"""Contains the needed functuality for schools in the UMC module schoolwizards/schools.
	By default they are randomly formed.\n
	:param umcConnection:
	:type umcConnection: UMC connection object
	:param ucr:
	:type ucr: UCR object
	:param name: name of the school to be created later
	:type name: str
	:param display_name: display_name of the school to be created later
	:type display_name: str
	"""

	# Initialization (Random by default)
	def __init__(self,
				 display_name=None,
				 name=None,
				 ucr=None,
				 umcConnection=None):
		self.name = name if name else uts.random_string()
		self.display_name = display_name if display_name else uts.random_string()
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
		"""Creates object school"""
		flavor = 'schoolwizards/schools'
		param =	[
				{
					'object':{
						'name': self.name,
						'dc_name': '',
						'display_name': self.display_name,
						},
					'options': None
					}
				]
		print 'Creating school %s' % (self.name,)
		print 'param = %s' % (param,)
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/add',
				param,
				flavor)
		if not reqResult[0]:
			utils.fail('Unable to create school (%r)' % (param,))

	# create list of random schools returns list of school objects
	def createList(self, count):
		"""Create a list of schools
		with random names and display_name\n
		:param count: number of wanted schools
		:type count: int
		:returns: [school_object]
		"""
		print 'Creating schoolsList'
		cList = []
		for i in xrange(count):
			c = self.__school__(self.school, self.umcConnection, ucr=self.ucr)
			c.create()
			cList.append(c)
		return cList

	def query(self):
		"""get the list of existing schools in the school"""
		flavor = 'schoolwizards/schools'
		param =	{
				'school': 'undefined',
				'filter': ""
				}
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/query',param,flavor)
		return reqResult

	def check_query(self, schools):
		q = self.query()
		k = [x['display_name'] for x in q]
		if not set(schools).issubset(set(k)):
			utils.fail('schools from query do not contain the existing schools, found (%r), expected (%r)' % (
				k, schools))

	def dn(self):
		 return UCSTestSchool().get_ou_base_dn(self.name)


	def remove(self):
		"""Remove school"""
		flavor = 'schoolwizards/schools'
		param =	[
				{
					'object':{
						'$dn$': self.dn(),
						},
					'options': None
					}
				]
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/remove',param,flavor)
		if not reqResult[0]:
			utils.fail('Unable to remove school (%s)' % self.name)


	def edit(self, new_attributes):
		"""Edit object school"""
		flavor = 'schoolwizards/schools'
		if new_attributes.get('home_share_file_server'):
			home_share = new_attributes['home_share_file_server']
		else:
			home_share = 'cn=%s,cn=dc,cn=computers,%s' % (
					self.ucr.get('hostname'), self.ucr.get('ldap/base'))
		if new_attributes.get('class_share_file_server'):
			class_share = new_attributes['class_share_file_server']
		else:
			class_share = 'cn=%s,cn=dc,cn=computers,%s' % (
					self.ucr.get('ldap/master'), self.ucr.get('ldap/base'))
		param =	[
				{
					'object':{
						'$dn$': self.dn(),
						'name': self.name,
						'home_share_file_server': home_share,
						'class_share_file_server': class_share,
						'dc_name': '',
						'display_name': new_attributes['display_name']
						},
					'options': None
					}
				]
		print 'Editing school %s' % (self.name,)
		print 'param = %s' % (param,)
		reqResult = self.umcConnection.request(
				'schoolwizards/schools/put',
				param,
				flavor)
		if not reqResult[0]:
			utils.fail('Unable to edit school (%s) with the parameters (%r)' % (self.name , param))
		else:
			self.home_share_file_server = home_share
			self.class_share_file_server = class_share
			self.display_name = new_attributes['display_name']

	def check_existence(self, should_exist):
		utils.verify_ldap_object(self.dn(), should_exist=should_exist)
