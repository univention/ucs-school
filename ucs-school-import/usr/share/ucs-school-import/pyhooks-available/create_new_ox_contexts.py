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

from ucsschool.importer.utils.user_pyhook import UserPyHook
from ucsschool.lib.models.utils import ucr
from univention.udm import UDM, CreateError

DEFAULT_CONTEXT_ID = "10"


class CreateNewContexts(UserPyHook):
    supports_dry_run = True

    priority = {
        "pre_create": 1,
        "pre_modify": 1,
    }

    def __init__(self, *args, **kwargs):
        super(CreateNewContexts, self).__init__(*args, **kwargs)
        self.existing_contexts = set()
        self.default_context = None
        udm = UDM(self.lo).version(0)
        self.oxcontext_mod = udm.get("oxmail/oxcontext")

    def _check_context(self, user):
        ctx_id = user.udm_properties.get("oxContext", "")
        if not ctx_id:
            self.logger.info("No OX context set for user %r.", user)
            return
        self.logger.info("User %r has OX context %r.", user, ctx_id)

        if not self.existing_contexts:
            for context_obj in self.oxcontext_mod.search():
                if DEFAULT_CONTEXT_ID == context_obj.props.contextid:
                    self.default_context = context_obj
                self.existing_contexts.add(context_obj.props.contextid)

        if ctx_id in self.existing_contexts:
            self.logger.info("OX context %r exists.", ctx_id)
            return
        else:
            self.logger.info("OX context %r does not exists, creating...", ctx_id)

        ox_context = self.oxcontext_mod.new()
        ox_context.position = "cn=open-xchange,{}".format(ucr["ldap/base"])
        ox_context.props.name = "context{}".format(ctx_id)
        ox_context.props.contextid = ctx_id
        for prop in (
            "hostname",
            "oxDBServer",
            "oxQuota",
            "oxadmindaemonversion",
            "oxintegrationversion",
            "oxgroupwareversion",
            "oxguiversion",
        ):
            val = getattr(self.default_context.props, prop)
            setattr(ox_context.props, prop, val)

        if self.dry_run:
            self.logger.info("Dry-run: skipping creation of OX context {!r}.".format(ctx_id))
            return
        try:
            ox_context.save()
            self.logger.info("Created UDM object for OX-context {!r}.".format(ctx_id))
        except CreateError:
            self.logger.info("OX-context {!r} already exists.".format(ctx_id))
        self.existing_contexts.add(ctx_id)

    pre_create = _check_context
    pre_modify = _check_context
