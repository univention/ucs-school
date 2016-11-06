#!/usr/bin/python2.7
#
# Univention Management Console
#  module: school accounts Module
#
# Copyright 2007-2016 Univention GmbH
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
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, BooleanSanitizer

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions
import univention.admin.objects as udm_objects

from univention.lib.i18n import Translation

from ucsschool.lib import LDAP_Connection, SchoolBaseModule, Display, USER_WRITE


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
		'school': StringSanitizer(required=True),
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
		'''Reset the password of the user'''  # TODO: instead of error-indicating strings we should raise UMC_Error
		userdn = request.options['userDN']
		pwdChangeNextLogin = request.options['nextLogin']
		newPassword = request.options['newPassword']
		self.finished(request.id, self._reset_password(ldap_user_write, userdn, newPassword, pwdChangeNextLogin))

	def _reset_password(self, lo, userdn, newPassword, pwdChangeNextLogin=True):
		try:
			user_module = udm_modules.get('users/user')
			ur = udm_objects.get(user_module, None, lo, None, userdn)
			ur.open()
			ur['password'] = newPassword
			ur['overridePWHistory'] = '1'
			dn = ur.modify()

			ur.open()
			ur['locked'] = 'none'
			dn = ur.modify()

			ur = udm_objects.get(user_module, None, lo, None, dn)
			ur.open()
			ur['pwdChangeNextLogin'] = '1' if pwdChangeNextLogin else '0'
			dn = ur.modify()
			return True
		except udm_exceptions.permissionDenied as e:
			MODULE.process('dn=%r' % ur.dn)
			MODULE.process('exception=%s' % str(e.__class__))
			return _('permission denied')
		except udm_exceptions.base as e:
			MODULE.process('dn=%r' % ur.dn)
			MODULE.process('exception=%s' % str(e.__class__))
			MODULE.process('exception=%s' % str(e.message))
			return '%s' % (get_exception_msg(e))
