#!/usr/share/ucs-test/runner python

from univention.lib.umc_connection import UMCConnection
import univention.testing.ucr as ucr_test
import random
import univention.testing.strings as uts
import univention.testing.utils as utils
from . import RandomDomain

"""""""""""""""""""""""""""""""""""""""
  Class InternetRule
  All the operations related to internet rules
"""""""""""""""""""""""""""""""""""""""


class InternetRule(object):

	# Initialization (None is used to invoke the default values)
	def __init__(
			self,
			umcConnection=None,
			ucr=None,
			name=None,
			typ=None,
			domains=None,
			wlan=None,
			priority=None):
		priorities = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
		self.name = name if name else uts.random_string()
		self.type = typ if typ else random.choice(['whitelist', 'blacklist'])
		if domains:
			self.domains = domains
		else:
			dom = RandomDomain.RandomDomain()
			domains = dom.getDomainList(random.choice(priorities))
			self.domains = sorted(domains)
		self.wlan = wlan if wlan else random.choice([True, False])
		self.priority = priority if priority else random.choice(priorities)
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		if umcConnection:
			self.umcConnection = umcConnection
		else:
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

	# define the rule umcp
	def define(self):
		print 'defining rule %s with UMCP:%s' % (
			self.name,
			'internetrules/add')
		param = [
			{
				'object':
				{
					'name': self.name,
					'type': self.type,
					'domains': self.domains,
					'wlan': self.wlan,
					'priority': self.priority
					}
				}
			]
		reqResult = self.umcConnection.request('internetrules/add', param)
		if not reqResult[0]['success']:
			utils.fail('Unable to define rule (%r)' % (param))

	# get the rule umcp
	def get(self, expectedResult):
		print 'Calling %s for %s' % (
			'internetrules/get',
			self.name)
		reqResult = self.umcConnection.request(
			'internetrules/get', [self.name])
		if bool(reqResult) != expectedResult:
			utils.fail(
				'Unexpected fetching result for internet rule (%r)' %
				(self.name))

	# try to modify the internet rule UMCP
	def put(
			self,
			newName,
			newtype,
			newDomains,
			newWlan,
			newPriority):
		param = [
			{
				'object':
				{
					'name': newName,
					'type': newtype,
					'domains': newDomains,
					'wlan': newWlan,
					'priority': newPriority
					},
				'options': {'name': self.name}
				}
			]
		print 'Modifying rule %s with UMCP:%s' % (
			self.name,
			'internetrules/put')
		reqResult = self.umcConnection.request('internetrules/put', param)
		if not reqResult[0]['success']:
			utils.fail('Unable to modify rule (%r)' % (param))
		else:
			self.name = newName
			self.type = newtype
			self.domains = newDomains
			self.wlan = newWlan
			self.priority = newPriority

	# try to remove rule UMCP
	def remove(self):
		print 'Calling %s for %s' % (
			'internetrules/remove',
			self.name)
		options = [{'object': self.name}]
		reqResult = self.umcConnection.request(
			'internetrules/remove',
			options)
		if not reqResult[0]['success']:
			utils.fail('Unable to remove rule (%r)' % (self.name))

	# Fetch the values from ucr and check if it matches
	# the correct values for the rule
	def checkUcr(self, expectedResult):
		print 'Checking UCR for %s' % self.name
		self.ucr.load()
		# extract related items from ucr
		exItems = dict([
			(key.split('/')[-1], value)
			for (key, value) in self.ucr.items() if self.name in key])
		if bool(exItems) != expectedResult:
			utils.fail(
				'Unexpected registery items (expectedResult=%r items=%r)' %
				(expectedResult, exItems))
		elif expectedResult:
			wlan = str(self.wlan).lower()
			typ = self.type
			if self.type == "whitelist":
				typ = "whitelist-block"
			elif self.type == "blacklist":
				typ = "blacklist-pass"
			curtype = exItems['filtertype']
			curWlan = exItems['wlan']
			curPriority = int(exItems['priority'])
			exDomains = dict([
				(key, value)for (key, value) in exItems.items()
				if unicode(key).isnumeric()])
			curDomains = sorted(exDomains.values())
			currentState = (curtype, curPriority, curWlan, curDomains)
			if currentState != (typ, self.priority, wlan, self.domains):
				utils.fail(
					'Values in UCR are not updated for rule (%r)' %
					(self.name))

	# Assign internet rules to workgroups/classes
	# return a tuple (groupName, ruleName)
	def assign(
			self,
			school,
			groupName,
			groupType,
			default=False):
		self.ucr.load()
		basedn = self.ucr.get('ldap/base')
		groupdn = ''
		if groupType == 'workgroup':
			groupdn = 'cn=%s-%s,cn=schueler,cn=groups,ou=%s,%s' % (
				school, groupName, school, basedn)
		elif groupType == 'class':
			groupdn = 'cn=%s-%s,cn=klassen,cn=schueler,cn=groups,ou=%s,%s' % (
				school, groupName, school, basedn)
		if default:
			name = '$default$'
		else:
			name = self.name
		param = [
			{
				'group': groupdn,
				'rule': name
				}
			]
		print 'Assigning rule %s to %s: %s' % (
			self.name,
			groupType,
			groupName)
		result = self.umcConnection.request(
			'internetrules/groups/assign',
			param)
		if not result:
			utils.fail(
				'Unable to assign internet rule to workgroup (%r)' %
				(param))
		else:
			return (groupName, self.name)

	# define multi rules and return list of rules Objects
	def defineList(self, count):
		print 'Defining ruleList'
		ruleList = []
		for i in xrange(count):
			rule = self.__class__(self.umcConnection)
			rule.define()
			ruleList.append(rule)
		return ruleList

	# returns a list of all the existing internet rules via UMCP
	def allRules(self):
		print 'Calling %s' % ('internetrules/query')
		ruleList = []
		rules = self.umcConnection.request(
			'internetrules/query', {'pattern': ''})
		ruleList = sorted([(x['name']) for x in rules])
		return ruleList
