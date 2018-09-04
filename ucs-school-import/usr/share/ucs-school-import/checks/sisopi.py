# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2018 Univention GmbH
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

"""
Configuration checks for SingleSourcePartialImport scenario.
"""

from ucsschool.lib.models import School
from ucsschool.importer.exceptions import InitialisationError
from ucsschool.importer.utils.configuration_checks import ConfigurationChecks


class SingleSourcePartialImportConfigurationChecks(ConfigurationChecks):
	def test_00_required_config_keys(self):
		for attr in ('limbo_ou', 'school', 'user_role'):
			if not self.config.get(attr):
				raise InitialisationError('No {!r} was specified in the configuration.'.format(attr))

	def test_limbo_ou(self):
		if not School(name=self.config['limbo_ou']).exists(self.lo):
			raise InitialisationError(
				"School {!r} in configuration for 'limbo_ou' does not exist.".format(self.config.get('limbo_ou'))
			)

	def test_deactivation_grace(self):
		deactivation_grace = max(0, int(self.config.get('deletion_grace_period', {}).get('deactivation', 0)))
		if deactivation_grace != 0:
			raise InitialisationError(
				'Value for deletion_grace_period:deactivation is {!r}, must be 0.'.format(deactivation_grace))

	def test_deletion_grace(self):
		deletion_grace = max(0, int(self.config.get('deletion_grace_period', {}).get('deletion', 0)))
		if deletion_grace == 0:
			self.logger.warn(
				'Very dangerous value for deletion_grace_period:deletion = %d! Expected something greater than 0.',
				deletion_grace
			)

	def test_school_not_limbo(self):
		if self.config['school'] == self.config['limbo_ou']:
				raise InitialisationError('Importing into limbo ({!r}) OU is forbidden.'.format(self.config['limbo_ou']))
