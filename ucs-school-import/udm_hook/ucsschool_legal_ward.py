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

translation = localization.translation("univention-admin-hooks-ucsschool_legal_ward")
_ = translation.translate

MAX_LEGAL_GUARDIANS = 4
MAX_LEGAL_WARDS = 10


class MaxLegalGuards(univention.admin.uexceptions.base):
    pass


class MaxLegalWards(univention.admin.uexceptions.base):
    pass


class UcsschoolLegalWard(simpleHook):
    def _check_legal_ward_count(self, obj: univention.admin.handlers.simpleLdap, legal_guardian_dn: str):
        """Check how many wards are assigned at legal guardian."""

        num_legal_wards = len(
            obj.lo.searchDn(filter=filter_format("(ucsschoolLegalGuardian=%s)", (legal_guardian_dn,))) # TODO
        )

        if num_legal_wards >= MAX_LEGAL_WARDS:
            raise MaxLegalWards(
                _(
                    "Legal guardian %(legal_guardian_dn)s already has %(num_legal_wards)d "
                    "legal wards. Adding %(self_dn)s would increase it above the maximum "
                    "allowed legal wards (%(max_legal_wards)d)."
                )
                % {
                    "legal_guardian_dn": legal_guardian_dn,
                    "num_legal_wards": num_legal_wards,
                    "self_dn": obj.dn,
                    "max_legal_wards": MAX_LEGAL_WARDS,
                }
            )

    def _check_restrictions(self, obj: univention.admin.handlers.simpleLdap) -> None:
        """Check if restrictions of legal guardian and legal ward are met."""

        if "ucsschoolStudent" not in obj.options:
            return

        if "ucsschoolLegalGuardian" in obj.info:

            new_guardians = obj.info.get("ucsschoolLegalGuardian", [])
            old_guardians = obj.oldinfo.get("ucsschoolLegalGuardian", [])

            if len(new_guardians) > MAX_LEGAL_GUARDIANS:
                # New guardians were added and we are above the maximum
                raise MaxLegalGuards(
                    _(
                        "Legal ward %(self_dn)s would have %(num_legal_guardians)d "
                        "legal guardians, which is above the maximum allowed number of "
                        "legal guardians (%(max_legal_guardians)d)."
                    )
                    % {
                        "self_dn": obj.dn,
                        "num_legal_guardians": len(obj["ucsschoolLegalGuardian"]),
                        "max_legal_guardians": MAX_LEGAL_GUARDIANS,
                    }
                )

            for legal_guardian_dn in set(new_guardians).difference(old_guardians):
                self._check_legal_ward_count(obj, legal_guardian_dn)

    def hook_ldap_pre_create(self, obj: univention.admin.handlers.simpleLdap) -> None:
        self._check_restrictions(obj)

    def hook_ldap_pre_modify(self, obj: univention.admin.handlers.simpleLdap) -> None:
        self._check_restrictions(obj)
