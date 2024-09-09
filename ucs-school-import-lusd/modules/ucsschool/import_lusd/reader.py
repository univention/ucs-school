import json
from typing import Any, Dict, Generator

from ucsschool.importer.exceptions import ConfigurationError
from ucsschool.importer.models.import_user import ImportUser
from ucsschool.importer.reader.csv_reader import CsvReader


class LUSDReader(CsvReader):  # type: ignore[misc]
    def __init__(self, filename: str, header_lines: int = 0, **kwargs: Any) -> None:
        """
        :param str filename: Path to file with user data.
        :param int header_lines: Number of lines before the actual data starts.
        :param dict kwargs: optional parameters for use in derived classes
        """
        super().__init__(filename, header_lines, **kwargs)

        self.config["csv"] = self.config["lusd"]
        self._delimiter: str = self.config["csv"].get("incell-delimiter", {}).get("default", ",")

    def read(self) -> Generator[Dict[str, str], None, None]:
        """
        Generate dicts from a JSON file.
        :return: iterator over list of dicts
        :rtype: Generator[Dict[str, str], None, None]
        """
        with open(self.filename) as fp:
            self.logger.debug("Reading %r.", self.filename)

            json_data = json.load(fp)[0]["antwort"][self.config["lusd"]["lusd_user_type"]]

        try:
            self.fieldnames = json_data[0].keys()
        except IndexError:
            self.logger.warning("No users in %r.", self.filename)
            self.fieldnames = []
            return
        missing_attributes = self._get_missing_columns()

        # see LUSD specification
        optional_attrs = ["klassenname"]

        if missing_attributes and not all(attr in optional_attrs for attr in missing_attributes):
            raise ConfigurationError(
                "Attributes configured in csv:mapping missing: "
                "{!r}. Attributes found: {!r}".format(missing_attributes, self.fieldnames)
            )

        user_obj: Dict[str, Any]
        for idx, user_obj in enumerate(json_data):
            self.entry_count = idx + 1
            self.input_data = user_obj
            self.lusd_preprocessing(user_obj)
            yield user_obj

    def lusd_preprocessing(self, user_obj: Dict[str, Any]) -> None:
        """Convert LUSD API attributes which are arrays to string to be conform with the CsvReader"""
        for attr in ["klassenlehrerKlassen", "klassenlehrerVertreterKlassen"]:
            if attr in user_obj:
                user_obj[attr] = self._delimiter.join(
                    [
                        class_obj["klassenname"].replace(
                            self._delimiter,
                            self.config.get("school_classes_invalid_character_replacement", ""),
                        )
                        for class_obj in user_obj[attr]
                        if "klassenname" in class_obj
                    ]
                )
        if "klassenname" not in user_obj and "schuelerUID" in user_obj:
            user_obj["klassenname"] = "lusd_noclass"

    def handle_input(
        self, mapping_key: str, mapping_value: str, value: str, import_user: ImportUser
    ) -> bool:
        """
        This is a hook into :py:meth:`map`.

        LUSD specific input handling

        :param str mapping_key: the key in config["csv"]["mapping"]
        :param str mapping_value: the value in config["csv"]["mapping"]
        :param str value: the associated value from the JSON object
        :param ImportUser import_user: the object to modify
        :return: True if the field was handled here. It will be ignored in map(). False if map() should
            handle the field.
        :rtype: bool
        """
        ret = super().handle_input(mapping_key, mapping_value, value, import_user)

        if ret:
            return True
        elif mapping_value == "__append_school_classes":
            # Intended to merge attributes "klassenlehrerKlassen" and "klassenlehrerVertreterKlassen"
            # to attribute school_classes if that is required by the customer
            if not import_user.school_classes:
                import_user.school_classes = value
                return True
            elif isinstance(import_user.school_classes, str):
                import_user.school_classes = self._delimiter.join([import_user.school_classes, value])
                return True
            else:
                self.logger.error(
                    f"Cannot append to import_user.school_classes {import_user.school_classes}"
                )
        return False
