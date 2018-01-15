#!/usr/bin/python2.7
#
# Univention Management Console
#  module: school accounts Module
#
# Copyright 2007-2018 Univention GmbH
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

from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, BooleanSanitizer

import univention.admin.uexceptions as udm_exceptions

from univention.lib.i18n import Translation

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule, Display, USER_WRITE, SchoolSanitizer
from ucsschool.lib.models import User


_ = Translation('ucs-school-umc-schoolusers').translate


def get_exception_msg(exc):  # TODO: str(exc) would be nicer, Bug #27940, 30089, 30088
	msg = getattr(exc, 'message', '')
	for arg in exc.args:
		if isinstance(arg, unicode):
			arg = arg.encode('utf-8')
		if str(arg) not in msg:
			msg = '%s %s' % (msg, arg)
	return msg


class Instance(SchoolBaseModule):

	@sanitize(**{
		'school': SchoolSanitizer(required=True),
		'class': StringSanitizer(required=True),  # allow_none=True
		'pattern': StringSanitizer(required=True),
	})
	@LDAP_Connection()
	def query(self, request, ldap_user_read=None, ldap_position=None):
		"""Searches for students"""

		klass = request.options.get('class')
		if klass in (None, 'None'):
			klass = None
		result = [{
			'id': usr.dn,
			'name': Display.user(usr),
			'passwordexpiry': usr.get('passwordexpiry', '')
		} for usr in self._users(ldap_user_read, request.options['school'], group=klass, user_type=request.flavor, pattern=request.options.get('pattern', ''))]
		self.finished(request.id, result)

	@sanitize(
		userDN=StringSanitizer(required=True),
		newPassword=StringSanitizer(required=True, minimum=1),
		nextLogin=BooleanSanitizer(default=True),
	)
	@LDAP_Connection(USER_WRITE)
	def password_reset(self, request, ldap_user_write=None):
		'''Reset the password of the user'''
		userdn = request.options['userDN']
		pwdChangeNextLogin = request.options['nextLogin']
		newPassword = request.options['newPassword']

		try:
			user = User.from_dn(userdn, None, ldap_user_write).get_udm_object(ldap_user_write)
			user['password'] = newPassword
			user['overridePWHistory'] = '1'
			user['locked'] = 'none'
			user['pwdChangeNextLogin'] = '1' if pwdChangeNextLogin else '0'
			user.modify()
			self.finished(request.id, True)
		except udm_exceptions.permissionDenied as exc:
			MODULE.process('dn=%r' % (userdn,))
			MODULE.process('exception=%s' % (type(exc),))
			raise UMC_Error(_('permission denied'))
		except udm_exceptions.base as exc:
			MODULE.process('dn=%r' % (userdn,))
			MODULE.process('exception=%s' % (type(exc),))
			MODULE.process('exception=%s' % (exc.message,))
			raise UMC_Error('%s' % (get_exception_msg(exc)))
