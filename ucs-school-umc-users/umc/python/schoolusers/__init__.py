#!/usr/bin/python2.7
#
# Univention Management Console
#  module: school accounts Module
#
# Copyright 2007-2019 Univention GmbH
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

from time import time, strptime
from calendar import timegm
from math import ceil

from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, BooleanSanitizer

from univention.admin.handlers.users.user import unmapPasswordExpiry
import univention.admin.uexceptions as udm_exceptions

from univention.lib.i18n import Translation

from ucsschool.lib.school_umc_base import LDAP_Connection, SchoolBaseModule, Display, USER_WRITE, SchoolSanitizer
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
		result = [
			{
				'id': dn,
				'name': Display.user_ldap(attr),
				'passwordexpiry': self.passwordexpiry_to_days(unmapPasswordExpiry(attr))
			}
			for dn, attr in self._users_ldap(
				ldap_user_read,
				request.options['school'],
				group=klass,
				user_type=request.flavor,
				pattern=request.options.get('pattern', ''),
				attr=['givenName', 'sn', 'shadowLastChange', 'shadowMax', 'uid'])
		]
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
			user['locked'] = '0'   # Bug #46175: reset locked state, do not set disabled=0 since this would enable the whole user account
			# workaround bug #46067 (start)
			user.modify()
			user = User.from_dn(userdn, None, ldap_user_write).get_udm_object(ldap_user_write)
			# workaround bug #46067 (end)
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

	def passwordexpiry_to_days(self, timestr):
		"""
		Calculates the number of days from now to the password expiration date.

		The result is always rounded up to the full day.
		The time function used here are all based on Epoch(UTC). Since we are not interested in a specific
		date and only in a time difference the actual timezone is neglectable.

		:param timestr: The string representation of the expiration date, e.g. 2018-05-30 or None
		:type timestr: str
		:return: -1 if no expiration day is set, 0 if already expired, >0 otherwise
		:rtype: int
		"""

		if not timestr:
			return -1
		current_timestamp = time()
		expires_timestamp = timegm(strptime(timestr, "%Y-%m-%d"))
		time_difference = expires_timestamp - current_timestamp
		if time_difference <= 0:
			return 0
		return int(ceil(time_difference / 86400))   # Bug #42212: User.passwordexpiry max resolution is day.
		# So we always round up towards the day the password will be expired
