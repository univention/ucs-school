# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2018 Univention GmbH
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

"""
Django settings for the UCS@school import HTTP API.
"""

from __future__ import unicode_literals
import os
import re
import stat
import logging
from univention.config_registry import ConfigRegistry
from django.conf import global_settings


ucr = ConfigRegistry()
ucr.load()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF_DIR = '/etc/ucsschool-import'
LOG_DIR = '/var/log/univention/ucs-school-import'
IMPORT_USER_DATA_DIR = '/var/lib/ucs-school-import'
SHARE_DIR = '/usr/share/ucs-school-import-http-api'
VAR_LIB_DIR = '/var/lib/ucs-school-import-http-api'
SPOOL_DIR = '/var/spool/ucs-school-import'

POSTGRES_USER = 'importhttpapi'
POSTGRES_DB = 'importhttpapi'
POSTGRES_HOST = 'localhost'
POSTGRES_PORT = '5432'
RABBITMQ_VHOST = "importhttpapi"


with open(os.path.join(CONF_DIR, 'django_key.secret'), 'rb') as fp:
	SECRET_KEY = fp.read().strip()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = ucr.is_true('ucsschool/import/http_api/django_debug')

if 'ucsschool/import/http_api/ALLOWED_HOSTS' in ucr:
	ALLOWED_HOSTS = [h.strip() for h in ucr.get('ucsschool/import/http_api/ALLOWED_HOSTS').split(',')]
else:
	ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '{}.{}'.format(ucr['hostname'], ucr['domainname'])]
	for k, v in ucr.items():
		if re.match(r'^interfaces/.*/address$', k):
			ALLOWED_HOSTS.append(v)

INSTALLED_APPS = (
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'django_pam',
	'rest_framework',
	'djcelery',
	'django_filters',
	'ucsschool.http_api.import_api',
)

MIDDLEWARE_CLASSES = (
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'django.middleware.locale.LocaleMiddleware',
)

ROOT_URLCONF = 'ucsschool.http_api.app.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [os.path.join(SHARE_DIR, 'templates')],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'ucsschool.http_api.app.wsgi.application'

with open(os.path.join(CONF_DIR, 'postgres.secret'), 'rb') as fp:
	_postgres_pw = fp.read().strip()

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.postgresql_psycopg2',
		'NAME': POSTGRES_DB,
		'USER': POSTGRES_USER,
		'PASSWORD': _postgres_pw,
		'HOST': POSTGRES_HOST,
		'PORT': POSTGRES_PORT,
	}
}

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]

AUTHENTICATION_BACKENDS = ['django_pam.auth.backends.PAMBackend'] + list(global_settings.AUTHENTICATION_BACKENDS)

TIME_ZONE = ucr.get('ucsschool/import/http_api/TIME_ZONE')
if not TIME_ZONE:
	with open('/etc/timezone', 'rb') as fp:
		TIME_ZONE = fp.read().strip()
	if not re.match(r'\w+/\w+', TIME_ZONE):
		TIME_ZONE = 'Europe/Berlin'

LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = os.path.join(VAR_LIB_DIR, 'static')
STATIC_URL = '/{}/'.format(ucr.get('ucsschool/import/http_api/URL_path/static', 'ucsschool-static').strip().strip('/'))
MEDIA_ROOT = os.path.join(SPOOL_DIR, 'media')  # uploads go here
MEDIA_URL = '/{}/'.format(ucr.get('ucsschool/import/http_api/URL_path/media', 'ucsschool-media').strip().strip('/'))
FILE_UPLOAD_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR
FILE_UPLOAD_DIRECTORY_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_SECONDS = 0
if ucr.is_true('apache2/hsts'):
	SECURE_HSTS_SECONDS = int(ucr.get('apache2/hsts/max-age', '10886400'))
	SECURE_HSTS_INCLUDE_SUBDOMAINS = bool(ucr.is_true('apache2/hsts/includeSubDomains'))
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

# Django REST settings
REST_FRAMEWORK = {
	'DEFAULT_PERMISSION_CLASSES': [
		'rest_framework.permissions.IsAuthenticated',
	],
	'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
	'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
	'PAGE_SIZE': 100,
	'UPLOADED_FILES_USE_URL': False,
}


# Celery settings
with open(os.path.join(CONF_DIR, 'rabbitmq.secret'), 'rb') as fp:
	_celery_broker_credentials = fp.read().strip()

BROKER_URL = 'amqp://{}@localhost:5672/{}'.format(_celery_broker_credentials, RABBITMQ_VHOST)
CELERYD_TASK_LOG_FORMAT = '[%(asctime)s: %(levelname)-8s/%(processName)s] %(task_name)s[%(task_id)s] %(module)s.%(funcName)s:%(lineno)d: %(message)s'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_EVENT_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_ENABLE_UTC = True
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
CELERY_TASK_RESULT_EXPIRES = 0
CELERY_ROUTES = {
	'ucsschool.http_api.import_api.tasks.dry_run': {'queue': 'dryrun'},
	'ucsschool.http_api.import_api.tasks.import_users': {'queue': 'import'},
}
CELERY_TRACK_STARTED = True
CELERY_TIMEZONE = TIME_ZONE
CELERYD_HIJACK_ROOT_LOGGER = False
# CELERYD_LOG_FORMAT = '%(asctime)s %(levelname)-8s [%(processName)s] %(module)s.%(funcName)s:%(lineno)d  %(message)s'
CELERYD_MAX_TASKS_PER_CHILD = 1
# CELERYD_TASK_LOG_FORMAT = '%(asctime)s %(levelname)-8s [%(processName)s %(task_name)s(%(task_id)s)] %(module)s.%(funcName)s:%(lineno)d  %(message)s'


# import settings
UCSSCHOOL_IMPORT = {
	'logging': {
		'api_datefmt': '%Y-%m-%d %H:%M:%S',
		'api_format': '%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d  %(message)s',
		'api_level': logging.DEBUG if DEBUG else logging.INFO,
		'api_logfile': os.path.join(LOG_DIR, 'http_api.log'),
	},
	'import_jobs_basedir': os.path.join(IMPORT_USER_DATA_DIR, 'jobs'),
	'new_user_passwords_filename': 'new_user_passwords.csv',
	'user_import_summary_filename': 'user_import_summary.csv',
}
