import pytest

import ucsschool.kelvin.constants
from ucsschool.importer.exceptions import UcsSchoolImportError
from ucsschool.kelvin.import_config import init_ucs_school_import_framework

must_run_in_container = pytest.mark.skipif(
    not ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter.",
)


@must_run_in_container
def test_config_loads():
    init_ucs_school_import_framework()


def test_missing_checks(reset_import_config):
    reset_import_config()
    with pytest.raises(UcsSchoolImportError) as exc_info:
        init_ucs_school_import_framework(configuration_checks=["mapped_udm_properties"])
    assert 'Missing "class_overwrites" in configuration checks' in exc_info.value.args[0]
    reset_import_config()
    with pytest.raises(UcsSchoolImportError) as exc_info:
        init_ucs_school_import_framework(configuration_checks=["class_overwrites"])
    assert 'Missing "mapped_udm_properties" in configuration checks' in exc_info.value.args[0]
    reset_import_config()
    init_ucs_school_import_framework(
        configuration_checks=["mapped_udm_properties", "class_overwrites"]
    )
