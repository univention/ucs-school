#
# Univention UCS@school
#
# Copyright 2007-2024 Univention GmbH
#
# http://www.univention.de/
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
"""\
A UCS@school command line interface to fetch
user and group data from LUSD and import the fetched data into
the UCS@school domain.
"""
import configparser
import json
import logging
import os
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import jwt
import requests

from ucsschool.lib.models.school import School
from ucsschool.lib.models.utils import get_file_handler, get_stream_handler
from univention.admin.uexceptions import noObject
from univention.admin.uldap import getMachineConnection

CONFIG_PATH: Path = Path("/etc/ucs-school-import-lusd/config.ini")

LOCK_FILE = Path("/var/lib/ucs-school-import-lusd/lock")
LOG_FILE = Path("/var/log/univention/ucs-school-import-lusd.log")

ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

logger = logging.getLogger(__name__)


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Configuration:

    lusd_api_url: str
    lusd_api_oauth_iss: str
    skip_fetch: bool
    dry_run: bool
    student_import_config_path: Path
    teacher_import_config_path: Path

    log_level: str = "ERROR"
    school_id_map: Dict[str, List[str]] = field(default_factory=dict)
    authentication_key_file_path: Path = Path("/var/lib/ucs-school-import-lusd/auth_key")
    lusd_data_save_path: Path = Path("/var/lib/ucs-school-import-lusd/data/")
    ucs_school_import_cli: Path = Path("/usr/share/ucs-school-import/scripts/ucs-school-user-import")

    def validate(self) -> None:
        """Validate the values stored in the configuration."""
        if not len(self.school_id_map) > 0:
            raise ConfigurationError("No schools configured.")

        if not self.student_import_config_path.exists():
            raise FileNotFoundError(
                f"Student import configuration not found in path {self.student_import_config_path}."
            )

        if not self.teacher_import_config_path.exists():
            raise FileNotFoundError(
                f"Teacher import configuration not found in path {self.teacher_import_config_path}."
            )

        if not self.authentication_key_file_path.exists():
            raise FileNotFoundError(
                f"Private key file not found in path {self.authentication_key_file_path}."
            )

        if not self.lusd_api_url:
            raise ConfigurationError(f"No valid LUSD API URL given: {self.lusd_api_url}.")

        if self.log_level not in LOG_LEVELS:
            raise ConfigurationError(
                f"Not a valid log level: {self.log_level}, choose from: {LOG_LEVELS}"
            )


def normalize_schools(school_id_map: Dict[str, str]) -> Dict[str, List[str]]:
    # to avoid duplicates, use the same case as the ldap ou
    lo, _ = getMachineConnection()
    normalized_school_id_map = {}
    for school, school_id in school_id_map.items():
        try:
            normalized_school_id_map[School.from_dn(School(school).dn, None, lo).name] = school_id.split(
                ","
            )
        except noObject:
            logger.error(
                f"Could not find school in ldap: {school}, delete it from the mapping or create it"
            )
            sys.exit(1)
    return normalized_school_id_map


class ImportLUSD:
    def __init__(self, args: Namespace) -> None:
        if not args.configuration_filepath.exists():
            self.setup_logging()
            logger.error(f"Config path {CONFIG_PATH} does not exist.")
            sys.exit(1)
        file_config = configparser.ConfigParser()
        file_config.read(args.configuration_filepath)
        self.configuration = Configuration(
            student_import_config_path=Path(file_config["Settings"]["student_import_config_path"]),
            teacher_import_config_path=Path(file_config["Settings"]["teacher_import_config_path"]),
            dry_run=args.dry_run,
            skip_fetch=args.skip_fetch,
            log_level=args.log_level if args.log_level else file_config["Settings"]["log_level"],
            school_id_map=normalize_schools(dict(file_config["SchoolMappings"])),
            lusd_api_url=os.environ.get("LUSD_URL", "https://ucs.hessen.de"),
            lusd_api_oauth_iss=os.environ.get("LUSD_ISS", "fa0e36138ff4d23ad2b6"),
        )
        self.setup_logging()
        logger.debug(f"Command line arguments: {vars(args)}")
        for section in file_config.sections():
            logger.debug(f"File config [{section}]: {dict(file_config[section].items())}")
        logger.debug(f"Configuration: {self.configuration}")
        try:
            self.configuration.validate()
        except (ConfigurationError, FileNotFoundError) as exc:
            logger.error(exc)
            sys.exit(1)

    def run_import(self) -> None:
        if not self.configuration.skip_fetch:
            self.fetch_and_store_lusd_data()
        else:
            logger.info("Skipping LUSD data download")
        for school_name in self.configuration.school_id_map.keys():
            self.run_sisopi_import(school_name)

    def fetch_and_store_lusd_data(self) -> None:
        """fetch and store data for all configured schools"""
        for school_name in self.configuration.school_id_map.keys():
            school_ids = self.configuration.school_id_map[school_name]

            for role in (ROLE_STUDENT, ROLE_TEACHER):
                logger.info(f"Starting download of LUSD data for role: {role}, in school: {school_name}")
                file_path = self.get_lusd_data_save_path(school_name, role)
                data = self.fetch_school_lusd_data(school_ids, role, file_path)
                data_dir_path = self.configuration.lusd_data_save_path.joinpath(school_name)
                data_dir_path.mkdir(parents=True, exist_ok=True)
                data_path = data_dir_path.joinpath(f"{role}.json")
                with open(data_path, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info(f"Finished download of LUSD data for role: {role}, in school: {school_name}")
                logger.debug(f"Data saved to {data_path}")

    def get_bearer_token(self) -> str:
        private_key_file = self.configuration.authentication_key_file_path
        issued_at_time = int(time.time())
        expiration_time = int(issued_at_time + 30)
        jwt_payload = {
            "iss": self.configuration.lusd_api_oauth_iss,
            "aud": "LUSD externer Datenaustausch",
            "iat": issued_at_time,
            "exp": expiration_time,
        }
        try:
            jwt_token = jwt.encode(jwt_payload, private_key_file.read_text(), algorithm="RS512")
        except ValueError:
            logger.error(f"The authentication key {private_key_file} is not valid. Not a pem file?")
            sys.exit(1)
        return str(jwt_token.decode())

    def fetch_school_lusd_data(self, school_ids: List[str], role: str, file_path: Path) -> Any:
        """Store LUSD data for school `school_ids` in `file_path`"""
        token = self.get_bearer_token()

        if role == ROLE_STUDENT:
            request_url = f"{self.configuration.lusd_api_url}/anfrage?format=JSON"
            action_id = "Administrationsdaten Lernende lesen"
        elif role == ROLE_TEACHER:
            request_url = f"{self.configuration.lusd_api_url}/anfrage?format=JSON"
            action_id = "Administrationsdaten Personal lesen"

        request_data = [
            {
                "bezeichnung": action_id,
                "version": 1,
                "parameter": {
                    "schulDienststellennummern": school_ids,
                },
            }
        ]

        response = requests.post(
            request_url, json=request_data, headers={"Authorization": f"Bearer {token}"}
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            logger.error(f"Could not retrieve LUSD data: {exc}\n{exc.response.text}")
            sys.exit(1)
        response_data = response.json()
        return response_data

    def get_lusd_data_save_path(self, school_name: str, role: str) -> Path:
        data_dir_path = self.configuration.lusd_data_save_path.joinpath(school_name)
        if not data_dir_path.exists():
            logger.warning(f"Path does not exist, creating {data_dir_path}")
            data_dir_path.mkdir(parents=True)
        data_path = data_dir_path.joinpath(f"{role}.json")
        return data_path

    def run_sisopi_import(self, school_name: str) -> None:
        """Run a single SiSoPi import for school `school_name`"""
        for role in (ROLE_STUDENT, ROLE_TEACHER):
            if role == ROLE_STUDENT:
                import_config = self.configuration.student_import_config_path
            elif role == ROLE_TEACHER:
                import_config = self.configuration.teacher_import_config_path

            input_file_path = self.get_lusd_data_save_path(school_name, role)
            # Add log path
            cmd = [
                str(self.configuration.ucs_school_import_cli),
                "--conffile",
                str(import_config),
                "--infile",
                str(input_file_path),
                "--user_role",
                role,
                "--school",
                school_name,
            ]

            if self.configuration.dry_run:
                cmd.append("--dry-run")
            if logger.isEnabledFor(logging.DEBUG):
                cmd.extend(["--logfile", str(LOG_FILE), "--verbose"])

            logger.info(f"Starting import for role {role}, in school {school_name}")
            logger.debug(f"Running ucs-school-user-import subprocess with command {cmd}.")
            for handler in logger.handlers:
                # Flush here, so the subprocess can write safely in the same file
                handler.flush()
            subprocess.check_call(  # nosec
                cmd,
                stderr=None if logger.isEnabledFor(logging.DEBUG) else subprocess.DEVNULL,
            )
            logger.info(f"Finished import for role {role}, in school {school_name}")

    def setup_logging(self) -> None:
        logger.addHandler(get_stream_handler(self.configuration.log_level))
        logger.addHandler(get_file_handler(self.configuration.log_level, LOG_FILE))
        logger.setLevel(self.configuration.log_level)


def get_args() -> Namespace:
    parser = ArgumentParser(str(Path(sys.argv[0]).absolute()), description=__doc__)

    parser.add_argument(
        "--configuration-filepath",
        "-c",
        dest="configuration_filepath",
        default=CONFIG_PATH,
        help=("The path to the configuration file of this CLI tool."),
        type=Path,
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        choices=LOG_LEVELS,
        type=str,
        help="The log level.",
    )
    parser.add_argument(
        "--skip-fetch",
        dest="skip_fetch",
        default=False,
        action="store_true",
        help=("Skip the fetching of LUSD DATA and import the previous data set again."),
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        default=False,
        action="store_true",
        help="Run the import in dry run mode",
    )
    return parser.parse_args()


def run() -> None:
    args = get_args()
    importLUSD = ImportLUSD(args)
    try:
        LOCK_FILE.parent.mkdir(exist_ok=True)
        LOCK_FILE.touch(exist_ok=False)
    except FileExistsError:
        logger.error(f"The LUSD importer is already running: Lock file {LOCK_FILE} exists.")
        sys.exit(1)
    try:
        importLUSD.run_import()
    finally:
        if LOCK_FILE.exists() and LOCK_FILE.is_file():
            LOCK_FILE.unlink()


if __name__ == "__main__":
    run()
