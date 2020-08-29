# Copyright 2020 Univention GmbH
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

import logging
from pathlib import Path
from typing import NamedTuple

import lazy_object_proxy
import pkg_resources


class Oauth2Scope(NamedTuple):
    model: str
    operation: str
    description: str

    def __str__(self):
        return f"{self.model}:{self.operation}"


def _app_version() -> str:
    try:
        return pkg_resources.get_distribution(APP_ID).version
    except pkg_resources.DistributionNotFound:
        pass
    # pytest before installation, try to read VERSION.txt or simply return a dummy value
    try:
        with (Path(__file__).parent.parent.parent / "VERSION.txt").open("r") as fp:
            return fp.read().strip()
    except IOError:
        return "1.1.0"


APP_ID = "ucsschool-kelvin-rest-api"
APP_VERSION = lazy_object_proxy.Proxy(_app_version)
API_USERS_GROUP_NAME = f"{APP_ID}-admins"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = APP_BASE_PATH / "conf"
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"
DEFAULT_LOG_LEVELS = {
    None: logging.INFO,
    "fastapi": logging.INFO,
    "requests": logging.INFO,
    "udm_rest_client": logging.INFO,
    "univention": logging.INFO,
    "ucsschool": logging.INFO,
    "uvicorn.access": logging.INFO,
    "uvicorn.error": logging.INFO,
}
IMPORT_CONFIG_FILE_DEFAULT = Path(
    "/usr/share/ucs-school-import/configs/kelvin_defaults.json"
)
IMPORT_CONFIG_FILE_USER = Path("/var/lib/ucs-school-import/configs/kelvin.json")
KELVIN_IMPORTUSER_HOOKS_PATH = Path("/var/lib/ucs-school-import/kelvin-hooks")
LOG_FILE_PATH = Path("/var/log/univention/ucsschool-kelvin-rest-api/http.log")
MACHINE_PASSWORD_FILE = "/etc/machine.secret"
OAUTH2_SCOPES = {
    "role": {
        "create": Oauth2Scope(
            model="role", operation="create", description="Create role objects.",
        ),
        "read": Oauth2Scope(
            model="role", operation="read", description="Read role objects."
        ),
        "update": Oauth2Scope(
            model="role", operation="update", description="Modify role objects.",
        ),
        "delete": Oauth2Scope(
            model="role", operation="delete", description="Delete role objects.",
        ),
    },
    "school": {
        "create": Oauth2Scope(
            model="school", operation="create", description="Create school objects.",
        ),
        "read": Oauth2Scope(
            model="school", operation="read", description="Read school objects."
        ),
        "update": Oauth2Scope(
            model="school", operation="update", description="Modify school objects.",
        ),
        "delete": Oauth2Scope(
            model="school", operation="delete", description="Delete school objects.",
        ),
    },
    "school_class": {
        "create": Oauth2Scope(
            model="school_class",
            operation="create",
            description="Create school class objects.",
        ),
        "read": Oauth2Scope(
            model="school_class", operation="read", description="Read school class objects."
        ),
        "update": Oauth2Scope(
            model="school_class",
            operation="update",
            description="Modify school class objects.",
        ),
        "delete": Oauth2Scope(
            model="school_class",
            operation="delete",
            description="Delete school class objects.",
        ),
    },
    "user": {
        "create": Oauth2Scope(
            model="user", operation="create", description="Create user objects.",
        ),
        "read": Oauth2Scope(
            model="user", operation="read", description="Read user objects."
        ),
        "update": Oauth2Scope(
            model="user", operation="update", description="Modify user objects.",
        ),
        "delete": Oauth2Scope(
            model="user", operation="delete", description="Delete user objects.",
        ),
    },
}
STATIC_FILES_PATH = Path("/kelvin/kelvin-api/static")
STATIC_FILE_CHANGELOG = STATIC_FILES_PATH / "changelog.html"
STATIC_FILE_README = STATIC_FILES_PATH / "readme.html"
TOKEN_SIGN_SECRET_FILE = APP_CONFIG_BASE_PATH / "tokens.secret"
TOKEN_HASH_ALGORITHM = "HS256"
UCRV_TOKEN_TTL = "ucsschool/kelvin/access_tokel_ttl"
UCS_SSL_CA_CERT = "/usr/local/share/ca-certificates/ucs.crt"
URL_KELVIN_BASE = "/ucsschool/kelvin"
URL_API_PREFIX = f"{URL_KELVIN_BASE}/v1"
URL_TOKEN_BASE = f"{URL_KELVIN_BASE}/token"
