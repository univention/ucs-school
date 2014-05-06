#!/usr/share/ucs-test/runner python

"""
.. module:: Klasse
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.lib.umc_connection import UMCConnection
import univention.testing.ucr as ucr_test


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
			host = self.ucr.get('hostname')
			self.umcConnection = UMCConnection(host)
			self.umcConnection.auth('Administrator', 'univention')

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
