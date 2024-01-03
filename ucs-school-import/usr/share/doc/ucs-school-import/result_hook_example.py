#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2024 Univention GmbH
#
# https://www.univention.de/
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

import io
import smtplib

from ucsschool.importer.utils.result_pyhook import ResultPyHook
from univention.config_registry import ConfigRegistry

# Set this to True, if emails should also be sent when a dry-run is executed:
SEND_AFTER_DRY_RUN = False

ucr = ConfigRegistry()
ucr.load()

from_address = "ucs-school-import@{}.{}".format(ucr["hostname"], ucr["domainname"])
to_addresses = ["root@{}.{}".format(ucr["hostname"], ucr["domainname"])]
smtp_server = "localhost"


class MailResultHook(ResultPyHook):
    priority = {
        "user_result": 1,
    }
    supports_dry_run = True

    def user_result(self, user_import_data):
        if self.dry_run and not SEND_AFTER_DRY_RUN:
            self.logger.info("Not sending result email in dry-run.")
            return

        msg = io.StringIO()
        msg.write("From: {}\n".format(from_address))
        msg.write("To: {}\r\n\r\n".format(", ".join(to_addresses)))

        msg.write("There have been {} errors.\n".format(len(user_import_data.errors)))
        for error in user_import_data.errors:
            msg.write("    {!s}".format(error))

        added = sum(len(users) for users in user_import_data.added_users.values())
        msg.write("Users created ({}):\n".format(added))
        for role, users in user_import_data.added_users.items():
            if not users:
                continue
            msg.write("    {}: {}\n".format(role, ", ".join([u["name"] for u in users[:4]])))
            for user_chunk in [users[i : i + 4] for i in range(4, len(users), 4)]:
                msg.write(
                    "      {}{}\n".format(" " * len(role), ", ".join([u["name"] for u in user_chunk]))
                )

        modified = sum(len(users) for users in user_import_data.modified_users.values())
        msg.write("Users modified ({}):\n".format(modified))
        for role, users in user_import_data.modified_users.items():
            if not users:
                continue
            msg.write("    {}: {}\n".format(role, ", ".join([u["name"] for u in users[:4]])))
            for user_chunk in [users[i : i + 4] for i in range(4, len(users), 4)]:
                msg.write(
                    "      {}{}\n".format(" " * len(role), ", ".join([u["name"] for u in user_chunk]))
                )

        deleted = sum(len(users) for users in user_import_data.deleted_users.values())
        msg.write("Users deleted ({}):\n".format(deleted))
        for role, users in user_import_data.deleted_users.items():
            if not users:
                continue
            msg.write("    {}: {}\n".format(role, ", ".join([u["name"] for u in users[:4]])))
            for user_chunk in [users[i : i + 4] for i in range(4, len(users), 4)]:
                msg.write(
                    "      {}{}\n".format(" " * len(role), ", ".join([u["name"] for u in user_chunk]))
                )

        server = smtplib.SMTP(smtp_server)
        server.set_debuglevel(1)
        server.sendmail(from_address, to_addresses, msg.getvalue().encode("UTF-8"))
        msg.close()
        server.quit()
