"""
.. module:: randomdomain
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
import random
import univention.testing.strings as uts


class RandomDomain(object):

	"""Generates random internet domain names"""

	def __init__(self):
		DOMAIN_NAMES = [
			"de", "com", "net", "org", "gov", "info", "me",
			"email", "eu", "at", "uk", "co", "ag", "sy"]
		self.name = uts.random_string()
		self.tail = random.choice(DOMAIN_NAMES)
		self.domain = '%s.%s' % (self.name, self.tail)

	def getDomainList(self, count):
		"""Generate list of domains names\n
		:param count: number of wanted domains
		:type count: int
		:returns: [str] domains list
		"""
		cls = type(self)
		return [cls().domain for i in xrange(count)]
