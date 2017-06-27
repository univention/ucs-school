# -*- coding: utf-8 -*-
#
# Univention UCS@school
"""
Create historically unique usernames.
"""
# Copyright 2016-2017 Univention GmbH
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
from univention.admin.uexceptions import noObject, objectExists
from ucsschool.importer.utils.ldap_connection import get_admin_connection, get_machine_connection
from ucsschool.importer.exceptions import BadValueStored, FormatError, NoValueStored, UsernameKeyExists
from ucsschool.importer.utils.logging import get_logger


class UsernameCounterStorageBackend(object):
	def create(self, username, value):
		"""
		Store a value for a new username.

		:param username: str
		:param value: int
		:return: None | objectExists
		"""
		raise NotImplementedError()

	def modify(self, username, old_value, new_value):
		"""
		Store a value for an existing username.

		:param username: str
		:param old_value: int
		:param new_value: int
		:return: None | UsernameKeyExists
		"""
		raise NotImplementedError()

	def retrieve(self, username):
		"""
		Retrieve a value for a username.

		:param username: str
		:return: int | NoValueStored | BadValueStored
		"""
		raise NotImplementedError()


class LdapStorageBackend(UsernameCounterStorageBackend):
	def __init__(self, lo=None, pos=None):
		if lo and pos:
			self.lo, _pos = lo, pos
		else:
			self.lo, _pos = get_admin_connection()

	def create(self, username, value):
		try:
			self.lo.add(
				"cn={},cn=unique-usernames,cn=ucsschool,cn=univention,{}".format(
					escape_dn_chars(username), self.lo.base),
				[
					("objectClass", "ucsschoolUsername"),
					("ucsschoolUsernameNextNumber", str(value))
				]
			)
		except objectExists:
			raise UsernameKeyExists("Cannot create key {!r} - already exists.".format(username))

	def modify(self, username, old_value, new_value):
		try:
			self.lo.modify(
				"cn={},cn=unique-usernames,cn=ucsschool,cn=univention,{}".format(
					escape_dn_chars(username), self.lo.base),
				[("ucsschoolUsernameNextNumber", str(old_value), str(new_value))]
			)
		except noObject:
			raise NoValueStored("Username {!r} not found.".format(username))

	def retrieve(self, username):
		try:
			res = self.lo.get(
				"cn={},cn=unique-usernames,cn=ucsschool,cn=univention,{}".format(
					escape_dn_chars(username), self.lo.base),
				attr=["ucsschoolUsernameNextNumber"])["ucsschoolUsernameNextNumber"][0]
		except (KeyError, noObject):
			raise NoValueStored("Username {!r} not found.".format(username))
		try:
			return int(res)
		except ValueError as exc:
			raise BadValueStored("Value for username {!r} has wrong format: {}".format(username, exc))


class MemoryStorageBackend(UsernameCounterStorageBackend):
	_mem_store = dict()
	ldap_backend = None

	def __init__(self):
		if not self.ldap_backend:
			self.__class__.ldap_backend = LdapStorageBackend(*get_machine_connection())

	def create(self, username, value):
		self._mem_store[username] = value

	def modify(self, username, old_value, new_value):
		self._mem_store[username] = new_value

	def retrieve(self, username):
		try:
			res = self._mem_store[username]
		except KeyError:
			res = self.ldap_backend.retrieve(username)
			self._mem_store[username] = res
		return res


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

	def __init__(self, username_max_length, dry_run=True):
		"""
		:param username_max_length: int: created usernames will be no longer
		than this
		:param dry_run: bool: if False use LDAP to store already-used usernames
		if True store for one run only in memory
		"""
		self.username_max_length = username_max_length
		self.dry_run = dry_run
		self.logger = get_logger()
		self.storage_backend = self.get_storage_backend()
		self.replacement_variable_pattern = re.compile(r'(%s)' % '|'.join(map(re.escape, self.counter_variable_to_function.keys())), flags=re.I)

	def get_storage_backend(self):
		"""
		:return: UsernameCounterStorageBackend instance
		"""
		if self.dry_run:
			return MemoryStorageBackend()
		else:
			return LdapStorageBackend()

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
				raise FormatError('More than one counter variable found in username scheme {!r}.'.format(name), name, name)

			# the variable must no be the [COUNTER] pattern
			without_pattern = self.replacement_variable_pattern.sub('', name)
			without_pattern = self.remove_bad_chars(without_pattern)

			if len(without_pattern) > cut_pos:
				without_pattern = without_pattern[:cut_pos]
				start, end = without_pattern[:match.start()], without_pattern[match.start():]
				username = '%s%s%s' % (start, match.group(), end)
			counter = func(without_pattern) if without_pattern else ''
			username = self.replacement_variable_pattern.sub(counter, username)

		username = self.remove_bad_chars(username)

		if not match and len(name) > self.username_max_length:
			username = username[:self.username_max_length]
			self.logger.warn("Username %r too long, shortened to %r.", name, username)

		username = username.strip('.')
		if not username:
			raise FormatError("No username in {!r}.".format(name), name, name)
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
		return self.get_and_raise(name_base, "1")

	def counter2(self, name_base):
		"""
		[COUNTER2]

		:param name_base: str: the (base) username
		:return: str: number to append to username
		"""
		return self.get_and_raise(name_base, "")

	def get_and_raise(self, name_base, initial_value):
		"""
		Returns the current counter value or initial_value if unset and stores
		it raised by 1.

		:param name_base: str
		:param initial_value: str
		:return str
		"""
		try:
			num = self.storage_backend.retrieve(name_base)
			self.storage_backend.modify(name_base, num, num + 1)
		except NoValueStored:  # not handling BadValueStored, because a data corruption should stop the import
			num = initial_value
			self.storage_backend.create(name_base, 2)
		return str(num)
