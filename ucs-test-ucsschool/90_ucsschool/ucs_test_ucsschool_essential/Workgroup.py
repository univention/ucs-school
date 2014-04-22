#!/usr/share/ucs-test/runner python

import univention.testing.strings as uts
import univention.testing.utils as utils
import univention.testing.ucr as ucr_test
from univention.lib.umc_connection import UMCConnection

"""""""""""""""""""""""""""""""""""""""
  Class Workgroup
"""""""""""""""""""""""""""""""""""""""


class Workgroup(object):

	# Initialization (Random by default)
	def __init__(self,
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
		with ucr_test.UCSTestConfigRegistry() as ucr:
			self.ucr = ucr
		return self

	def __exit__(self, type, value, trace_back):
		pass

	# Create workgroup UMCP
	def create(self):
		print 'Ceate workgroup %s in school %s' % (
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

	# create list of random workgroups returns list of groups objects
	def createList(self, count):
		print 'Creating groupList'
		groupList = []
		for i in xrange(count):
			g = self.__class__(self.school)
			g.create()
			groupList.append(g)
		return groupList
