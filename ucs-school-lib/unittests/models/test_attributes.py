import sys

import pytest

from ucsschool.lib.models.attributes import is_valid_win_directory_name

sys.path.insert(1, "modules")


class TestIsValidWinDirectoryName:
    @pytest.mark.parametrize(
        "input,expected_result",
        [
            ("good_name", True),
            ("good.name", True),
            ("good name", True),
            (".good_name", True),
            ("com1", False),
            ("COM1.txt", False),
            ("LPT9", False),
            ("con", False),
            ("good name ", False),
            ("good.name.", False),
            ("bad<name", False),
            ("bad:name", False),
            ("bad/name", False),
            ("bad|name", False),
            ("bad?name", False),
            ("bad*name", False),
            ("a" * 256, False),
        ],
    )
    def test_directory_name_validation(self, input, expected_result):
        assert is_valid_win_directory_name(name=input) is expected_result
