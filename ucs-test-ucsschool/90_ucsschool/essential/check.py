"""
.. module:: check
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from univention.lib.umc_connection import UMCConnection
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils


class Check(object):

	"""Contains the needed functuality for checks related to internet rules
     within groups/classes.\n
	:param school: name of the ou
	:type school: str
	:param groupRuleCouples: couples of groups and rules assigned to them
	:type groupRuleCouples: tuple(str,str)
	:param umcConnection:
	:type umcConnection: UMC connection object
	:param ucr:
	:type ucr: UCR object
	"""

	def __init__(
			self,
			school,
			groupRuleCouples,
			umcConnection=None,
			ucr=None):
		self.school = school
		self.groupRuleCouples = groupRuleCouples
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		if umcConnection:
			self.umcConnection = umcConnection
		else:
			self.ucr.load()
			host = self.ucr.get('hostname')
			self.umcConnection = UMCConnection(host)
			self.umcConnection.auth('Administrator', 'univention')

	def __enter__(self):
		return self

	def __exit__(self, type, value, trace_back):
		self.ucr.revert_to_original_registry()

	def checkRules(self):
		"""Check if the assigned internet rules are correct UMCP"""
		for groupName, ruleName in self.groupRuleCouples:
			print 'Checking %s rules' % (groupName)
			param = {
				'school': self.school,
				'pattern': groupName
				}
			if ruleName is None:
				ruleName = '-- default settings --' + '-- Voreinstellungen --'
			result = self.umcConnection.request(
				'internetrules/groups/query',
				param)[0]['rule']
			if not result in ruleName:
				utils.fail(
					'Assigned rule (%r) to workgroup (%r) doesn\'t match' %
					(ruleName, groupName))

	def checkUcr(self):
		"""Check ucr variables for groups/ classes internet rules"""
		self.ucr.load()
		for groupName, ruleName in self.groupRuleCouples:
			print 'Checking %s UCR variables' % (groupName)
			groupid = 'proxy/filter/groupdefault/%s-%s' % (
				self.school, groupName)
			if self.ucr.get(groupid) != ruleName:
				utils.fail(
					'Ucr variable (%r) is not correctly set' % (groupid))
