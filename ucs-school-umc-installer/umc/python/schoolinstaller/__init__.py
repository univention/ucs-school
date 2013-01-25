#!/usr/bin/python2.6
#
# Univention Management Console
#  This installation wizard guides the installation of UCS@school in the domain
#
# Copyright 2012 Univention GmbH
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

import os.path
import subprocess
import socket
import paramiko
import ldap.filter

from univention.lib import escape_value
from univention.management.console.modules import Base
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, Sanitizer

from univention.lib.i18n import Translation

_ = Translation( 'ucs-school-umc-installer' ).translate

class HostSanitizer(StringSanitizer):
	def _sanitize(self, value, name, further_args):
		value = super(HostSanitizer, self)._sanitize(value, name, further_args)
		try:
			master = socket.gethostbyname(master)
		except socket.gaierror:
			# invalid FQDN
			self.raise_validation_error(_('The entered FQDN is not a valid value'))
		else:
			return master

class Instance(Base):

	@simple_response
	def query(self, **kwargs):
		"""Returns a dictionary of initial values for the form."""
		ucr.load()

		return {
			'server/role': ucr.get('server/role'),
			'joined': os.path.exists('/var/univention-join/joined') }

	
	@sanitize(username=StringSanitizer(required=True, use_asterisks=False), password=StringSanitizer(required=True), master=HostSanitizer(required=True), allow_other_keys=False)
	@simple_response
	def credentials(self, username, password, master):
		ssh = paramiko.SSHClient()
		try:
			ssh.connect(master, username=username, password=password)
		except:
			pass

		# try to get the DN of the user account
		username = ldap.filter.escape_filter_chars(username)
		stdin, dn, stderr = ssh.exec_command("/usr/sbin/udm users/user list --filter uid='%s' --logfile /dev/null | sed -ne 's|^DN: ||p'" % escape_value(username))

		if not dn.strip():
			dn = None

	def install(self, request):
		self.finished( request.id, True)
