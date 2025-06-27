#!/usr/bin/python3
#
# UCS@school legal guardian hook
#
# Copyright (C) 2025 Univention GmbH
#
# https://www.univention.de/
#
# All rights reserved.
#
# source code of this program is made available
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
# /usr/share/common-licenses/AGPL-3. If not, see <http://www.gnu.org/licenses/>.


from ldap.filter import filter_format

import univention.admin.uexceptions
from univention.admin import localization
from univention.admin.hook import simpleHook

translation = localization.translation("ucsschool-import-udm-hooks")
_ = translation.translate

MAX_LEGAL_GUARDIANS = 4
MAX_LEGAL_WARDS = 10


class MaxLegalGuards(univention.admin.uexceptions.base):
    pass


class MaxLegalWards(univention.admin.uexceptions.base):
    pass


class UcsschoolLegalWard(simpleHook):
    def _check_legal_ward_count(self, obj, legal_guardian_dn):

        num_legal_wards = len(
            obj.lo.searchDn(filter=filter_format("(ucsschoolLegalGuardian=%s)", (legal_guardian_dn,)))
        )

        if num_legal_wards >= MAX_LEGAL_WARDS:
            raise MaxLegalWards(
                _(
                    "Legal guardian %s already has %d legal wards. "
                    "Adding %s would increase it above the maximum allowed legal wards."
                )
                % (legal_guardian_dn, num_legal_wards, obj.dn)
            )

    def _check_restrictions(self, obj):

        if "ucsschoolStudent" not in obj.options:
            return

        if "ucsschoolLegalGuardian" in obj.info:

            current_guardians = obj.info.get("ucsschoolLegalGuardian", [])
            old_guardians = obj.oldinfo.get("ucsschoolLegalGuardian", [])
            new_legal_guardian_dns = set(current_guardians).difference(old_guardians)

            if len(new_legal_guardian_dns) == 0:
                return

            if len(new_legal_guardian_dns) > 0 and len(current_guardians) > MAX_LEGAL_GUARDIANS:
                # New guardians were added and we are above the maximum
                raise MaxLegalGuards(
                    _(
                        "Legal ward %s has %d legal guardians, which is above"
                        " the maximum allowed number of legal guardians (%d)."
                    )
                    % (obj.dn, len(obj["ucsschoolLegalGuardian"]), MAX_LEGAL_GUARDIANS)
                )

            for legal_guardian_dn in new_legal_guardian_dns:
                self._check_legal_ward_count(obj, legal_guardian_dn)

    def hook_ldap_pre_create(self, obj):
        self._check_restrictions(obj)

    def hook_ldap_pre_modify(self, obj):
        self._check_restrictions(obj)
