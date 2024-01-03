# -*- coding: utf-8 -*-
#
# Copyright 2021-2024 Univention GmbH
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
Example hook class that creates/modifies an email address for a school class.

Copy to /usr/share/ucs-school-import/pyhooks to activate it.
"""

from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.hook import Hook


class MailForSchoolClass(Hook):
    model = SchoolClass
    priority = {
        "post_create": 10,
        "post_modify": 10,
    }

    def post_create(self, obj):  # type: (SchoolClass) -> None
        """
        Create an email address for the new school class.

        :param SchoolClass obj: the SchoolClass instance, that was just created.
        :return: None
        """
        ml_name = self.name_for_mailinglist(obj)
        self.logger.info("Setting email address %r on %r...", ml_name, obj)
        # The SchoolClass object does not have an email attribute, so we'll have to access the underlying
        # UDM object.
        udm_obj = obj.get_udm_object(self.lo)
        udm_obj["mailAddress"] = ml_name
        udm_obj.modify()

    def post_modify(self, obj):  # type: (SchoolClass) -> None
        """
        Change the email address of an existing school class, if it didn't have an email or was renamed.

        :param SchoolClass obj: the SchoolClass instance, that was just modified.
        :return: None
        """
        udm_obj = obj.get_udm_object(self.lo)
        ml_name = self.name_for_mailinglist(obj)
        if udm_obj["mailAddress"] != ml_name:  # this also works if it doesn't have an email address
            self.logger.info(
                "Changing the email address of %r from %r to %r...",
                obj,
                udm_obj["mailAddress"],
                ml_name,
            )
            udm_obj["mailAddress"] = ml_name
            udm_obj.modify()

    def name_for_mailinglist(self, obj):  # type: (SchoolClass) -> str
        return "{}@{}".format(obj.name, self.domainname).lower()

    @property
    def domainname(self):  # type: () -> str
        try:
            return self.ucr["mail/hosteddomains"].split()[0]
        except (AttributeError, IndexError):
            return self.ucr["domainname"]
