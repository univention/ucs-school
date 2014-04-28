#!/usr/share/ucs-test/runner python

"""
.. module:: Workgroup
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from univention.lib.umc_connection import UMCConnection
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils


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
			ucr=None,
			name=None,
			description=None,
			members=None):
		self.school = school
		self.name = name if name else uts.random_string()
		self.description = description if description else uts.random_string()
		self.members = members if members else []
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		if umcConnection:
			self.umcConnection = umcConnection
		else:
			self.ucr = ucr_test.UCSTestConfigRegistry()
			self.ucr.load()
			host = self.ucr.get('hostname')
			self.umcConnection = UMCConnection(host)
			self.umcConnection.auth('Administrator', 'univention')

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace_back):
		self.ucr.revert_to_original_registry()

	def create(self):
		"""Creates object workgroup"""
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
		if not self.umcConnection.request('schoolgroups/add', param, flavor):
			utils.fail('Unable to add workgroup (%r)' % (param))

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
			g.create()
			groupList.append(g)
		return groupList
