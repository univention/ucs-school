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
from univention.udm import UDM
from univention.udm.exceptions import ModifyError, NoObject, WrongObjectType

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


def _get_student(dn, user_mod):
    try:
        student = user_mod.get(dn)
    except (NoObject, WrongObjectType):
        raise LegalGuardianNotFoundError(
            f"Could not find student '{dn}' to modify ucsschoolLegalGuardian"
        )
    if "ucsschoolStudent" not in student.options:
        raise LegalGuardianNotFoundError(
            f"Could not modify ucsschoolLegalGuardian on '{dn}' because they are not a student"
        )
    return student


def _save_student(student):
    try:
        student.save()
    except ModifyError as exc:
        raise LegalGuardianModifyError(
            f"Could not modify ucsschoolLegalGuardian on '{student.dn}': {exc}"
        )


class UcsschoolLegalGuardian(simpleHook):
    def hook_open(self, obj):
        if "ucsschoolLegalGuardian" not in obj.options:
            return
        if obj.dn:
            obj.info["ucsschoolLegalWard"] = obj.lo.searchDn(
                filter=filter_format("(ucsschoolLegalGuardian=%s)", (obj.dn,))
            )

    def hook_ldap_addlist(self, obj, al):
        # hook_ldap_modlist will be called later anyways, but at that point
        # ucsschoolLegalWard needs to be already removed from the add list
        # or udm throws an error
        return self.hook_ldap_modlist(obj, al)

    def hook_ldap_modlist(self, obj, ml):
        if "ucsschoolLegalGuardian" not in obj.options:
            return ml
        for change in ml:
            if change[0] == "ucsschoolLegalWard":
                legal_wards_old = set(change[1])
                legal_wards_new = set(change[2])
                break
        else:
            # no change in ucsschoolLegalWard
            return ml
        if len(legal_wards_new) >= MAX_LEGAL_WARDS:
            # New wards were added and we are above the maximum
            raise MaxLegalWards(
                _(
                    "Legal guardian %(self_dn)s would have %(num_of_wards)d legal wards, "
                    "which is above the maximum allowed number of legal wards (%(max_legal_wards)d)."
                )
                % {
                    "self_dn": obj.dn,
                    "num_of_wards": len(legal_wards_new),
                    "max_legal_wards": MAX_LEGAL_WARDS,
                }
            )
        user_mod = UDM(obj.lo).version(2).get("users/user")
        students_to_change = []
        for added_legal_ward in legal_wards_new.difference(legal_wards_old):
            student = _get_student(added_legal_ward.decode(), user_mod)
            if len(student.props.ucsschoolLegalGuardian) >= MAX_LEGAL_GUARDIANS:
                raise MaxLegalGuards(
                    _(
                        "Legal ward %(student_dn)s already has %(num_legal_guardians)d legal guardians. "
                        "Adding %(self_dn)s would increase it above the maximum allowed "
                        "legal guardians (%(max_legal_guardians)d)."
                    )
                    % {
                        "student_dn": student.dn,
                        "num_legal_guardians": len(student.props.ucsschoolLegalGuardian),
                        "self_dn": obj.dn,
                        "max_legal_guardians": MAX_LEGAL_GUARDIANS,
                    }
                )
            student.props.ucsschoolLegalGuardian.append(obj.dn)
            students_to_change.append(student)
        for removed_legal_ward in legal_wards_old.difference(legal_wards_new):
            student = _get_student(removed_legal_ward.decode(), user_mod)
            student.props.ucsschoolLegalGuardian.remove(obj.dn)
            students_to_change.append(student)
        for student in students_to_change:
            # Only start saving when it will probably work for all
            _save_student(student)
        return [change for change in ml if change[0] != "ucsschoolLegalWard"]
