# SPDX-FileCopyrightText: 2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import sys

import pytest

from ucsschool.lib.models.group import SchoolGroup

sys.path.insert(1, "modules")


class TestGroups:
    @pytest.mark.parametrize(
        "school,name,expected_result",
        [
            ("aaaaa", "another group-aaaaa", "another group"),
            ("aaaaa", "another group aaaaa", "another group"),
            ("aaaaa", "mitarbeiter-aaaaa", "mitarbeiter"),
            ("aaaaa", "schueler-aaaaa", "schueler"),
            ("aaaaa", "lehrer-aaaaa", "lehrer"),
            ("aaaaa", "Domain Users aaaaa", "Domain Users"),
            ("bbbbb", "mycoolgroup", "mycoolgroup"),
            ("bbbbb", "mitarbeiter", "mitarbeiter"),
            ("bbbbb", "schueler", "schueler"),
            ("bbbbb", "lehrer", "lehrer"),
            ("bbbbb", "Domain Users", "Domain Users"),
            (None, "mitarbeiter-aaaaa", "mitarbeiter-aaaaa"),
            (None, "schueler", "schueler"),
            (None, "lehrer-aaaaa", "lehrer-aaaaa"),
            (None, "Domain Users aaaaa", "Domain Users aaaaa"),
        ],
    )
    def test_group_suffix_detection(self, school, name, expected_result):
        assert SchoolGroup(name=name, school=school).get_relative_name() == expected_result
