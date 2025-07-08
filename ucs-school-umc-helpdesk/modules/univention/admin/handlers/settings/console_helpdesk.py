#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# UCS@school Helpdesk
#  univention admin helpdesk module
#
# SPDX-FileCopyrightText: 2006-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

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
