#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention UCS@School
"""
Modify ucsschool objects in LDAP to use new objectClasses
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


import ldap
import sys

from univention.admin import uldap, uexceptions
from ucsschool.lib.schoolldap import SchoolSearchBase

ldap_errors = (ldap.LDAPError, uexceptions.base,)


class MigrationFailed(Exception):

	def __init__(self, errors):
		super(Exception, self).__init__(errors)
		self.errors = errors

	def _format(self):
		yield '%d error(s) occurred' % (len(self.errors),)
		for (etype, exc, etraceback), dn in self.errors:
			yield '%s: %s: %s' % (etype.__name__, dn, exc)

	def __str__(self):
		return '\n'.join(self._format())


def migrate(lo):
	errors = []
	try:
		schools = lo.search('objectClass=ucsschoolOrganizationalUnit', attr=['ou'])
	except ldap_errors:
		errors.append((sys.exc_info(), None))
		raise MigrationFailed(errors)

	for dn, attrs in schools:
		school = attrs['ou'][0]
		yield 'Migrating users of school %r' % (school,)
		base = SchoolSearchBase([school], dn=dn)
		mapping = [
			(base.students, 'ucsschoolStudent'),
			(base.teachers, 'ucsschoolTeacher'),
			(base.teachersAndStaff, ('ucsschoolTeacher', 'ucsschoolStaff')),
			(base.staff, 'ucsschoolStaff'),
			(base.admins, 'ucsschoolAdministrator'),
		]
		for container, object_classes in mapping:
			yield 'Migrating users underneath of %r' % (container,)
			if isinstance(object_classes, basestring):
				object_classes = [object_classes]
			try:
				objects = lo.search(base=container, scope='one')
			except uexceptions.noObject:
				yield 'Container %r does not exists' % (container,)
				continue
			except ldap_errors:
				errors.append((sys.exc_info(), container))
				continue
			for object_dn, object_attrs in objects:
				old_schools = object_attrs.get('ucsschoolSchool', [])
				old_object_classes = object_attrs.get('objectClass', [])
				new_schools = set(old_schools) | set([school])
				new_object_classes = set(old_object_classes) | set(object_classes)
				yield 'Adding %r into school %r' % (object_dn, ', '.join(new_schools))
				try:
					lo.modify(object_dn, [
						('ucsschoolSchool', list(old_schools), list(new_schools)),
						('objectClass', list(old_object_classes), list(new_object_classes))
					])
				except ldap_errors:
					errors.append((sys.exc_info(), object_dn))
	if errors:
		raise MigrationFailed(errors)


if __name__ == '__main__':
	try:
		lo, po = uldap.getAdminConnection()
	except IOError:
		raise SystemExit('This script must be executed on a DC Master.')
	try:
		for message in migrate(lo):
			print(message)
	except MigrationFailed as exc:
		raise SystemExit(str(exc))
