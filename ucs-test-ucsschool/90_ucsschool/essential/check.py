#!/usr/share/ucs-test/runner python

from univention.lib.umc_connection import UMCConnection
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils

"""""""""""""""""""""""""""""""""""""""
  Class Check
  resposible of all the checks operations on rules/groups
"""""""""""""""""""""""""""""""""""""""


class Check(object):

	# Initialization
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

	# check if the assigned internet rules are correct UMCP
	def checkRules(self):
		for groupName, ruleName in self.groupRuleCouples:
			print 'Checking %s rules' % (groupName)
			param = {
				'school': self.school,
				'pattern': groupName
				}
			if ruleName is None:
				ruleName_eng = '-- default settings --'
				ruleName_deu = '-- Voreinstellungen --'
			result = self.umcConnection.request(
				'internetrules/groups/query',
				param)[0]['rule']
			if result != ruleName_eng and result != ruleName_deu:
				utils.fail(
					'Assigned rule (%r) to workgroup (%r) doesn\'t match' %
					(ruleName, groupName))

	# check ucr variables for groups/ classes internet rules
	def checkUcr(self):
		self.ucr.load()
		for groupName, ruleName in self.groupRuleCouples:
			print 'Checking %s UCR variables' % (groupName)
			groupid = 'proxy/filter/groupdefault/%s-%s' % (
				self.school, groupName)
			if self.ucr.get(groupid) != ruleName:
				utils.fail(
					'Ucr variable (%r) is not correctly set' % (groupid))
