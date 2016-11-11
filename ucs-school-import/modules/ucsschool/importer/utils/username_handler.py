# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Create historically unique usernames.
"""
# Copyright 2016 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import re
import string

from ldap.dn import escape_dn_chars
from univention.admin.uexceptions import noObject
from ucsschool.importer.utils.ldap_connection import get_admin_connection
from ucsschool.importer.exceptions import FormatError
from ucsschool.importer.utils.logging import get_logger


class UsernameHandler(object):
	"""
	>>> BAD_CHARS = ''.join(sorted(set(map(chr, range(128))) - set('.1032547698ACBEDGFIHKJMLONQPSRUTWVYXZacbedgfihkjmlonqpsrutwvyxz')))
	>>> UsernameHandler(20).format_username('Max.Mustermann')
	'Max.Mustermann'
	>>> UsernameHandler(20).format_username('Foo[COUNTER2][COUNTER2]')   # doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	FormatError:
	>>> UsernameHandler(20).format_username('.')   # doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	FormatError:
	>>> UsernameHandler(20).format_username('.Max.Mustermann.')
	'Max.Mustermann'
	>>> UsernameHandler(4).format_username('Max.Mustermann')
	'Max'
	>>> for c in BAD_CHARS:
	...  assert 'Max' == UsernameHandler(20).format_username('Ma%sx' % (c,))
	...
	>>> UsernameHandler(20).format_username('Max.Mustermann12.4567890')
	'Max.Mustermann12.456'
	>>> for c in '.1032547698ACBEDGFIHKJMLONQPSRUTWVYXZacbedgfihkjmlonqpsrutwvyxz':
	...  assert 'Ma%sx' % (c,) == UsernameHandler(20).format_username('Ma%sx' % (c,))
	...
	>>> UsernameHandler(20).format_username('Max[Muster]Mann')
	'MaxMusterMann'
	>>> UsernameHandler(20).format_username('Max[ALWAYSCOUNTER].Mustermann')
	'Max1.Mustermann'
	>>> UsernameHandler(20).format_username('Max[ALWAYSCOUNTER].Mustermann')
	'Max2.Mustermann'
	>>> UsernameHandler(20).format_username('Max[ALWAYSCOUNTER].Mustermann')
	'Max3.Mustermann'
	>>> UsernameHandler(20).format_username('Max[COUNTER2].Mustermann')
	'Max4.Mustermann'
	>>> UsernameHandler(20).format_username('Maria[ALWAYSCOUNTER].Musterfrau')
	'Maria1.Musterfrau'
	>>> UsernameHandler(20).format_username('Moritz[COUNTER2]')
	'Moritz'
	>>> UsernameHandler(20).format_username('Moritz[COUNTER2]')
	'Moritz2'
	>>> UsernameHandler(20).format_username('Foo[ALWAYSCOUNTER]')
	'Foo1'
	>>> for i, c in enumerate(BAD_CHARS + BAD_CHARS, 2):
	...  username = UsernameHandler(20).format_username('Fo%so[ALWAYSCOUNTER]' % (c,))
	...  assert 'Foo%d' % (i,) == username, (username, i, c)
	>>> UsernameHandler(8).format_username('aaaa[COUNTER2]bbbbcccc')
	'aaaab'
	>>> UsernameHandler(8).format_username('aaaa[COUNTER2]bbbbcccc')
	'aaaa2b'
	>>> UsernameHandler(8).format_username('bbbb[ALWAYSCOUNTER]ccccdddd')
	'bbbb1c'
	>>> UsernameHandler(8).format_username('bbbb[ALWAYSCOUNTER]ccccdddd')
	'bbbb2c'
	>>> INVALID = ['..[ALWAYSCOUNTER]..', '[ALWAYSCOUNTER]', ]
	>>> for invalid in INVALID:
	...  try:
	...   UsernameHandler(20).format_username(invalid)
	...  except ucsschool.importer.exceptions.FormatError:
	...   pass
	...  else:
	...   raise AssertionError(invalid)
	>>> UsernameHandler(20).format_username('[FOObar]')
	'FOObar'
	"""

	allowed_chars = string.ascii_letters + string.digits + "."

	def __init__(self, username_max_length):
		self.username_max_length = username_max_length
		self.logger = get_logger()
		self.connection, self.position = get_admin_connection()
		self.replacement_variable_pattern = re.compile(r'(%s)' % '|'.join(map(re.escape, self.counter_variable_to_function.keys())), flags=re.I)

	def add_to_ldap(self, username, first_number):
		assert isinstance(username, basestring)
		assert isinstance(first_number, basestring)
		self.connection.add(
			"cn={},cn=unique-usernames,cn=ucsschool,cn=univention,{}".format(
				escape_dn_chars(username), self.connection.base),
			[
				("objectClass", "ucsschoolUsername"),
				("ucsschoolUsernameNextNumber", first_number)
			]
		)

	def get_next_number(self, username):
		assert isinstance(username, basestring)
		try:
			return self.connection.get(
				"cn={},cn=unique-usernames,cn=ucsschool,cn=univention,{}".format(
					escape_dn_chars(username), self.connection.base),
				attr=["ucsschoolUsernameNextNumber"])["ucsschoolUsernameNextNumber"][0]
		except KeyError:
			raise noObject("Username '{}' not found.".format(username))

	def get_and_raise_number(self, username):
		assert isinstance(username, basestring)
		cur = self.get_next_number(username)
		next = int(cur) + 1
		self.connection.modify(
			"cn={},cn=unique-usernames,cn=ucsschool,cn=univention,{}".format(
				escape_dn_chars(username), self.connection.base),
			[("ucsschoolUsernameNextNumber", cur, str(next))]
		)
		return cur

	def remove_bad_chars(self, name):
		"""
		Remove characters disallowed for usernames.
		* Username must only contain numbers, letters and dots, and may not be 'admin'!
		* Username must not start or end in a dot.

		:param name: str: username to check
		:return: str: copy of input, possibly modified
		"""
		bad_chars = ''.join(set(name).difference(set(self.allowed_chars)))
		if bad_chars:
			self.logger.warn("Removing disallowed characters %r from username %r.", ''.join(sorted(bad_chars)), name)
		if name.startswith(".") or name.endswith("."):
			self.logger.warn("Removing disallowed dot from start and end of username %r.", name)
			name = name.strip(".")
		return name.translate(None, bad_chars)

	def format_username(self, name):
		"""
		Create a username from name, possibly replacing a counter variable.
		* This is intended to be called before/by/after ImportUser.format_from_scheme().
		* Supports inserting the counter anywhere in the name, as long as its
		length does not overflow username_max_length.
		* Only one counter variable is allowed.
		* Counters should run only to 999. The algorithm will not honor
		username_max_length for higher numbers!
		* Subclass->override counter_variable_to_function() and the called methods to support
		other schemes than [ALWAYSCOUNTER] and [COUNTER2] or change their meaning.

		:param name: str: username, possibly a template
		:return: str: unique username
		"""
		assert isinstance(name, basestring)
		PATTERN_FUNC_MAXLENGTH = 3  # maximum a counter function can produce is len('999')
		username = name

		match = self.replacement_variable_pattern.search(name)
		if match:
			func = self.counter_variable_to_function[match.group().upper()]
			cut_pos = self.username_max_length - PATTERN_FUNC_MAXLENGTH

			# it's not allowed to have two [COUNTER] patterns
			if len(self.replacement_variable_pattern.findall(name)) >= 2:
				raise FormatError("More than one counter variable found in username scheme '{}'.".format(name), name, name)

			# the variable must no be the [COUNTER] pattern
			without_pattern = self.replacement_variable_pattern.sub('', name)
			without_pattern = self.remove_bad_chars(without_pattern)

			username = name
			if len(without_pattern) > cut_pos:
				without_pattern = without_pattern[:cut_pos]
				start, end = without_pattern[:match.start()], without_pattern[match.start():]
				username = '%s[%s]%s' % (start, match.group(), end)
			counter = func(without_pattern) if without_pattern else ''
			username = self.replacement_variable_pattern.sub(counter, username)

		username = self.remove_bad_chars(username)

		if not match and len(name) > self.username_max_length:
			username = username[:self.username_max_length]
			self.logger.warn("Username %r too long, shortened to %r.", name, username)

		username = username.strip('.')
		if not username:
			raise FormatError("No username in '{}'.".format(name), name, name)
		return username

	@property
	def counter_variable_to_function(self):
		"""
		Subclass->override this to support other variables than [ALWAYSCOUNTER]
		and [COUNTER2] or change their meaning. Add/Modify corresponding
		methods in your subclass.
		Variables have to start with '[', end with ']' and must be all
		upper case.

		:return: dict: variable name -> function
		"""
		return {
			"[ALWAYSCOUNTER]": self.always_counter,
			"[COUNTER2]": self.counter2
		}

	def always_counter(self, name_base):
		"""
		[ALWAYSCOUNTER]

		:param name_base: str: the (base) username
		:return: str: number to append to username
		"""
		return self._counters(name_base, "1")

	def counter2(self, name_base):
		"""
		[COUNTER2]

		:param name_base: str: the (base) username
		:return: str: number to append to username
		"""
		return self._counters(name_base, "")

	def _counters(self, name_base, first_time):
		"""
		Common code of always_counter() and counter2().
		"""
		try:
			num = self.get_and_raise_number(name_base)
		except noObject:
			num = first_time
			self.add_to_ldap(name_base, "2")
		return num
