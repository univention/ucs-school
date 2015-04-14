#!/usr/bin/python2.7
#
# Univention Management Console
#  module: Helpdesk Module
#
# Copyright 2007-2015 Univention GmbH
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
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response

from univention.lib.i18n import Translation

from ucsschool.lib import LDAP_Connection, SchoolBaseModule
from ucsschool.lib.models import School

import notifier
import notifier.popen

import smtplib

_ = Translation('ucs-school-umc-helpdesk').translate


class Instance(SchoolBaseModule):

	@simple_response
	@LDAP_Connection()
	def configuration(self, ldap_user_read=None, ldap_position=None, search_base=None):
		MODULE.process('return configuration')
		username = _('unknown')
		if self._username:
			username = self._username

		MODULE.info('username=%s  school=%s' % (self._username, search_base.school))

		school = School.from_dn(School(search_base.school).dn, None, ldap_user_read)
		return {
			'username': username,
			'school': school.display_name,
			'recipient': ucr.get('ucsschool/helpdesk/recipient')
		}

	def send(self, request):
		def _send_thread(sender, recipients, username, school, category, message):
			MODULE.info('sending mail: thread running')

			msg = u'From: ' + sender + u'\r\n'
			msg += u'To: ' + (', '.join(recipients)) + u'\r\n'
			msg += u'Subject: %s (%s: %s)\r\n' % (category, _('School'), school)
			msg += u'\r\n'
			msg += u'%s: %s\r\n' % (_('Sender'), username)
			msg += u'%s: %s\r\n' % (_('School'), school)
			msg += u'%s: %s\r\n' % (_('Category'), category)
			msg += u'%s:\r\n' % _('Message')
			msg += message + u'\r\n'
			msg += u'\r\n'

			msg = msg.encode('latin1')

			server = smtplib.SMTP('localhost')
			server.set_debuglevel(0)
			server.sendmail(sender, recipients, msg)
			server.quit()

		def _send_return(thread, result, request):
			import traceback

			if not isinstance(result, BaseException):
				MODULE.info('sending mail: completed successfully')
				self.finished(request.id, True)
			else:
				msg = '%s\n%s: %s\n' % (''.join(traceback.format_tb(thread.exc_info[2])), thread.exc_info[0].__name__, str(thread.exc_info[1]))
				MODULE.process('sending mail:An internal error occurred: %s' % msg)
				self.finished(request.id, False, msg, False)

		keys = ['username', 'school', 'category', 'message']
		self.required_options(request, *keys)
		for key in keys:
			if request.options[key]:
				MODULE.info('send ' + key + '=' + request.options[key].replace('%', '_'))

		if ucr.get('ucsschool/helpdesk/recipient'):
			if ucr.get('hostname') and ucr.get('domainname'):
				sender = 'ucsschool-helpdesk@%s.%s' % (ucr['hostname'], ucr['domainname'])
			else:
				sender = 'ucsschool-helpdesk@localhost'

			func = notifier.Callback(_send_thread, sender, ucr['ucsschool/helpdesk/recipient'].split(' '), request.options['username'], request.options['school'], request.options['category'], request.options['message'])
			MODULE.info('sending mail: starting thread')
			cb = notifier.Callback(_send_return, request)
			thread = notifier.threads.Simple('HelpdeskMessage', func, cb)
			thread.run()
		else:
			MODULE.error('HELPDESK: cannot send mail - config-registry variable "ucsschool/helpdesk/recipient" is not set')
			self.finished(request.id, False, _('The email address for the helpdesk team is not configured.'))

	@LDAP_Connection()
	def categories(self, request, ldap_user_read=None, ldap_position=None, search_base=None):
		categories = []
		res = ldap_user_read.searchDn(filter='objectClass=univentionUMCHelpdeskClass', base=ldap_position.getBase())
		# use only first object found
		if res and res[0]:
			categories = ldap_user_read.getAttr(res[0], 'univentionUMCHelpdeskCategory')

		self.finished(request.id, map(lambda x: {'id': x, 'label': x}, categories))
