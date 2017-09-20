# Univention UCS@school
#
# Copyright 2007-2017 Univention GmbH
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

__package__ = ''  # workaround for PEP 366
import listener
import univention.debug
import univention.uldap
import os


name = 'ucs-school-user-logonscript'
description = 'Create user-specific netlogon-scripts'
filter = '(|(&(objectClass=posixAccount)(objectClass=organizationalPerson)(!(uid=*$)))(objectClass=posixGroup)(objectClass=univentionShare))'
attributes = []



class Log(object):
	@classmethod
	def debug(cls, msg):
		cls.emit(univention.debug.ALL, msg)

	@staticmethod
	def emit(level, msg):
		univention.debug.debug(univention.debug.LISTENER, level, '{}: {}'.format(name, msg))

	@classmethod
	def error(cls, msg):
		cls.emit(univention.debug.ERROR, msg)

	@classmethod
	def info(cls, msg):
		cls.emit(univention.debug.INFO, msg)

	@classmethod
	def warn(cls, msg):
		cls.emit(univention.debug.WARN, msg)




	else:




def initialize():
	for path in UserLogonScriptListener.template_paths.values():
		if not os.path.exists(path):
			raise Exception('Missing template file {!r}.'.format(path))


def clean():
	Log.warn('Deleting all netlogon scripts in {!r}...'.format(UserLogonScriptListener.get_script_path()))
	listener.setuid(0)
	try:
		for path in UserLogonScriptListener.get_script_path():
			if os.path.exists(path):
				for f in os.listdir(path):
					if f.lower().endswith('.vbs'):
						os.unlink(os.path.join(path, f))
	finally:
		listener.unsetuid()

