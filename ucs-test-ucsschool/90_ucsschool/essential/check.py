# -*- coding: utf-8 -*-
"""
.. module:: check
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from univention.testing.umc2 import Client
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils


class Check(object):

	"""Contains the needed functuality for checks related to internet rules
	within groups/classes.\n
	:param school: name of the ou
	:type school: str
	:param groupRuleCouples: couples of groups and rules assigned to them
	:type groupRuleCouples: tuple(str,str)
	:param connection:
	:type connection: UMC connection object
	:param ucr:
	:type ucr: UCR object
	"""

	def __init__(self, school, groupRuleCouples, connection=None, ucr=None):
		self.school = school
		self.groupRuleCouples = groupRuleCouples
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		if connection:
			self.client = connection
		else:
			self.ucr.load()
			self.client = Client.get_test_connection()

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
				ruleName = ['-- Default (unrestricted) --', '-- Voreinstellungen (Unbeschränkt) --']
			result = self.client.umc_command('internetrules/groups/query', param).result[0]['rule']
			if result not in ruleName:
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
