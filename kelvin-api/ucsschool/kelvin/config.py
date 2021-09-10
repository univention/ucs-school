from pathlib import Path
from typing import Any, Dict, List

import lazy_object_proxy
import ujson
from pydantic import BaseSettings

from ..importer.configuration import ReadOnlyDict
from ..importer.models.import_user import ImportUser
from ..lib.models.group import SchoolClass
from ..lib.models.school import School
from .constants import UDM_MAPPED_PROPERTIES_CONFIG_FILE
from .exceptions import InvalidConfiguration
from .import_config import get_import_config


def json_config_settings_source(path: Path):
    def _json_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
        """
        A simple settings source that loads variables from a JSON file
        at the project's root.

        Here we happen to choose to use the `env_file_encoding` from Config
        when reading `config.json`

        Source: https://pydantic-docs.helpmanual.io/usage/settings/#customise-settings-sources
        """
        encoding = settings.__config__.env_file_encoding
        try:
            result = ujson.loads(path.read_text(encoding))
        except FileNotFoundError:
            # TODO: We should log this error,
            #  but can we expect logging to be set up during loading of config?
            result = {}
        return result

    return _json_config_settings_source


def import_config_udm_mapping_source(settings: BaseSettings) -> Dict[str, Any]:
    config: ReadOnlyDict = get_import_config()
    if "mapped_udm_properties" in config:
        return {"user": config.get("mapped_udm_properties")}
    else:
        return {}


class UDMMappingConfiguration(BaseSettings):
    school: List[str] = []
    user: List[str] = []
    school_class: List[str] = []

    class Config:
        env_file_encoding = "utf-8"

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                init_settings,
                json_config_settings_source(UDM_MAPPED_PROPERTIES_CONFIG_FILE),
                import_config_udm_mapping_source,
            )

    def prevent_mapped_attributes_in_udm_properties(self):
        """
        Make sure users do not configure values for ucsschool.lib mapped Attributes
        in udm_properties.
        """
        for udm_properties, lib_model in [
            (self.school, School),
            (self.user, ImportUser),
            (self.school_class, SchoolClass),
        ]:
            bad_props = set(udm_properties).intersection(lib_model.attribute_udm_names())
            if bad_props:
                raise InvalidConfiguration(
                    "UDM properties '{}' must be set as attributes of the {} object (not in "
                    "udm_properties).".format("', '".join(bad_props), lib_model.__name__)
                )


UDM_MAPPING_CONFIG: UDMMappingConfiguration = lazy_object_proxy.Proxy(UDMMappingConfiguration)


def load_configurations():
    """
    This function can be called to initialize all settings in this module
    in case an early abort for faulty configuration is desired.
    """
    UDM_MAPPING_CONFIG.prevent_mapped_attributes_in_udm_properties()
