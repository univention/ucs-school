#!/usr/share/ucs-test/runner python

import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.lib.umc_connection import UMCConnection
import univention.testing.ucr as ucr_test

"""""""""""""""""""""""""""""""""""""""
  Class Klasse
"""""""""""""""""""""""""""""""""""""""


class Klasse():

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
			host = self.ucr.get('hostname')
			self.umcConnection = UMCConnection(host)
			self.umcConnection.auth('Administrator', 'univention')

	def __enter__(self):
		with ucr_test.UCSTestConfigRegistry() as ucr:
			self.ucr = ucr
		return self

	def __exit__(self, type, value, trace_back):
		pass

	# create class
	def create(self):
		print 'Creating class %s in school %s' %(
			self.name,
			self.school)
		flavor = 'schoolwizards/classes'
		param = {
			'name': self.name,
			'school': self.school,
			'description': self.description,
			}
		reqResult = self.umcConnection.request(
			'schoolwizards/classes/create',
			param,
			flavor)
		if reqResult is not None:
			utils.fail('Unable to create class (%r)' % (param))

	# create list of random classes returns list of class objects
	def createList(self, count):
		print 'Creating classesList'
		cList = []
		for i in xrange(count):
			c = self.__class__(self.school, self.umcConnection, ucr=self.ucr)
			c.create()
			cList.append(c)
		return cList
