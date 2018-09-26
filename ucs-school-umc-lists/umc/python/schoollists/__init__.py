#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Get csv class lists
#
# Copyright 2018-2019 Univention GmbH
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

import csv
import StringIO
from ldap.dn import explode_dn

from univention.lib.i18n import Translation
from univention.management.console.modules.sanitizers import DNSanitizer, StringSanitizer
from univention.management.console.modules.decorators import sanitize

from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from ucsschool.lib.school_umc_base import SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.models.user import User

_ = Translation('ucs-school-umc-lists').translate


class Instance(SchoolBaseModule):

	@sanitize(
		school=SchoolSanitizer(required=True),
		group=DNSanitizer(required=True, minimum=1),
		separator=StringSanitizer(required=True),
	)
	@LDAP_Connection()
	def csv_list(self, request, ldap_user_read=None, ldap_position=None):
		school = request.options['school']
		group = request.options['group']
		separator = request.options['separator']
		csvfile = StringIO.StringIO()
		fieldnames = [_('Firstname'), _('Lastname'), _('Class'), _('Username')]
		writer = csv.writer(csvfile, delimiter=str(separator))
		writer.writerow(fieldnames)
		for student in self.students(ldap_user_read, school, group):
			class_display_name = student.school_classes[school][0].split('-', 1)[1]
			writer.writerow([
				student.firstname,
				student.lastname,
				class_display_name,
				student.name,
			])
		csvfile.seek(0)
		filename = explode_dn(group)[0].split('=')[1] + '.csv'
		result = {'filename': filename, 'csv': csvfile.read()}
		csvfile.close()
		self.finished(request.id, result)

	def students(self, lo, school, group):
		for user in self._users(lo, school, group=group, user_type='student'):
			yield User.from_udm_obj(user, school, lo)
