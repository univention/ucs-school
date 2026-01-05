#!/usr/bin/python3

# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

# -*- coding: utf-8 -*-
#
# Univention UCS@school
#

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
