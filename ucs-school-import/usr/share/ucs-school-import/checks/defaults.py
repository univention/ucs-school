# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2018-2020 Univention GmbH
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
Default configuration checks.

See docstring of module ucsschool.importer.utils.configuration_checks on how to
add your own checks.
"""

from ucsschool.lib.models.utils import ucr, ucr_username_max_length
from ucsschool.importer.exceptions import InitialisationError
from ucsschool.importer.utils.configuration_checks import ConfigurationChecks


class DefaultConfigurationChecks(ConfigurationChecks):
	"""
	Default configuration checks. Should always be executed.
	Run in alphanumerical order.
	"""
	def test_minimal_mandatory_attributes(self):
		try:
			mandatory_attributes = self.config["mandatory_attributes"]
		except KeyError:
			raise InitialisationError("Configuration key 'mandatory_attributes' must exist.")
		if not isinstance(mandatory_attributes, list):
			raise InitialisationError("Configuration value of 'mandatory_attributes' must be a list.")

	def test_source_uid(self):
		if not self.config.get("source_uid"):
			raise InitialisationError("No source_uid was specified.")

	def test_input_type(self):
		if not self.config["input"].get("type"):
			raise InitialisationError("No input:type was specified.")

	def test_deprecated_user_deletion(self):
		if "user_deletion" in self.config:
			raise InitialisationError(
				"The 'user_deletion' configuration key is deprecated. Please set 'deletion_grace_period'.")

	def test_username_max_length(self):
		for role in ('default', 'staff', 'student', 'teacher', 'teacher_and_staff'):
			try:
				username_max_length = self.config["username"]["max_length"][role]
				if username_max_length < 4:
					raise InitialisationError(
						"Configuration value of username:max_length:{} must be higher than 3.".format(role)
					)
				if username_max_length > ucr_username_max_length:
					raise InitialisationError(
						"Configuration value of username:max_length:{} is {!r}, but must not be higher than UCR variable "
						"ucsschool/username/max_length ({}).".format(role, username_max_length, int(ucr_username_max_length))
					)
			except KeyError:
				username_max_length = ucr_username_max_length

			if username_max_length > 20 and role != 'default':
				self.logger.warning(
					"Configuration value of username:max_length:%s (%d) is higher than 20. "
					"Logging into Windows < 8.1 will not be possible.",
					role, username_max_length)

	def test_exam_user_prefix_length(self):
		exam_user_prefix = ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-")
		exam_user_prefix_length = len(exam_user_prefix)
		student_username_max_length = self.config["username"]["max_length"].get("student", ucr_username_max_length)
		if student_username_max_length > 20 - exam_user_prefix_length:
			self.logger.warning(
				"Configuration value of username:max_length:student is higher than %d (20 - length(%r)). "
				"Exam users will not be able to log into Windows < 8.1.",
				20 - exam_user_prefix_length, exam_user_prefix)

	def test_user_role_role_mapping_combination(self):
		if self.config['user_role'] and '__role' in self.config['csv']['mapping'].values():
			raise InitialisationError("Using 'user_role' setting and '__role' mapping at the same time is not allowed.")
