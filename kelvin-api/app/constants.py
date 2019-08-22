from pathlib import Path


__version__ = "0.1.0"
API_USERS_GROUP_NAME = "kelvin-users"
APP_ID = "ucs-school-kelvin-api"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = Path(APP_BASE_PATH, "conf")
LOG_FILE_PATH = Path("/var/log/univention/kelvin-api/http.log")
MACHINE_PASSWORD_FILE = "/etc/machine.secret"
RPC_ADDR = "tcp://127.0.0.1:6789"
STATIC_FILE_CHANGELOG = "changelog.html"
STATIC_FILE_README = "readme.html"
TOKEN_SIGN_SECRET_FILE = Path(APP_CONFIG_BASE_PATH, "tokens.secret")
TOKEN_HASH_ALGORITHM = "HS256"
UCRV_TOKEN_TTL = "ucsschool/kelvin-api/access_tokel_ttl"
URL_KELVIN_BASE = "/kelvin"
URL_API_PREFIX = f"{URL_KELVIN_BASE}/api/v1"
URL_TOKEN_BASE = f"{URL_KELVIN_BASE}/api/token"
