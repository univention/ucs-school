#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2025 Univention GmbH
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

from typing import List

from ldap.filter import filter_format

from ucsschool.importer.configuration import Configuration
from ucsschool.importer.exceptions import InvalidLegalGuardian, InvalidLegalWard, UcsSchoolImportError
from ucsschool.importer.utils.post_read_pyhook import PostReadPyHook


class RecordUidConversionError(Exception):
    pass


class LegalGuardianAsRecordUid(PostReadPyHook):
    supports_dry_run = False
    priority = {
        "entry_read": 20,
        "all_entries_read": None,
    }

    def __init__(self, *args, **kwargs):
        super(LegalGuardianAsRecordUid, self).__init__(*args, **kwargs)
        self.config = Configuration()

    def entry_read(self, _, input_data, input_dict):
        mapping = self.config["csv"]["mapping"]
        source_uid = self._get_source_uid(mapping, input_dict)
        for csv_attr_name, school_attr_name in mapping.items():
            if school_attr_name in ["legal_guardians", "legal_wards"] and input_dict[csv_attr_name]:
                try:
                    input_dict[csv_attr_name] = ",".join(
                        self._record_uids_to_uids(source_uid, input_dict[csv_attr_name].split(","))
                    )
                except RecordUidConversionError as exc:
                    if school_attr_name == "legal_guardians":
                        raise InvalidLegalGuardian(exc)
                    else:
                        raise InvalidLegalWard(exc)

    def _get_source_uid(self, mapping, input_dict):
        source_uid = self.config.get("source_uid")
        if not source_uid:
            for csv_attr_name, school_attr_name in mapping.items():
                if school_attr_name == "source_uid":
                    source_uid = input_dict[csv_attr_name]
        if not source_uid:
            raise UcsSchoolImportError("No source_uid found")
        return source_uid

    def _record_uids_to_uids(self, source_uid: str, record_uids: List[str]) -> List[str]:
        uids = []
        for record_uid in record_uids:
            filter_s = filter_format(
                "(&(ucsschoolSourceUID=%s)(ucsschoolRecordUID=%s))", (source_uid, record_uid)
            )
            res = self.lo.search(filter_s, attr=("uid",))
            if len(res) > 1:
                raise RecordUidConversionError(
                    f"Could not find distinct user with "
                    f"source_uid={source_uid} and record_uid={record_uid}"
                )
            try:
                uids.append(res[0][1]["uid"][0].decode("utf-8"))
            except IndexError:
                raise RecordUidConversionError(
                    f"Could not find user with source_uid={source_uid} and record_uid={record_uid}"
                )
        return uids
