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


def test_missing_checks():
    ucsschool.kelvin.import_config._ucs_school_import_framework_initialized = False
    with pytest.raises(UcsSchoolImportError):
        init_ucs_school_import_framework(configuration_checks=["mapped_udm_properties"])
    ucsschool.kelvin.import_config._ucs_school_import_framework_error = None
    with pytest.raises(UcsSchoolImportError):
        init_ucs_school_import_framework(configuration_checks=["class_overwrites"])
    ucsschool.kelvin.import_config._ucs_school_import_framework_error = None
    init_ucs_school_import_framework(
        configuration_checks=["mapped_udm_properties", "class_overwrites"]
    )
