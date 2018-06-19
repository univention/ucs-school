File locations
==============

Configuration files
-------------------

Apache
~~~~~~
The Apache configuration file is ``/etc/apache2/sites-available/ucs-school-import-http-api.conf``.
As it is generated from a UCR template do not edit it directly, but only by setting relevant UCR variables (currently only ``ucsschool/import/http_api/wsgi_server_port``).

Django
~~~~~~
The Django configuration file is ``/etc/ucsschool-import/settings.py``.
As it is generated from a UCR template do not edit it directly, but only by setting relevant UCR variables ``ucsschool/import/http_api/...`` (currently only ``../ALLOWED_HOSTS``, ``../TIME_ZONE`` and ``../django_debug``, see `Django configuration reference <https://docs.djangoproject.com/en/1.10/ref/settings/>`_).
A secret key for cryptographic signing is stored in ``/etc/ucsschool-import/django_key.secret``.

Gunicorn
~~~~~~~~
The Gunicorn configuration file is ``/etc/gunicorn.d/ucs-school-import``.
As it is generated from a UCR template do not edit it directly, but only by setting relevant UCR variables ``ucsschool/import/http_api//wsgi_server_*`` (see `Gunicorn configuration reference <http://docs.gunicorn.org/en/19.6.0/settings.html>`_).

The code running in Gunicorn requires read-only LDAP-access. For that it uses an unprivileged simple authentication account. The credentials are read from ``/etc/ucsschool-import/ldap.secret``.

RabbitMQ
~~~~~~~~
The RabbitMQ configuration file is ``/etc/rabbitmq/rabbitmq.config``.
As it is generated from a UCR template do not edit it directly. Currently there are no modifiable settings. The credentials are stored in ``/etc/ucsschool-import/rabbitmq.secret``.

PostgreSQL
~~~~~~~~~~
The PostgreSQL configuration provided by ``univention-postgres`` in not touched. Only a user and database is created by the join script. The users password is stored in ``/etc/ucsschool-import/postgres.secret``.

Files read and written during import job (CSV, hooks, logfile, summary, new-users-passwords etc)
------------------------------------------------------------------------------------------------

All input and output of an import job (incl the logfiles) are located in ``/var/lib/ucs-school-import/jobs/<year>/<job id>/``.
Such a directory will for example include the following files and subdirectories:

* ``0_global_defaults.json``: Global configuration file used in import job. Copied from ``/usr/share/ucs-school-import/configs/``.
* ``1_global.json``: Custom configuration file used in import job. Copied from ``/var/lib/ucs-school-import/configs/``.
* ``2_user_import_defaults.json``: Default configuration file used in import job. Copied from ``/usr/share/ucs-school-import/configs/``.
* ``3_user_import.json``: Custom configuration file used in import job. Copied from ``/var/lib/ucs-school-import/configs/``.
* ``4_user_import_http-api.json`` : Default configuration file used in import job. Copied from ``/usr/share/ucs-school-import/configs/``.
* ``5_user_import_http-api.json`` : Custom configuration file used in import job. Copied from ``/var/lib/ucs-school-import/configs/``.
* ``6_gsmitte.json`` : Custom configuration file for OU ``gsmitte`` used in import job. Copied from ``/var/lib/ucs-school-import/configs/``.
* ``1528356738-10_teachers.csv``: Previously uploaded CSV input file.
* ``hooks/``: Shell hooks directory copied from ``/usr/share/ucs-school-import/hooks``.
* ``new_user_passwords.csv``: Passwords of new users created in import job, downloadable through HTTP-API and UMC module.
* ``pyhooks/``: Python hooks directory copied from ``/usr/share/ucs-school-import/hooks``.
* ``ucs-school-import.info``: Import job log file, severity ``info`` and above.
* ``ucs-school-import.log``: Import job log file, severity ``debug`` and above, downloadable through HTTP-API and UMC module.
* ``user_import_summary.csv``: Import job summary file, downloadable through HTTP-API and UMC module.
