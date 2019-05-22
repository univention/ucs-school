# -*- coding: utf-8 -*-
#
# Copyright 2021 Univention GmbH
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

*Attention*: Kelvin version using ``async/await``.
"""

from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.hook import Hook
from udm_rest_client import UDM


class MailForSchoolClass(Hook):
    model = SchoolClass
    priority = {
        "post_create": 10,
        "post_modify": 10,
    }

    async def post_create(self, obj: SchoolClass) -> None:
        """
        Create an email address for the new school class.

        :param SchoolClass obj: the SchoolClass instance, that was just created.
        :return: None
        """
        domain_name = await self.domainname(self.udm)
        ml_name = self.name_for_mailinglist(obj, domain_name)
        self.logger.info("Setting email address %r on %r...", ml_name, obj)
        # The SchoolClass object does not have an email attribute, so we'll have to access the underlying
        # UDM object.
        udm_obj = await obj.get_udm_object(self.udm)
        udm_obj.props.mailAddress = ml_name
        await udm_obj.save()

    async def post_modify(self, obj: SchoolClass) -> None:
        """
        Change the email address of an existing school class, if it didn't have an email or was renamed.

        :param SchoolClass obj: the SchoolClass instance, that was just modified.
        :return: None
        """
        udm_obj = await obj.get_udm_object(self.udm)
        domain_name = await self.domainname(self.udm)
        ml_name = self.name_for_mailinglist(obj, domain_name)
        if udm_obj.props.mailAddress != ml_name:  # this also works if it doesn't have an email address
            self.logger.info(
                "Changing the email address of %r from %r to %r...",
                obj,
                udm_obj.props.mailAddress,
                ml_name,
            )
            udm_obj.props.mailAddress = ml_name
            await udm_obj.save()

    @staticmethod
    def name_for_mailinglist(obj: SchoolClass, domain_name: str) -> str:
        return "{}@{}".format(obj.name, domain_name).lower()

    async def domainname(self, udm: UDM) -> str:
        async for mail_domain_udm_obj in udm.get("mail/domain").search():
            return mail_domain_udm_obj.props.name
        else:
            return self.ucr["domainname"]
