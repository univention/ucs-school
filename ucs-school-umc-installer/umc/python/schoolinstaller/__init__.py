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
import apt

import univention.admin.modules as udm_modules
import univention.admin.uldap as udm_uldap

from univention.lib import escape_value
from univention.management.console.modules import Base
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.modules.decorators import simple_response, sanitize
from univention.management.console.modules.sanitizers import StringSanitizer, Sanitizer
import univention.uldap

from univention.lib.i18n import Translation

_ = Translation( 'ucs-school-umc-installer' ).translate
ucr.load()

fqdn_pattern = '^[a-z]([a-z0-9-]*[a-z0-9])*\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*$'
hostname_pattern = '^[a-z]([a-z0-9-]*[a-z0-9])*(\.([a-z0-9]([a-z0-9-]*[a-z0-9])*[.])*[a-z0-9]([a-z0-9-]*[a-z0-9])*)?$'

class HostSanitizer(StringSanitizer):
	def _sanitize(self, value, name, further_args):
		value = super(HostSanitizer, self)._sanitize(value, name, further_args)
		try:
			return socket.getfqdn(master)
		except socket.gaierror:
			# invalid FQDN
			self.raise_validation_error(_('The entered FQDN is not a valid value'))

def get_ldap_connection(host, binddn, bindpw):
	return univention.uldap.access(host, port=int(ucr.get('ldap/master/port', '7389')), binddn=binddn, bindpw=bindpw)

class Instance(Base):
	@property
	def sambaVersion(self):
		'''Returns 3 or 4 for Samba4 or Samba3 installation, respectively, and returns None otherwise.'''
		cache = apt.Cache()
		try:
			if cache['univention-samba4'].is_installed:
				return 4
			if cache['univention-samba'].is_installed:
				return 3
		except KeyError as e:
			# package not known
			pass

		return None

	@simple_response
	def query(self, **kwargs):
		"""Returns a dictionary of initial values for the form."""
		ucr.load()

		return {
			'server/role': ucr.get('server/role'),
			'joined': os.path.exists('/var/univention-join/joined'),
			'samba': self.sambaVersion,
		}

	@sanitize(username=StringSanitizer(required=True, use_asterisks=False), password=StringSanitizer(required=True), master=HostSanitizer(required=True, regex_pattern=hostname_pattern), allow_other_keys=False)
	@simple_response
	def credentials(self, username, password, master):
		"""Returns the usernames DN and masters FQDN"""
		ssh = paramiko.SSHClient()
		try:
			ssh.connect(master, username=username, password=password)
		except:
			raise UMC_CommandError('invalid credentails')

		# try to get the DN of the user account
		username = ldap.filter.escape_filter_chars(username)
		stdin, dn, stderr = ssh.exec_command("/usr/sbin/udm users/user list --filter uid='%s' --logfile /dev/null | sed -ne 's|^DN: ||p'" % escape_value(username))

		if not dn.strip():
			dn = None

		return {'dn': dn, 'master': master}

### currently not used
#	@sanitize(username=StringSanitizer(required=True, use_asterisks=False), password=StringSanitizer(required=True), master=HostSanitizer(required=True, regex_pattern=fqdn_pattern), allow_other_keys=False)
#	@simple_response
#	def samba(self, username, password, master):
#		"""Returns 'samba3' if the Samba3 is installed on the master system, else 'samab4'"""
#		try:
#			lo = get_ldap_connection(master, username, password)
#		except:
#			pass # TODO
#
#		# search for samba4 service object
#		if lo.search(filter='(&(objectClass=univentionServiceObject)(name=Samba 3))'):
#			return 'samba3'
#		elif lo.search(filter='(&(objectClass=univentionServiceObject)(name=Samba 4))'):
#			return 'samba4'
#		return 'samba4' # fallback, no samba installed

	@simple_response
	def progress(self):
		return {'finished': True}

	def install(self, request):
		self.finished( request.id, True)
