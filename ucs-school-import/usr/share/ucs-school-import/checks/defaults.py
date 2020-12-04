# -*- coding: utf-8 -*-
#
# Univention UCS@school
# Copyright 2018-2021 Univention GmbH
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


import re
import string

from six import iteritems, string_types

from ucsschool.importer.exceptions import InitialisationError
from ucsschool.importer.factory import setup_factory
from ucsschool.importer.utils.configuration_checks import ConfigurationChecks
from ucsschool.lib.models.utils import ucr, ucr_username_max_length


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
                "The 'user_deletion' configuration key is deprecated. Please set "
                "'deletion_grace_period'."
            )

    def test_school_class_invalid_char_replacement_is_valid_char(self):
        valid_chars = string.ascii_letters + string.digits + " -."
        try:
            assert len(self.config.get("school_classes_invalid_character_replacement", "")) in (0, 1)
            assert self.config["school_classes_invalid_character_replacement"] in valid_chars
        except (AssertionError, IndexError):
            raise InitialisationError(
                "school_classes_invalid_character_replacement must be one of {!r}".format(valid_chars)
            )

    def test_username_max_length(self):
        for role in ("default", "staff", "student", "teacher", "teacher_and_staff"):
            try:
                username_max_length = self.config["username"]["max_length"][role]
                if username_max_length < 4:
                    raise InitialisationError(
                        "Configuration value of username:max_length:{} must be higher than 3.".format(
                            role
                        )
                    )
                if username_max_length > ucr_username_max_length:
                    raise InitialisationError(
                        "Configuration value of username:max_length:{} is {!r}, but must not be higher "
                        "than UCR variable ucsschool/username/max_length ({}).".format(
                            role, username_max_length, int(ucr_username_max_length)
                        )
                    )
            except KeyError:
                username_max_length = ucr_username_max_length

            if username_max_length > 20 and role != "default":
                self.logger.warning(
                    "Configuration value of username:max_length:%s (%d) is higher than 20. "
                    "Logging into Windows < 8.1 will not be possible.",
                    role,
                    username_max_length,
                )

    def test_exam_user_prefix_length(self):
        exam_user_prefix = ucr.get("ucsschool/ldap/default/userprefix/exam", "exam-")
        exam_user_prefix_length = len(exam_user_prefix)
        student_username_max_length = self.config["username"]["max_length"].get(
            "student", ucr_username_max_length
        )
        if student_username_max_length > 20 - exam_user_prefix_length:
            self.logger.warning(
                "Configuration value of username:max_length:student is higher than %d (20 - length(%r))."
                " Exam users will not be able to log into Windows < 8.1.",
                20 - exam_user_prefix_length,
                exam_user_prefix,
            )

    def test_user_role_role_mapping_combination(self):
        if self.config["user_role"] and "__role" in self.config["csv"]["mapping"].values():
            raise InitialisationError(
                "Using 'user_role' setting and '__role' mapping at the same time is not allowed."
            )

    def test_scheme_valid_format(self):
        """
        Check validity of "scheme" entries.

        Known entries:
        * scheme:record_uid -> str
        * scheme:username -> dict: {
        *   default -> str
        *   staff, student, teacher, teacher_and_staff -> str
        *   allow_rename -> bool # depricated!
        * }
        * scheme:<udm_attribute_name> -> str
        """
        factory = setup_factory(self.config["factory"])
        username_handler = factory.make_username_handler(15)
        # If a '[' or a ']' appears in a "scheme" field, it should be in one of these
        # contexts:
        counters = username_handler.counter_variable_to_function.keys()
        counters_str = [r"\[{}\]".format(counter[1:-1]) for counter in counters]
        scheme_allowed_occurences = [r"\[\d\]", r"\[\d*:\d*\]"] + counters_str
        scheme_allowed_occurences_regex = re.compile("|".join(scheme_allowed_occurences))

        def check_scheme(scheme):
            """
            Check if '<' and '>' symbols occure equal times and if counter names in
            '[', ']' are correct.
            """
            if scheme.count("<") != scheme.count(">"):
                raise InitialisationError("The numbers of '<' and '>' symbols are not identical.")
            # Check if on each '<' symbol a '>' symbol follows
            start = 0
            while True:
                opening = scheme.find("<", start)
                if opening == -1:
                    break
                closing = scheme.find(">", start)
                if closing < opening:
                    raise InitialisationError("'<' and '>' are in wrong order.")
                start = closing + 1
            # remove allowed usages of '[..]' and check if any remain
            rest = scheme_allowed_occurences_regex.sub("", scheme)
            if any(symbol in rest for symbol in ["[", "]"]):
                raise InitialisationError(
                    "Erroneous use of square brackets in schema {!r}".format(scheme)
                )

        for name, value in iteritems(self.config["scheme"]):
            if name == "username":
                if not isinstance(value, dict):
                    raise InitialisationError("Value of 'scheme:username' must be a dict/object.")
                for k, v in iteritems(value):
                    if k == "allow_rename":
                        raise InitialisationError(
                            "Deprecated configuration key 'scheme:username:allow_rename'."
                        )
                    elif k in ("default", "staff", "student", "teacher", "teacher_and_staff"):
                        if not isinstance(v, string_types):
                            raise InitialisationError(
                                "Value of 'scheme:username:{}' must be a string.".format(k)
                            )
                        check_scheme(v)
                    else:
                        raise InitialisationError(
                            "Unknown configuration key 'scheme:username:{}'.".format(k)
                        )
            else:
                if not isinstance(value, string_types):
                    raise InitialisationError("Value of 'scheme:{}' must be a string.".format(name))
                check_scheme(value)
