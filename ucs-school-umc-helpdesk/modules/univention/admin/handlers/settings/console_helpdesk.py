#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# UCS@School Helpdesk
#  univention admin helpdesk module
#
# Copyright 2006-2021 Univention GmbH
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

import univention.admin.handlers
import univention.admin.localization
import univention.admin.syntax
from univention.admin.layout import Tab

translation = univention.admin.localization.translation("univention.admin.handlers.settings.helpdesk")
_ = translation.translate

module = "settings/console_helpdesk"
operations = ["add", "edit", "remove", "search", "move"]
superordinate = "settings/cn"

childs = False
short_description = _("Settings: Console Helpdesk")
long_description = _("Settings for Univention Console Helpdesk Module")
options = {
    "default": univention.admin.option(
        short_description=short_description,
        default=True,
        objectClasses=["top", "univentionUMCHelpdeskClass"],
    )
}

default_containers = ["cn=config,cn=console,cn=univention"]


property_descriptions = {
    "name": univention.admin.property(
        short_description=_("Name"),
        long_description=_("Name of Console-Helpdesk-Settings-Object"),
        syntax=univention.admin.syntax.string_numbers_letters_dots,
        required=True,
        may_change=False,
        identifies=True,
    ),
    "description": univention.admin.property(
        short_description=_("Description"),
        long_description=_("Description"),
        syntax=univention.admin.syntax.string,
        dontsearch=True,
    ),
    "category": univention.admin.property(
        short_description=_("Category"),
        long_description=_("Helpdesk Category"),
        syntax=univention.admin.syntax.string,
        multivalue=True,
    ),
}


layout = [
    Tab(_("General"), _("Basic Values"), layout=["description", "category"]),
]

mapping = univention.admin.mapping.mapping()

mapping.register("name", "cn", None, univention.admin.mapping.ListToString)
mapping.register("description", "description", None, univention.admin.mapping.ListToString)
mapping.register("category", "univentionUMCHelpdeskCategory")


class object(univention.admin.handlers.simpleLdap):
    module = module


lookup = object.lookup
identify = object.identify
