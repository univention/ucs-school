#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Dynamic LDAP ACL generation
#
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
import sys
import ldap
import ldap.dn
import ldap.filter

import univention.config_registry

ucr = univention.config_registry.ConfigRegistry()
ucr.load()


class Object(object):

	@classmethod
	def new(cls, *args, **kwargs):
		if args and isinstance(args[0], cls):
			return args[0]
		return cls(*args, **kwargs)


class AccessRule(Object):

	def __init__(self, dn=None, dnstyle=None, filter=None, attrs=None, by=None, comment=None):
		self.comment = comment
		if isinstance(attrs, basestring):
			attrs = attrs.split(',')
		self.acl = ACL(What(dn, attrs, filter, dnstyle), Bys(by))

	def __str__(self):
		accessrule = ''
		if self.comment:
			accessrule += '# %s\n' % (repr(self.comment).strip('"\''),)
		accessrule += str(self.acl)
		return accessrule


class ACL(Object):
	"""access to <what> [ by <who> [ <access> ] [ <control> ] ]+"""

	def __init__(self, what, bys=None):
		self.what = What.new(what)
		self.bys = bys and Bys.new(bys)

	def __str__(self):
		acl = 'access to %s\n' % (self.what,)
		if self.bys:
			acl += '\t%s\n' % (self.bys,)
		acl += '\n'
		return acl


class What(Object):
	"""what = <dn> <filter> <attrs>"""

	def __init__(self, dn=None, attrs=None, filter=None, dnstyle=None):
		self.dn = dn and DN.new(dn, dnstyle)
		self.attrs = attrs and Attrs.new(attrs)
		self.filter = filter and Filter.new(filter)
		if not self.dn and not self.attrs and not self.filter:
			raise TypeError('what=None != <dn> <filter> <attrs>')

	def __str__(self):
		what = ''
		if self.dn:
			what += str(self.dn)
		if self.filter:
			what += ' %s' % (self.filter,)
		if self.attrs:
			what += ' %s' % (self.attrs,)
		return what


class DN(Object):
	"""
		dn[.<dnstyle>]=<dnpattern>
		<dnstyle>={{exact|base(object)}|regex|one(level)|sub(tree)|children}
	"""

	def __init__(self, dn, dnstyle=None):
		self.dnpattern = dn
		if '%' in self.dnpattern:
			self.dnpattern = self.dnpattern % ucr
		self.dnstyle = (dnstyle or 'base').lower()
		if self.dnstyle not in ('exact', 'base', 'baseobject', 'regex', 'one', 'onelevel', 'sub', 'subtree', 'children'):
			raise TypeError('dnstyle=%r != {{exact|base(object)}|regex|one(level)|sub(tree)|children}' % (self.dnstyle,))
		if self.dnstyle != 'regex':
			try:
				ldap.dn.str2dn(self.dnpattern)
			except ldap.DECODING_ERROR:
				raise TypeError('dn=%r != <dnpattern>' % (self.dnpattern,))
		else:
			try:
				re.compile(self.dnpattern)  # FIXME: posix-regex != python-regex
			except re.error as exc:
				print >> sys.stderr, 'WARNING: regex=%r might be wrong: %s' % (self.dn, exc)

	def __str__(self):
		dn = 'dn'
		if self.dnstyle:
			dn += '.%s' % (self.dnstyle,)
		dn += '="%s"' % (self.dnpattern,)
		return dn


class Attrs(Object):
	"""
		attrs=<attrlist>[ val[/matchingRule][.<attrstyle>]=<attrval>]
		<attrlist>={<attr>|[{!|@}]<objectClass>}[,<attrlist>]
		<attrstyle>={{exact|base(object)}|regex|one(level)|sub(tree)|children}
	"""

	def __init__(self, attrs):
		self.attrs = [Attr.new(attr) for attr in attrs]
		if len(self.attrs) > 1 and sum(a for a in self.attrs if a.value):
			raise TypeError('attr=%r != <attrlist>[ val[/matchingRule][.<attrstyle>]=<attrval>]' % (self,))

	def __str__(self):
		return 'attrs="%s"' % (','.join(str(attr) for attr in self.attrs))


class Attr(Object):

	def __init__(self, attr, value=None, attrstyle=None, matchingrule=None):
		self.attr = attr
		self.value = value
		self.attrstyle = (attrstyle or '').lower()
		self.matchingrule = matchingrule

		if self.attrstyle and self.attrstyle not in ('exact', 'base', 'baseobject', 'regex', 'one', 'onelevel', 'sub', 'subtree', 'children'):
			raise TypeError('attrstyle=%r != {{exact|base(object)}|regex|one(level)|sub(tree)|children}' % (self.attrstyle,))

	def __str__(self):
		attr = self.attr
		if self.value:
			attr += ' value'
			if self.matchingrule:
				attr += '/%s' % (self.matchingrule,)
			if self.attrstyle:
				attr += '.%s' % (self.attrstyle,)
			attr += '="%s"' % (self.value,)
		return attr


class Filter(Object):
	"""
		filter=<ldapfilter>
	"""
	def __init__(self, filter):
		self.filter = filter
		lo = ldap.initialize('')
		try:
			lo.search_ext_s('', ldap.SCOPE_BASE, self.filter)
		except ldap.FILTER_ERROR:
			raise TypeError('filter=%r != <ldapfilter>' % (self.filter,))
		except ldap.SERVER_DOWN:
			pass
		finally:
			lo.unbind()

	def __str__(self):
		return 'filter="%s"' % (self.filter,)


class Bys(Object):

	def __init__(self, bys):
		self.bys = [By.new(by) for by in bys]

	def __str__(self):
		return '\n\t'.join((str(by) for by in self.bys))


class By(Object):
	"""by <who> [ <access> ] [ <control>"""

	def __init__(self, who, access=None, control=None):
		self.who = Who.new(who)
		self.access = access and Access.new(access)
		self.control = control and Control.new(control)

	def __str__(self):
		by = b'by %s' % (self.who,)
		if self.access:
			by += ' %s' % (self.access,)
		if self.control:
			by += ' %s' % (self.control,)
		return by


class Who(Object):
	"""
		*
		anonymous
		users
		self[.<selfstyle>]

		dn[.<dnstyle>[,<modifier>]]=<DN>
		dnattr=<attrname>

		realanonymous
		realusers
		realself[.<selfstyle>]

		realdn[.<dnstyle>[,<modifier>]]=<DN>
		realdnattr=<attrname>

		group[/<objectclass>[/<attrname>]][.<groupstyle>]=<group>
		peername[.<peernamestyle>]=<peername>
		sockname[.<style>]=<sockname>
		domain[.<domainstyle>[,<modifier>]]=<domain>
		sockurl[.<style>]=<sockurl>
		set[.<setstyle>]=<pattern>

		ssf=<n>
		transport_ssf=<n>
		tls_ssf=<n>
		sasl_ssf=<n>

		dynacl/<name>[/<options>][.<dynstyle>][=<pattern>]

		with

		<style>={exact|regex|expand}
		<selfstyle>={level{<n>}}
		<dnstyle>={{exact|base(object)}|regex|one(level)|sub(tree)|children|level{<n>}}
		<groupstyle>={exact|expand}
		<peernamestyle>={<style>|ip|ipv6|path}
		<domainstyle>={exact|regex|sub(tree)}
		<setstyle>={exact|expand}
		<modifier>={expand}
		<name>=aci
		<pattern>=<attrname>]
	"""

	def __init__(self, who=None, dn=None, dnstyle=None, dnattr=None, modifier=None, group=None, objectclass=None, attrname=None, groupstyle=None):
		# TODO: more validation + implement the rest
		self.who = who
		self.dn = dn
		if self.dn and '%' in self.dn:
			self.dn = self.dn % ucr
		self.dnstyle = dnstyle
		self.dnattr = dnattr
		self.modifier = modifier
		self.group = group
		if self.group and '%' in self.group:
			self.group = self.group % ucr
		self.groupstyle = groupstyle
		self.objectclass = objectclass
		self.attrname = attrname
		self.groupstyle = groupstyle
		if self.who and self.who not in ('*', 'anonymous', 'users', 'self', 'realanonymous', 'realusers', 'realself'):
			raise TypeError()

	def __str__(self):
		if self.who:
			return self.who
		if self.dn:
			who = 'dn'
			if self.dnstyle:
				who += '.%s' % (self.dnstyle,)
			if self.modifier:
				who += ',%s' % (self.modifier,)
			who += '="%s"' % (self.dn,)
			return who
		if self.group:
			who = 'group'
			if self.objectclass:
				who += '/%s' % (self.objectclass,)
			if self.attrname:
				who += '/%s' % (self.attrname,)
			if self.groupstyle:
				who += '.%s' % (self.groupstyle,)
			who += '="%s"' % (self.group,)
			return who

		raise RuntimeError(self.__dict__)


class GroupUniqueMember(Who):

	def __init__(self, dn, groupstyle=None):
		super(GroupUniqueMember, self).__init__(group=dn, objectclass='univentionGroup', attrname='uniqueMember', groupstyle=groupstyle)


class Access(Object):
	"""
		<access> ::= [[real]self]{<level>|<priv>}
		<level> ::= none|disclose|auth|compare|search|read|{write|add|delete}|manage
		<priv> ::= {=|+|-}{0|d|x|c|s|r|{w|a|z}|m}+
	"""
	def __init__(self, access):
		self.access = (access or 'none').lower()
		if self.access not in ('none', 'disclose', 'auth', 'compare', 'search', 'read', 'write', 'add', 'delete', 'manage'):
			if not (self.access.startswith('=') or self.access.startswith('+') or self.access.startswith('-')):
				raise TypeError('access=%s != none|disclose|auth|compare|search|read|{write|add|delete}|manage' % (self.access,))
			if set(self.access[1:]) - set('0dxcsrwazm'):
				raise TypeError('access=%s != {=|+|-}{0|d|x|c|s|r|{w|a|z}|m}+' % (self.access,))

	def __str__(self):
		return self.access


class Control(Object):
	"""control = {stop,continue,break}"""

	def __init__(self, control):
		self.control = (control or 'stop').lower()
		if self.control not in ('stop', 'continue', 'break'):
			raise TypeError('control=%r != {stop,continue,break}' % (self.control,))

	def __str__(self):
		return self.control

STOP = Control('stop')
CONTINUE = Control('continue')
BREAK = Control('break')
