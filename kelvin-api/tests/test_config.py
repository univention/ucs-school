from unittest.mock import MagicMock, patch

import pytest

from ucsschool.kelvin.config import UDMMappingConfiguration
from ucsschool.kelvin.constants import CN_ADMIN_PASSWORD_FILE, UDM_MAPPED_PROPERTIES_CONFIG_FILE
from ucsschool.kelvin.exceptions import InvalidConfiguration

pytestmark = pytest.mark.skipif(
    not CN_ADMIN_PASSWORD_FILE.exists(),
    reason="Must run inside Docker container started by appcenter due to import config problems.",
)


def test_config_priority_user(fs):
    """
    Tests that the settings of the import config for mapped udm properties is overwritten
    by the new config, if present.
    """
    fs.create_file(UDM_MAPPED_PROPERTIES_CONFIG_FILE, contents='{"user": ["new_config"]}')
    config = UDMMappingConfiguration()
    assert config.user == ["new_config"], config


@patch("ucsschool.kelvin.config.import_config_udm_mapping_source")
def test_config_no_file(import_config_udm_mapping_source_mock: MagicMock, fs):
    """
    Tests that the settings object can also be created with the new config file not existing.

    We have to mock the import config source function instead of using pyfakefs here as well,
    since the import framework has some caching that would make it more complicated that just replacing
    the file, since the framework is already 'initialized' when this test starts.
    """
    import_config_udm_mapping_source_mock.return_value = {"user": ["import_config"]}
    config = UDMMappingConfiguration()
    assert config.user == ["import_config"], config


def test_invalid_config():
    config = UDMMappingConfiguration(user=[], school_class=["description"], school=[])
    with pytest.raises(InvalidConfiguration):
        config.prevent_mapped_attributes_in_udm_properties()
