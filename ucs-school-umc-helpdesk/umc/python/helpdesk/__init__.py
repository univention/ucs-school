#!/usr/bin/python3
#
# Univention Management Console
#  module: Helpdesk Module
#
# Copyright 2007-2024 Univention GmbH
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

import codecs
import smtplib
import traceback

import ldap

from ucsschool.lib.models.school import School
from ucsschool.lib.school_umc_base import SchoolBaseModule, SchoolSanitizer
from ucsschool.lib.school_umc_ldap_connection import LDAP_Connection
from univention.admin.handlers.users.user import object as User
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.log import MODULE
from univention.management.console.modules import UMC_Error
from univention.management.console.modules.decorators import sanitize, threaded
from univention.management.console.modules.sanitizers import StringSanitizer

_ = Translation("ucs-school-umc-helpdesk").translate


def sanitize_header(header):
    for chr_ in "\x00\r\n":
        header = header.replace(chr_, u"?")
    return header


class Instance(SchoolBaseModule):
    @sanitize(
        school=SchoolSanitizer(required=True),
        message=StringSanitizer(required=True),
        category=StringSanitizer(required=True),
    )
    @threaded
    @LDAP_Connection()
    def send(self, request, ldap_user_read=None, ldap_position=None):
        ucr.load()
        if not ucr.get("ucsschool/helpdesk/recipient"):
            raise UMC_Error(
                _(
                    "The message could not be send to the helpdesk team: The email address for the "
                    "helpdesk team is not configured. It must be configured by an administrator via "
                    'the UCR variable "ucsschool/helpdesk/recipient".'
                ),
                status=500,
            )

        recipients = ucr["ucsschool/helpdesk/recipient"].split(" ")
        school = School.from_dn(
            School(name=request.options["school"]).dn, None, ldap_user_read
        ).display_name
        category = request.options["category"]
        message = request.options["message"]

        subject = u"%s (%s: %s)" % (category, _("School"), school)

        try:
            user = User(None, ldap_user_read, ldap_position, request.user_dn)
            user.open()
        except ldap.LDAPError:
            MODULE.error("Error receiving user information: %s" % (traceback.format_exception(),))
            user = {
                "displayName": request.username,
                "mailPrimaryAddress": "",
                "mailAlternativeAddress": [],
                "e-mail": [],
                "phone": [],
            }
        mails = {user["mailPrimaryAddress"]} | set(user["mailAlternativeAddress"]) | set(user["e-mail"])

        sender = user["mailPrimaryAddress"]
        if not sender:
            if ucr.get("hostname") and ucr.get("domainname"):
                sender = "ucsschool-helpdesk@%s.%s" % (ucr["hostname"], ucr["domainname"])
            else:
                sender = "ucsschool-helpdesk@localhost"

        data = [
            (_("Sender"), u"%s (%s)" % (user["displayName"], request.username)),
            (_("School"), school),
            (_("Mail address"), u", ".join(mails)),
            (_("Phone number"), u", ".join(user["phone"])),
            (_("Category"), category),
            (_("Message"), u"\r\n%s" % (message,)),
        ]
        message = u"\r\n".join(u"%s: %s" % (key, value) for key, value in data)

        MODULE.info(
            "sending message: %s" % ("\n".join(repr(x.strip()) for x in message.splitlines())),
        )

        msg = u"From: %s\r\n" % (sanitize_header(sender),)
        msg += u"To: %s\r\n" % (sanitize_header(", ".join(recipients)),)
        msg += u"Subject: =?UTF-8?Q?%s?=\r\n" % (
            codecs.encode(sanitize_header(subject).encode("utf-8"), "quopri")
        ).decode("ASCII")
        msg += u'Content-Type: text/plain; charset="UTF-8"\r\n'
        msg += u"\r\n"
        msg += message
        msg += u"\r\n"
        msg = msg.encode("UTF-8")

        server = smtplib.SMTP("localhost")
        server.set_debuglevel(0)
        server.sendmail(sender, recipients, msg)
        server.quit()
        return True

    @LDAP_Connection()
    def categories(self, request, ldap_user_read=None, ldap_position=None):
        categories = []
        res = ldap_user_read.searchDn(
            filter="objectClass=univentionUMCHelpdeskClass", base=ldap_position.getBase()
        )
        # use only first object found
        if res and res[0]:
            categories = ldap_user_read.getAttr(res[0], "univentionUMCHelpdeskCategory")

        self.finished(
            request.id, [{"id": x.decode("utf-8"), "label": x.decode("utf-8")} for x in categories]
        )
