from pathlib import Path

API_USERS_GROUP_NAME = "ucsschool-kelvin-admins"
APP_ID = "ucsschool-kelvin"
APP_BASE_PATH = Path("/var/lib/univention-appcenter/apps", APP_ID)
APP_CONFIG_BASE_PATH = Path(APP_BASE_PATH, "conf")
CN_ADMIN_PASSWORD_FILE = APP_CONFIG_BASE_PATH / "cn_admin.secret"
LOG_FILE_PATH = Path("/var/log/univention/ucs-school-kelvin/http.log")
MACHINE_PASSWORD_FILE = "/etc/machine.secret"
STATIC_FILE_CHANGELOG = "changelog.html"
STATIC_FILE_README = "readme.html"
TOKEN_SIGN_SECRET_FILE = Path(APP_CONFIG_BASE_PATH, "tokens.secret")
TOKEN_HASH_ALGORITHM = "HS256"
UCRV_TOKEN_TTL = "ucsschool/kelvin/access_tokel_ttl"
UCS_SSL_CA_CERT = "/usr/local/share/ca-certificates/ucs.crt"
URL_KELVIN_BASE = "/kelvin"
URL_API_PREFIX = f"{URL_KELVIN_BASE}/api/v1"
URL_TOKEN_BASE = f"{URL_KELVIN_BASE}/api/token"
