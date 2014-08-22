"""""""""""""""""""""""""""""""""""""""
  **Class InternetRule**\n
  All the operations related to internet rules
"""""""""""""""""""""""""""""""""""""""
"""
.. module:: internetrule
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from .randomdomain import RandomDomain
from univention.lib.umc_connection import UMCConnection
import random
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils
from univention.testing.ucsschool import UCSTestSchool
import univention.testing.ucsschool as utu


class InternetRule(object):

	"""Contains the needed functionality for internet rules.
	By default they are randomly formed\n
	:param umcConnection:
	:type umcConnection: UMC connection object
	:param ucr:
	:type ucr: UCR object
	:param name: name of the internet rule to be created later
	:type name: str
	:param typ: type of the internet rule to be created later
	:type typ: str='whitelist' or 'blacklist'
	:param domains: list of the internet rule to be created later
	:type domains: [str]
	:param wlan: if the internet rule supports wlan
	:type wlan: bool
	:param priority: priority of the internet rule [1,10]
	:type priority: [int]
	"""
	def __init__(
			self,
			umcConnection=None,
			ucr=None,
			name=None,
			typ=None,
			domains=None,
			wlan=None,
			priority=None):
		self.name = name if name else uts.random_string()
		self.typ = typ if typ else random.choice(['whitelist', 'blacklist'])
		if domains:
			self.domains = domains
		else:
			dom = RandomDomain()
			domains = dom.getDomainList(random.randint(1, 10))
			self.domains = sorted(domains)
		if wlan==True or wlan==False:
			self.wlan = wlan
		else:
			self.wlan = random.choice([True, False])
		self.priority = priority if priority else random.randint(1, 10)
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		if umcConnection:
			self.umcConnection = umcConnection
		else:
			self.ucr.load()
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

	# define the rule umcp
	def define(self):
		"""Define internet rule via UMCP"""
		param = [
			{
				'object':
				{
					'name': self.name,
					'type': self.typ,
					'domains': self.domains,
					'wlan': self.wlan,
					'priority': self.priority
					}
				}
			]
		print 'defining rule %s with UMCP:%s' % (
			self.name,
			'internetrules/add')
		print 'param = %r' % (param,)
		reqResult = self.umcConnection.request('internetrules/add', param)
		if not reqResult[0]['success']:
			utils.fail('Unable to define rule (%r)' % (param,))

	def get(self, should_exist):
		"""gets internet rule via UMCP\n
		:param should_exist: True if the rule is expected to be found
		:type should_exist: bool"""
		print 'Calling %s for %s' % (
			'internetrules/get',
			self.name)
		reqResult = self.umcConnection.request(
			'internetrules/get', [self.name])
		if bool(reqResult) != should_exist:
			utils.fail(
				'Unexpected fetching result for internet rule (%r)' %
				(self.name))

	def put(
			self,
			new_name=None,
			new_type=None,
			new_domains=None,
			new_wlan=None,
			new_priority=None):
		"""Modify internet rule via UMCP\n
		with no args passed this only reset the rule properties\n
		:param new_name:
		:type new_name: str
		:param new_type:
		:type new_type: str
		:param new_domains:
		:type new_domains: [str]
		:param new_wlan:
		:type new_wlan: bool
		:param new_priority:
		:type new_priority: int [1,10]
		"""
		new_name = new_name if new_name else self.name
		new_type = new_type if new_type else self.typ
		new_domains = new_domains if new_domains else self.domains
		new_wlan = new_wlan if new_wlan else self.wlan
		new_priority = new_priority if new_priority else self.priority

		param = [
			{
				'object':
				{
					'name': new_name,
					'type': new_type,
					'domains': new_domains,
					'wlan': new_wlan,
					'priority': new_priority
					},
				'options': {'name': self.name}
				}
			]
		print 'Modifying rule %s with UMCP:%s' % (
			self.name,
			'internetrules/put')
		print 'param = %r' % (param,)
		reqResult = self.umcConnection.request('internetrules/put', param)
		if not reqResult[0]['success']:
			utils.fail('Unable to modify rule (%r)' % (param,))
		else:
			self.name = new_name
			self.typ = new_type
			self.domains = new_domains
			self.wlan = new_wlan
			self.priority = new_priority

	def remove(self):
		"""removes internet rule via UMCP"""
		print 'Calling %s for %s' % (
			'internetrules/remove',
			self.name)
		options = [{'object': self.name}]
		reqResult = self.umcConnection.request(
			'internetrules/remove',
			options)
		if not reqResult[0]['success']:
			utils.fail('Unable to remove rule (%r)' % (self.name,))

	# Fetch the values from ucr and check if it matches
	# the correct values for the rule
	def checkUcr(self, should_match):
		"""check ucr for internet rule\n
		Fetch the values from ucr and check if it matches
		the correct values for the rule\n
		:param should_match:
		:type  should_match: bool
		"""
		print 'Checking UCR for %s' % self.name
		self.ucr.load()
		# extract related items from ucr
		exItems = dict([
			(key.split('/')[-1], value)
			for (key, value) in self.ucr.items() if self.name in key])
		if bool(exItems) != should_match:
			utils.fail(
				'Unexpected registery items (should_match=%r items=%r)' %
				(should_match, exItems))
		elif should_match:
			wlan = str(self.wlan).lower()
			typ = self.typ
			if self.typ == "whitelist":
				typ = "whitelist-block"
			elif self.typ == "blacklist":
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
		"""Assign internet rule via UMCP\n
		:param school: name of the ou
		:type school: str
		:param groupName: name of the group or class
		:type groupName: str
		:param groupType: 'workgroup' or 'class'
		:type groupType: str
		:param default: if the group is assigned to default values
		:type default: bool
		"""
		self.ucr.load()
		groupdn = ''
		schoolenv = utu.UCSTestSchool()
		school_basedn = schoolenv.get_ou_base_dn(school)

		if groupType == 'workgroup':
			ucsschool = UCSTestSchool()
			groupdn = ucsschool.get_workinggroup_dn(school, groupName)
		elif groupType == 'class':
			groupdn = 'cn=%s-%s,cn=klassen,cn=schueler,cn=groups,%s' % (
				school, groupName, school_basedn)

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
		print 'param = %r' % (param,)
		result = self.umcConnection.request(
			'internetrules/groups/assign',
			param)
		if not result:
			utils.fail(
				'Unable to assign internet rule to workgroup (%r)' %
				(param,))
		else:
			return (groupName, self.name)

	# define multi rules and return list of rules Objects
	def defineList(self, count):
		"""Define list of random internet rules\n
		:param count: number of wanted rules
		:type count: int
		:returns: list of rule objects
		"""
		print 'Defining ruleList'
		ruleList = []
		for i in xrange(count):
			rule = self.__class__(self.umcConnection)
			rule.define()
			ruleList.append(rule)
		return ruleList

	# returns a list of all the existing internet rules via UMCP
	def allRules(self):
		"""Get all defined rules via UMCP\n
		:returns: [str] list of rules names
		"""
		print 'Calling %s = get all defined rules' % ('internetrules/query')
		ruleList = []
		rules = self.umcConnection.request(
			'internetrules/query', {'pattern': ''})
		ruleList = sorted([(x['name']) for x in rules])
		return ruleList
