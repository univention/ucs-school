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

from logging import getLogger

import ldap

import univention.admin.uexceptions
from univention.admin import localization
from univention.admin.hook import simpleHook

log = getLogger("ADMIN")
LOGPREFIX = "hook ucsschool_legal_guardian:"

translation = localization.translation("univention-admin-hooks-ucsschool_legal_guardian")
_ = translation.translate

MAX_LEGAL_GUARDIANS = 4
MAX_LEGAL_WARDS = 10


class MaxLegalGuards(univention.admin.uexceptions.base):
    pass


class MaxLegalWards(univention.admin.uexceptions.base):
    pass


class LegalGuardianNotFoundError(univention.admin.uexceptions.base):
    pass


class LegalGuardianModifyError(univention.admin.uexceptions.base):
    pass


class NoLegalWard(univention.admin.uexceptions.base):
    pass


class UcsschoolLegalGuardian(simpleHook):
    def hook_ldap_pre_create(self, obj: univention.admin.handlers.simpleLdap) -> None:
        self._check_restrictions(obj)

    def hook_ldap_pre_modify(self, obj: univention.admin.handlers.simpleLdap) -> None:
        self._check_restrictions(obj)

    # hook_ldap_post_remove() is not required - it is handled by the LDAP overlay refint

    def _check_restrictions(self, obj: univention.admin.handlers.simpleLdap) -> None:
        log.debug(f"{LOGPREFIX} checking restrictions for {obj.dn}")
        log.debug(f"{LOGPREFIX} options={obj.options}")
        if "ucsschoolLegalGuardian" not in obj.options:
            log.debug(f"{LOGPREFIX} obj is no legal guardian")
            return

        log.debug(f"{LOGPREFIX} exists={obj.exists()}")
        log.debug(f"{LOGPREFIX} hasChanged={obj.hasChanged('ucsschoolLegalWard')}")
        if obj.hasChanged("ucsschoolLegalWard"):
            new_wards = set(obj.info.get("ucsschoolLegalWard", []))
            old_wards = set(obj.oldinfo.get("ucsschoolLegalWard", []))
            log.debug(f"{LOGPREFIX} len(new_wards)={len(new_wards)}")
            log.debug(f"{LOGPREFIX} len(old_wards)={len(old_wards)}")

            if len(new_wards) > MAX_LEGAL_WARDS:
                log.debug(
                    f"{LOGPREFIX} Number of ucsschoolLegalWard entries is above limit:\n"
                    f"legal guardian DN={obj.dn}\nentries={new_wards}"
                )
                # New wards were added and we are above the maximum
                raise MaxLegalWards(
                    _(
                        "This legal guardian would have %(num_of_wards)d assigned students, "
                        "which is above the maximum allowed number of assigned students "
                        "(%(max_legal_wards)d)."
                    )
                    % {
                        "num_of_wards": len(new_wards),
                        "max_legal_wards": MAX_LEGAL_WARDS,
                    }
                )

            # Check if the guardian count for the newly referenced wards is at/above the maximum
            # (== testing if adding an additional legal guardian to the legal ward is possible)
            for legal_ward_dn in new_wards - old_wards:
                self._check_legal_guardian_count(obj, legal_ward_dn)

    def _check_legal_guardian_count(
        self, obj: univention.admin.handlers.simpleLdap, legal_ward_dn: str
    ) -> None:
        """Check for specified legal ward, if adding an additional legal guardian is within limits."""
        log.debug(f"{LOGPREFIX} checking number legal_guardian entries at {legal_ward_dn}")
        try:
            ward_attrs = obj.lo.get(
                legal_ward_dn, attr=["ucsschoolLegalGuardian", "objectClass"], required=True
            )
        except ldap.NO_SUCH_OBJECT:
            raise LegalGuardianNotFoundError(
                f"Could not find student '{legal_ward_dn}': the specified student at "
                f"{obj.dn} is incorrect."
            )

        if b"ucsschoolStudent" not in ward_attrs.get("objectClass", []):
            raise NoLegalWard(_("The specified user %(dn)s is no student.") % {"dn": legal_ward_dn})

        num_legal_guardians = len(ward_attrs.get("ucsschoolLegalGuardian", []))
        if num_legal_guardians >= MAX_LEGAL_GUARDIANS:
            log.debug(
                f"{LOGPREFIX} Number of ucsschoolLegalGuardian entries is above limit:\n"
                f"student DN={legal_ward_dn}\nentries={ward_attrs.get('ucsschoolLegalGuardian', [])}"
            )
            raise MaxLegalGuards(
                _(
                    "This student already has %(num_legal_guardians)d assigned legal guardians. "
                    "Adding more would increase it above the maximum allowed number of "
                    "assigned legal guardians (%(max_legal_guardians)d)."
                )
                % {
                    "num_legal_guardians": num_legal_guardians,
                    "max_legal_guardians": MAX_LEGAL_GUARDIANS,
                }
            )

    def hook_ldap_post_create(self, obj: univention.admin.handlers.simpleLdap) -> None:
        self._update_ward_objects(obj)

    def hook_ldap_post_modify(self, obj: univention.admin.handlers.simpleLdap) -> None:
        self._update_ward_objects(obj)

    def _update_ward_objects(self, obj: univention.admin.handlers.simpleLdap) -> None:
        """Update attribute ucsschoolLegalGuardian at legal ward objects"""
        if obj.exists():
            new_wards = set(obj.info.get("ucsschoolLegalWard", []))
            old_wards = set(obj.oldinfo.get("ucsschoolLegalWard", []))
        else:
            new_wards = set(obj.info.get("ucsschoolLegalWard", []))
            old_wards = set()

        # update ucsschoolLegalGuardian at legal ward objects whose reference has been added
        for add_ward_dn in new_wards - old_wards:
            log.debug(f"{LOGPREFIX} adding {obj.dn} to {add_ward_dn}")
            try:
                obj.lo.modify(
                    add_ward_dn,
                    [("ucsschoolLegalGuardian", b"", obj.dn.encode("utf8"))],
                    ignore_license=True,
                )
            except (
                univention.admin.uexceptions.ldapError,
                univention.admin.uexceptions.noObject,
            ) as exc:
                msg = f"Cannot add legal guardian {obj.dn} to {add_ward_dn}: {exc}"
                log.exception(f"{LOGPREFIX} {msg}")
                raise LegalGuardianModifyError(msg)

        # update ucsschoolLegalGuardian at legal ward objects whose reference has been removed
        for remove_ward_dn in old_wards - new_wards:
            log.debug(f"{LOGPREFIX} removing {obj.dn} from {remove_ward_dn}")
            try:
                obj.lo.modify(
                    remove_ward_dn,
                    [("ucsschoolLegalGuardian", obj.dn.encode("utf8"), b"")],
                    ignore_license=True,
                )
            except univention.admin.uexceptions.noObject:
                log.info(
                    f"{LOGPREFIX} Cannot remove legal guardian {obj.dn} from student "
                    f"{remove_ward_dn}: student does not exist any longer"
                )
            except univention.admin.uexceptions.ldapError as exc:
                msg = f"Cannot remove legal guardian {obj.dn} from {remove_ward_dn}: {exc}"
                log.exception(f"{LOGPREFIX} {msg}")
                raise LegalGuardianModifyError(msg)
