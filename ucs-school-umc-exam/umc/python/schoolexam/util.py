#!/usr/bin/python2.7
#
# Univention Management Console
#  utility code for the UMC exam module
#
# Copyright 2013-2016 Univention GmbH
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

# univention
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
ucr.load()

# distribution utils - adjust paths
import univention.management.console.modules.distribution.util as distribution
distribution.DISTRIBUTION_DATA_PATH = ucr.get('ucsschool/exam/cache', '/var/lib/ucs-school-umc-schoolexam')
distribution.POSTFIX_DATADIR_SENDER = ucr.get('ucsschool/exam/datadir/sender', 'Klassenarbeiten')
distribution.POSTFIX_DATADIR_RECIPIENT = ucr.get('ucsschool/exam/datadir/recipient', 'Klassenarbeiten')

class Progress(object):
	def __init__(self, max_steps=100):
		self.reset(max_steps)

	def reset(self, max_steps=100):
		self._max_steps = max_steps
		self._finished = False
		self._steps = 0
		self._component = ''
		self._info = ''
		self._errors = []

	def poll(self):
		return dict(
			finished=self._finished,
			steps=100 * float(self._steps) / self._max_steps,
			component=self._component,
			info=self._info,
			errors=self._errors,
		)

	def finish(self):
		self._finished = True

	def component(self, component):
		self._component = component

	def info(self, info):
		MODULE.process('%s - %s' % (self._component, info))
		self._info = info

	def error(self, err):
		MODULE.warn('%s - %s' % (self._component, err))
		self._errors.append(err)

	def add_steps(self, steps=1):
		self._steps += steps
