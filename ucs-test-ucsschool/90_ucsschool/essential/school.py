"""
.. module:: School
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from essential.importou import verify_ou
from univention.lib.umc_connection import UMCConnection
from univention.testing.ucsschool import UCSTestSchool
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
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


class School(object):

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
				 dc_name=None,
				 ucr=None,
				 umcConnection=None):
		self.name = name if name else uts.random_string()
		self.display_name = display_name if display_name else uts.random_string()
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
		singlemaster = self.ucr.is_true('ucsschool/singlemaster')
		if singlemaster:
			self.dc_name = None
		else:
			self.dc_name = dc_name if dc_name else uts.random_string()
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
						'dc_name': self.dc_name,
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
			raise CreateFail('Unable to create school (%r)' % (param,))
		else:
			utils.wait_for_replication()

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
			raise QueryCheckFail('schools from query do not contain the existing schools, found (%r), expected (%r)' % (
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
			raise RemoveFail('Unable to remove school (%s)' % self.name)
		else:
			utils.wait_for_replication()

	def edit(self, new_attributes):
		"""Edit object school"""
		flavor = 'schoolwizards/schools'
		if self.dc_name:
			host = self.dc_name
			home_share = 'cn=%s,cn=dc,cn=server,cn=computers,%s' % (
					host, UCSTestSchool().get_ou_base_dn(self.name))
			class_share = 'cn=%s,cn=dc,cn=server,cn=computers,%s' % (
					host, UCSTestSchool().get_ou_base_dn(self.name))
		else:
			host = self.ucr.get('hostname')
			if new_attributes.get('home_share_file_server'):
				home_share = new_attributes['home_share_file_server']
			else:
				home_share = 'cn=%s,cn=dc,cn=computers,%s' % (
						host, self.ucr.get('ldap/base'))
			if new_attributes.get('class_share_file_server'):
				class_share = new_attributes['class_share_file_server']
			else:
				class_share = 'cn=%s,cn=dc,cn=computers,%s' % (
						host, self.ucr.get('ldap/base'))
		param =	[
				{
					'object':{
						'$dn$': self.dn(),
						'name': self.name,
						'home_share_file_server': home_share,
						'class_share_file_server': class_share,
						'dc_name': self.dc_name,
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
			raise EditFail('Unable to edit school (%s) with the parameters (%r)' % (self.name , param))
		else:
			self.home_share_file_server = home_share
			self.class_share_file_server = class_share
			self.display_name = new_attributes['display_name']
			utils.wait_for_replication()

	def verify_ldap(self, should_exist):
		verify_ou(self.name, self.dc_name, self.ucr, None, None, should_exist)

