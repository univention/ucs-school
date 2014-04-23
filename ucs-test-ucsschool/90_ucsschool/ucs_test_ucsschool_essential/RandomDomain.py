#!/usr/share/ucs-test/runner python

import random
import univention.testing.strings as uts


"""""""""""""""""""""""""""""""""""""""
  Class RandomDomain
"""""""""""""""""""""""""""""""""""""""


class RandomDomain(object):

	# Initialization
	def __init__(self):
		DOMAIN_NAMES = [
			"de", "com", "net", "org", "gov", "info", "me",
			"email", "eu", "at", "uk", "co", "ag", "sy"]
		self.name = uts.random_string()
		self.tail = random.choice(DOMAIN_NAMES)
		self.domain = '%s.%s' % (self.name, self.tail)

	# multi domain getter as a list of domain names
	def getDomainList(self, count):
		domainList = []
		for i in xrange(count):
			dom = self.__class__()
			domainList.append(getattr(dom, 'domain'))
		return domainList
