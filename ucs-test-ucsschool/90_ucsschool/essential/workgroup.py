"""
.. module:: Workgroup
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from univention.lib.umc_connection import UMCConnection
import httplib
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils
import univention.uldap as uu
from univention.testing.ucsschool import UCSTestSchool


class Workgroup(object):

	"""Contains the needed functuality for workgroups in an already created OU,
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
	:param members: list of dns of members
	:type members: [str=memberdn]
	"""

	def __init__(
			self,
			school,
			umcConnection=None,
			ulConnection =None,
			ucr=None,
			name=None,
			description=None,
			members=None):
		self.school = school
		self.name = name if name else uts.random_string()
		self.description = description if description else uts.random_string()
		self.members = members if members else []
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
		if ulConnection:
			self.ulConnection = ulConnection
		else:
			self.ulConnection = uu.getMachineConnection(ldap_master=False)
		if umcConnection:
			self.umcConnection = umcConnection
		else:
			host = self.ucr.get('hostname')
			self.umcConnection = UMCConnection(host)
			account = utils.UCSTestDomainAdminCredentials()
			admin = account.username
			passwd = account.bindpw
			self.umcConnection.auth(admin, passwd)

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace_back):
		self.ucr.revert_to_original_registry()

	def create(self, expect_creation_fails_due_to_duplicated_name=False):
		"""Creates object workgroup\n
		:param expect_creation_fails_due_to_duplicated_name: if user allow duplicate names no exception is
		raised, no group is created either
		:type expect_creation_fails_due_to_duplicated_name: bool
		"""
		try:
			createResult = self._create()
			if createResult and expect_creation_fails_due_to_duplicated_name:
				utils.fail('Workgroup %s already exists, though a new workgroup is created with a the same name' % self.name )
			utils.wait_for_replication()
		except httplib.HTTPException as e:
			 exception_strings = [
					 'The groupname is already in use as groupname or as username',
					 'Der Gruppenname wird bereits als Gruppenname oder als Benutzername verwendet']
			 for entry in exception_strings:
				 if expect_creation_fails_due_to_duplicated_name and entry in str(e):
					 print('Fail : %s' % (e) )
					 break
			 else:
				 print("Exception: '%s' '%s' '%r'" % (str(e), type(e), e))
				 raise

	def _create(self):
		print 'Creating workgroup %s in school %s' % (
			self.name,
			self.school)
		flavor = 'workgroup-admin'
		param = [
			{
				'object': {
					'name': self.name,
					'school': self.school,
					'members': self.members,
					'description': self.description
					}
				}
			]
		requestResult = self.umcConnection.request(
				'schoolgroups/add',
				param,
				flavor)
		if not requestResult:
			utils.fail('Unable to add workgroup (%r)' % (param,))
		return requestResult

	def createList(self, count):
		"""create list of random workgroups returns list of groups objects\n
		:param count: number of wanted workgroups
		:type count: int
		:returns: [workgroup_object]
		"""
		print 'Creating groupList'
		groupList = []
		for i in xrange(count):
			g = self.__class__(self.school)
			g._create()
			groupList.append(g)
		utils.wait_for_replication()
		return groupList

	def remove(self, options=None):
		"""Removing a Workgroup from ldap"""
		print 'Removing group %s from ldap' % (self.name)
		groupdn = self.dn()
		flavor = 'workgroup-admin'
		removingParam = [{"object":[groupdn],"options":options}]
		requestResult = self.umcConnection.request(
				'schoolgroups/remove',
				removingParam,
				flavor)
		if not requestResult:
			utils.fail('Group %s failed to be removed' % self.name)
		utils.wait_for_replication()

	def addMembers(self, memberListdn, options=None):
		"""Add members to workgroup\n
		:param memberListdn: list of the new members
		:type memberListdn: list
		:param options:
		:type options: None
		"""
		print 'Adding members  %r to group %s' % (memberListdn, self.name)
		groupdn = self.dn()
		currentMembers = sorted(
				self.ulConnection.getAttr(groupdn,'uniqueMember'))
		for member in memberListdn:
			if member not in currentMembers:
				currentMembers.append(member)
			else:
				print('member', member, 'already exist in the group')
		self.set_members(currentMembers)

	def removeMembers(self, memberListdn, options=None):
		"""Remove members from workgroup\n
		:param memberListdn: list of the removed members
		:type memberListdn: list
		:param options:
		:type options: None
		"""
		print 'Removing members  %r from group %s' % (memberListdn, self.name)
		groupdn = self.dn()
		currentMembers = sorted(
				self.ulConnection.getAttr(groupdn, 'uniqueMember'))
		for member in memberListdn:
			if member in currentMembers:
				currentMembers.remove(member)
		self.set_members(currentMembers)

	def set_members(self, new_members, options=None):
		"""Set members for workgroup\n
		:param new_members: list of the new members
		:type new_members: list
		"""
		print 'Setting members  %r from group %s' % (new_members, self.name)
		flavor = 'workgroup-admin'
		groupdn = self.dn()
		creationParam = [{
			'object':{
				'$dn$' :	groupdn,
				'school':	self.school,
				'name' :	self.name,
				'description':	self.description,
				'members':	new_members
				},
			'options':	options
			}]
		requestResult = self.umcConnection.request(
				'schoolgroups/put',
				creationParam,
				flavor)
		if not requestResult:
			utils.fail('Members %s failed to be set' % new_members)
		else:
			self.members = new_members
		utils.wait_for_replication()

	def verify_ldap_attributes(self):
		"""checking group attributes in ldap"""
		print 'Checking the attributes for group %s in ldap' % (self.name)
		members = []
		if self.members:
			for member in self.members:
				m = member.split(',')[0][4:]
				members.append(m)

		utils.verify_ldap_object(
				self.dn(),
				expected_attr = {
					'memberUid': members,
					'description': [self.description]
					})

	def verify_exists(self, group_should_exist, share_should_exist):
		"""check for group and file share objects existance in ldap"""
		print 'Checking if group %s and its share object exist in ldap' % (self.name)
		groupdn = self.dn()
		utils.verify_ldap_object(groupdn, should_exist=group_should_exist)
		ucsschool = UCSTestSchool()
		sharedn = 'cn=%s-%s,cn=shares,%s' % (
					self.school,
					self.name,
					ucsschool.get_ou_base_dn(self.school))
		utils.verify_ldap_object(sharedn, should_exist=share_should_exist)


	def dn(self):
		ucsschool = UCSTestSchool()
		groupdn = ucsschool.get_workinggroup_dn(self.school, self.name)
		return groupdn
