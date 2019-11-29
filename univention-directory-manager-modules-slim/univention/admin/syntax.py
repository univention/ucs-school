# -*- coding: utf-8 -*-
#
# Copyright 2004-2019 Univention GmbH
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

"""
|UDM| syntax definitions.
"""

import re
import copy
try:
	from typing import Any, Callable, List, Optional, Pattern, Sequence, Tuple, Type, Union  # noqa F401
except ImportError:
	pass
import ipaddr
from .uexceptions import valueError
# from . import localization


# translation = localization.translation('univention/admin')
# _ = translation.translate
_ = lambda x: x


class ClassProperty(object):
	"""
	A decorator that can be used to define read-only class properties.
	"""

	def __init__(self, getter):
		self.getter = getter

	def __get__(self, instance, owner):
		return self.getter(owner)


SIZES = ('OneThird', 'Half', 'TwoThirds', 'One', 'FourThirds', 'OneAndAHalf', 'FiveThirds')
"""Widget sizes. UDM uses a two-column layout and by default any widget uses one column. Widgets can also be configured to span (partly) both columns."""


class ISyntax(object):
	"""
	Base class for all syntax classes.
	"""
	size = 'One'
	"""Widget size. See :py:data:`SIZES`."""

	@ClassProperty
	def name(cls):
		return cls.__name__

	@ClassProperty
	def type(cls):
		return cls.__name__

	@classmethod
	def tostring(self, text):
		# type: (Any) -> str
		"""
		Convert from internal representation to textual representation.

		:param text: internal representation.
		:returns: textual representation.
		"""
		return text


class simple(ISyntax):
	"""
	Base class for single value entries.
	"""
	regex = None  # type: Optional[Pattern]
	"""Regular expression to validate the value."""
	error_message = _('Invalid value')
	"""Error message when an invalid item is selected."""

	@classmethod
	def parse(self, text):
		# type: (Any) -> str
		"""
		Validate the value by parsing it.

		:return: the parsed textual value.
		:raises valueError: if the value is invalid.
		"""
		if text is None or self.regex is None or self.regex.match(text) is not None:
			return text
		else:
			raise valueError(self.error_message)

	@classmethod
	def new(self):
		"""
		Return the initial value.
		"""
		return ''

	@classmethod
	def any(self):
		"""
		Return the default search filter.
		"""
		return '*'

	@classmethod
	def checkLdap(self, lo, value):
		# type: ("univention.admin.uldap.access", Any) -> Any
		"""
		Check the given value against the current LDAP state by
		reading directly from LDAP directory. The function returns nothing
		or raises an exception, if the value does not match with predefined
		constrains.

		:param lo: LDAP connection.
		:param value: The value to check.
		:returns: None on errors.
		:raises Exception: on errors.
		"""


class gid(simple):
	"""
	Syntax for group account names.
	"""
	min_length = 1
	max_length = 32
	regex = re.compile(r"(?u)^\w([\w -.’]*\w)?$")
	error_message = _(
		"A group name must start and end with a letter, number or underscore. In between additionally spaces, dashes "
		"and dots are allowed."
	)


class string(simple):
	"""
	Syntax for a string with unlimited length.
	"""
	min_length = 0
	max_length = 0

	@classmethod
	def parse(self, text):
		return text


class string_numbers_letters_dots_spaces(simple):
	"""
	Syntax for string consisting of only digits, letters, dots and spaces.
	The later two are not allowed at the beginning and at the end.

	>>> string_numbers_letters_dots_spaces.parse('a') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> string_numbers_letters_dots_spaces.parse('A') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> string_numbers_letters_dots_spaces.parse('0') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> string_numbers_letters_dots_spaces.parse('aA')
	'aA'
	>>> string_numbers_letters_dots_spaces.parse('a.A')
	'a.A'
	>>> string_numbers_letters_dots_spaces.parse('a_A')
	'a_A'
	>>> string_numbers_letters_dots_spaces.parse('a-A')
	'a-A'
	>>> string_numbers_letters_dots_spaces.parse('a A')
	'a A'
	>>> string_numbers_letters_dots_spaces.parse('.') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> string_numbers_letters_dots_spaces.parse('_') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> string_numbers_letters_dots_spaces.parse('-') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> string_numbers_letters_dots_spaces.parse(' ') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> string_numbers_letters_dots_spaces.parse('/') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	"""

	regex = re.compile('(?u)(^[a-zA-Z0-9])[a-zA-Z0-9._ -]*([a-zA-Z0-9]$)')
	error_message = _("Value must not contain anything other than digits, letters, dots or spaces, must be at least 2 characters long, and start and end with a digit or letter!")


class emailAddress(simple):
	"""
	Syntax class for an e-mail address.
	"""
	min_length = 3
	max_length = 0

	@classmethod
	def parse(self, text):
		if not text.startswith('@') and \
			'@' in text and \
			not text.endswith('@'):
			return text
		raise valueError(_("Not a valid email address!"))


class emailAddressValidDomain(emailAddress):
	"""
	Syntax class for an e-mail address in one of the registered e-mail domains.
	"""
	name = 'emailAddressValidDomain'
	errMsgDomain = _("The domain part of the following mail addresses is not in list of configured mail domains: %s")

	@classmethod
	def checkLdap(self, lo, mailaddresses):
		# convert mailaddresses to array if necessary
		mailaddresses = copy.deepcopy(mailaddresses)
		if isinstance(mailaddresses, str):
			mailaddresses = [mailaddresses]
		if not isinstance(mailaddresses, list):
			return

		faillist = []
		domainCache = {}
		# iterate over mail addresses
		for mailaddress in mailaddresses:
			if mailaddress:
				domain = mailaddress.rsplit('@', 1)[-1]
				if domain not in domainCache:
					ldapfilter = '(&(objectClass=univentionMailDomainname)(cn=%s))' % domain
					result = lo.searchDn(filter=ldapfilter)
					domainCache[domain] = bool(result)
				if not domainCache[domain]:
					faillist.append(mailaddress)

		if faillist:
			raise valueError(self.errMsgDomain % (', '.join(faillist),))


class primaryEmailAddressValidDomain(emailAddressValidDomain):
	"""
	Syntax class for the primary e-mail address in one of the registered e-mail domains.
	"""
	name = 'primaryEmailAddressValidDomain'
	errMsgDomain = _("The domain part of the primary mail address is not in list of configured mail domains: %s")


class iso8601Date(simple):
	"""
	A date of the format:

	* yyyy-ddd   (2009-213)
	* yyyy-mm    (2009-05)
	* yyyy-mm-dd (2009-05-13)
	* yyyy-Www   (2009-W21)
	* yyyy-Www-D (2009-W21-4)

	with the dashes being optional
	"""
	# regexp-source: http://regexlib.com/REDetails.aspx?regexp_id=2092
	regex = re.compile('^(\d{4}(?:(?:(?:\-)?(?:00[1-9]|0[1-9][0-9]|[1-2][0-9][0-9]|3[0-5][0-9]|36[0-6]))?|(?:(?:\-)?(?:1[0-2]|0[1-9]))?|(?:(?:\-)?(?:1[0-2]|0[1-9])(?:\-)?(?:0[1-9]|[12][0-9]|3[01]))?|(?:(?:\-)?W(?:0[1-9]|[1-4][0-9]|5[0-3]))?|(?:(?:\-)?W(?:0[1-9]|[1-4][0-9]|5[0-3])(?:\-)?[1-7])?)?)$')
	error_message = _("The given date does not conform to iso8601, example: \"2009-01-01\".")


class uid_umlauts(simple):
	"""
	Syntax for user account names supporting umlauts.
	"""
	name = 'uid'
	min_length = 1
	max_length = 16
	_re = re.compile('(?u)(^\w[\w -.]*\w$)|\w*$')

	@classmethod
	def parse(self, text):
		if " " in text:
			raise valueError(_("Spaces are not allowed in the username!"))
		if self._re.match(text) is not None:
			return text
		else:
			raise valueError(_("Username must only contain numbers, letters and dots!"))


class boolean(simple):
	"""
	Syntax for a boolean checkbox, which internally stores the state as `0` and `1`.

	>>> boolean.parse('')
	''
	>>> boolean.parse('0')
	'0'
	>>> boolean.parse('1')
	'1'
	>>> boolean.parse(True)
	'1'
	>>> boolean.parse(False)
	'0'
	>>> boolean.parse('2') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> boolean.parse('0.1') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> boolean.parse('text') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	"""
	min_length = 1
	max_length = 1
	regex = re.compile('^[01]?$')
	error_message = _("Value must be 0 or 1")

	@classmethod
	def parse(self, text):
		if isinstance(text, bool):
			return '1' if text else '0'
		return super(boolean, self).parse(text)

	@classmethod
	def get_object_property_filter(cls, object_property, object_property_value):
		not_set_filter = '(!(%s=*))' % object_property
		compare_filter = '%s=%s' % (object_property, object_property_value)
		if object_property_value == '0':
			return '(|(%s)%s)' % (compare_filter, not_set_filter)
		elif object_property_value == '1':
			return compare_filter
		else:
			return ''

	@classmethod
	def sanitize_property_search_value(cls, search_value):
		return '1' if search_value is True else '0'


class UDM_Objects(ISyntax):
	"""
	Base class to lookup selectable items from |LDAP| enties using their |DN|.

	See :py:class:`UDM_Attribute` for an alternative to use values from one |LDAP| entry..
	"""
	udm_modules = ()  # type: Sequence[str]
	"""Sequence of |UDM| module names to search for."""
	udm_filter = ''
	"""A |LDAP| filter string to further restrict the matching |LDAP| objects."""
	key = 'dn'
	"""The |LDAP| attribute name to use as the value for this syntax class."""
	label = None
	"""The |UDM| property name, which is used as the displayed value."""
	regex = re.compile('^([^=,]+=[^=,]+,)*[^=,]+=[^=,]+$')
	"""Regular expression for validating the values."""
	static_values = None  # type: Optional[Sequence[Tuple[str, str]]]
	"""Sequence of additional static items."""
	empty_value = False
	"""Allow to select no entry."""
	depends = None  # type: Optional[str]
	"""The name of another |UDM| property this syntax sepends on."""
	error_message = _("Not a valid LDAP DN")
	"""Error message when an invalid item is selected."""
	simple = False  # by default a MultiObjectSelect widget is used; if simple == True a ComboBox is used
	"""With `True`, only a single object can be selected using a ComboBox. With `False` multiple entries can be selected using a MultiObjectSelect widget."""
	use_objects = True
	"""By default with `True` create Python UDM instance for each LDAP entry. With `False` only work with the LDAP attribute data."""

	@classmethod
	def parse(self, text):
		if not self.empty_value and not text:
			raise valueError(_('An empty value is not allowed'))
		if not text or not self.regex or self.regex.match(text) is not None:
			return text
		raise valueError(self.error_message)


class UserDN(UDM_Objects):
	"""
	Syntax to select an user from |LDAP| by |DN|.

	.. seealso::
	   * :py:class:`UserID`
	"""
	udm_modules = ('users/user', )
	use_objects = False


class GroupDN(UDM_Objects):
	"""
	Syntax to select a group from |LDAP| by |DN|.

	.. seealso::
	   * :py:class:`GroupID`
	   * :py:class:`GroupDNOrEmpty`
	"""
	udm_modules = ('groups/group', )
	use_objects = False


class ipAddress(simple):
	"""
	Syntax class for an IPv4 or IPv6 address.
	`0.0.0.0` and IPv4-mapped IPv6 addresses are allowed.

	>>> ipAddress.parse('0.0.0.0')
	'0.0.0.0'
	>>> ipAddress.parse('::1')
	'::1'
	"""
	@classmethod
	def parse(self, text):
		try:
			return str(ipaddr.IPAddress(text))
		except ValueError:
			raise valueError(_("Not a valid IP address!"))


class MAC_Address(simple):
	"""
	Syntax to enter MAC address.
	The address is stored with octets separated by `:`.

	>>> MAC_Address.parse('86:f5:d1:f5:6b:3e')
	'86:f5:d1:f5:6b:3e'
	>>> MAC_Address.parse('86-f5-d1-f5-6b-3e')
	'86:f5:d1:f5:6b:3e'
	>>> MAC_Address.parse('86f5d1f56b3e')
	'86:f5:d1:f5:6b:3e'
	>>> MAC_Address.parse('86f5.d1f5.6b3e')
	'86:f5:d1:f5:6b:3e'
	"""
	regexLinuxFormat = re.compile(r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')
	regexWindowsFormat = re.compile(r'^([0-9a-fA-F]{2}-){5}[0-9a-fA-F]{2}$')
	regexRawFormat = re.compile(r'^[0-9a-fA-F]{12}$')
	regexCiscoFormat = re.compile(r'^([0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}$')
	error_message = _('This is not a valid MAC address (valid examples are 86:f5:d1:f5:6b:3e, 86-f5-d1-f5-6b-3e, 86f5d1f56b3e, 86f5.d1f5.6b3e)')

	@classmethod
	def parse(self, text):
		if self.regexLinuxFormat.match(text) is not None:
			return text.lower()
		elif self.regexWindowsFormat.match(text) is not None:
			return text.replace('-', ':').lower()
		elif self.regexRawFormat.match(text) is not None:
			temp = []
			for i in range(0, len(text) - 1, 2):
				temp.append(text[i:i + 2])
			return ':'.join(temp).lower()
		elif self.regexCiscoFormat.match(text) is not None:
			tmpList = []
			tmpStr = text.translate(None, '.')
			for i in range(0, len(tmpStr) - 1, 2):
				tmpList.append(tmpStr[i:i + 2])
			return ':'.join(tmpList).lower()
		else:
			raise valueError(self.error_message)


class disabled(boolean):
	"""
	Syntax to select account disabled state.
	"""
	@classmethod
	def parse(cls, text):
		if text in ('none', 'none2'):
			text = '0'
		elif text in ('all', 'windows', 'kerberos', 'posix', 'windows_posix', 'windows_kerberos', 'posix_kerberos'):
			text = '1'
		return super(disabled, cls).parse(text)


class reverseLookupSubnet(simple):
	"""
	Syntax for IPv4 or IPv6 sub-network.

	>>> reverseLookupSubnet.parse('1.2.3')
	'1.2.3'
	>>> reverseLookupSubnet.parse('1')
	'1'
	>>> reverseLookupSubnet.parse('1000:2000:3000:4000:5000:6000:7000:800')
	'1000:2000:3000:4000:5000:6000:7000:800'
	"""
	#               <-                      0-255                     ->  *dot  <-                      0-255                     ->
	regex_IPv4 = r'((([1-9]?[0-9])|(1[0-9]{0,2})|(2([0-4][0-9]|5[0-5])))\.){1,2}(([1-9]?[0-9])|(1[0-9]{0,2})|(2([0-4][0-9]|5[0-5])))'
	# normal IPv6 address without "::" substitution, leading zeroes must be preserved, at most 31 nibbles
	regex_IPv6 = r'(([0-9a-f]{4}:){0,7}[0-9a-f]{1,3})|(([0-9a-f]{4}:){0,6}[0-9a-f]{1,4})'
	regex = re.compile(r'^((%s)|(%s))$' % (regex_IPv4, regex_IPv6, ))
	error_message = _('A subnet for reverse lookup consists of the first 1-3 octets of an IPv4 address (example: "192.168.0") or of the first 1 to 31 nibbles of an expanded (with leading zeroes and without ::-substitution) IPv6 address (example: "2001:0db8:010" for "2001:db8:100::/24")')


class ipv4Address(simple):
	"""
	Syntax class for an IPv4 address.
	`0.0.0.0` is allowed.

	>>> ipv4Address.parse('0.0.0.0')
	'0.0.0.0'
	"""
	@classmethod
	def parse(self, text):
		try:
			return str(ipaddr.IPv4Address(text))
		except ValueError:
			raise valueError(_("Not a valid IP address!"))


class integer(simple):
	"""
	Syntax for positive numeric values.

	* :py:class:`integerOrEmpty`

	>>> integer.parse('1')
	'1'
	>>> integer.parse('0')
	'0'
	>>> integer.parse('-1') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> integer.parse('1.1') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> integer.parse('text') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	>>> integer.parse('') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
		...
	valueError:
	"""
	min_length = 1
	max_length = 0
	_re = re.compile('^[0-9]+$')
	size = 'Half'

	@classmethod
	def parse(self, text):
		if self._re.match(text) is not None:
			return text
		else:
			raise valueError(_("Value must be a number!"))


class v4netmask(simple):
	"""
	Syntax for a IPv4 network mask.
	May be entered as a *bit mask* or the number of bits.

	>>> v4netmask.parse('255.255.255.0')
	'24'
	>>> v4netmask.parse('24')
	'24'
	>>> v4netmask.parse('0.0.0.0')
	'0'
	>>> v4netmask.parse('255.255.255.255')
	'32'
	>>> v4netmask.parse('33') #doctest: +IGNORE_EXCEPTION_DETAIL +SKIP
	Traceback (most recent call last):
	...
	valueError: Not a valid netmask!
	"""
	min_length = 1
	max_length = 15

	@classmethod
	def netmaskBits(self, dotted):
		def splitDotted(ip):
			quad = [0, 0, 0, 0]

			i = 0
			for q in ip.split('.'):
				if i > 3:
					break
				quad[i] = int(q)
				i += 1

			return quad

		dotted = splitDotted(dotted)

		bits = 0
		for d in dotted:
			for i in range(0, 8):
				if ((d & 2**i) == 2**i):
					bits += 1
		return bits

	@classmethod
	def parse(self, text):
		_ip = ipv4Address()
		_int = integer()
		errors = 0
		try:
			_ip.parse(text)
			return "%d" % self.netmaskBits(text)
		except Exception:
			try:
				_int.parse(text)
				if int(text) > 0 and int(text) < 32:
					return text
			except Exception:
				errors = 1
		if errors:
			# FIXME: always raise exception here!
			raise valueError(_("Not a valid netmask!"))


class netmask(simple):
	"""
	Syntax for a IPv4 network mask.
	May be entered as a *bit mask* or the number of bits.

	>>> netmask.parse('255.255.255.0')
	'24'
	>>> netmask.parse('1')
	'1'
	>>> netmask.parse('127')
	'127'
	>>> netmask.parse('0') #doctest: +IGNORE_EXCEPTION_DETAIL +SKIP
	Traceback (most recent call last):
	...
	valueError: Not a valid netmask!
	>>> netmask.parse('128') #doctest: +IGNORE_EXCEPTION_DETAIL
	Traceback (most recent call last):
	...
	valueError: Not a valid netmask!
	"""

	@classmethod
	def parse(self, text):
		if text.isdigit() and int(text) > 0 and int(text) < max(ipaddr.IPV4LENGTH, ipaddr.IPV6LENGTH):
			return str(int(text))
		try:
			return str(ipaddr.IPv4Network('0.0.0.0/%s' % (text, )).prefixlen)
		except ValueError:
			pass
		raise valueError(_("Not a valid netmask!"))


if __name__ == '__main__':
	import doctest
	doctest.testmod()
