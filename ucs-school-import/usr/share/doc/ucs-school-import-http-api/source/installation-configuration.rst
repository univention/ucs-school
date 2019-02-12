Installation and configuration
==============================

Backend installation
--------------------

The backend *must* be installed on the DC master::

	$ univention-install ucs-school-import-http-api

The join script ``40ucs-school-import-http-api.inst`` must be run.

This will have installed and configured five system services:

* apache2 (adding the ``ucs-school-import-http-api`` site)
* ucs-school-import-http-api (Gunicorn instance: a Python application server)
* postgresql (SQL server)
* rabbitmq-server (message queueing system)
* celery-worker-ucsschool-import (worker process pool)

UMC frontend installation
-------------------------

Conceptually the UMC module can be installed on all UCS roles.
But in its current implementation it *must* be installed on the DC master::

	$ univention-install ucs-school-umc-import

Configuration
-------------

The configuration of the HTTP-API import is the same as for the command line variant: it reads JSON files in the following order:

1. ``/usr/share/ucs-school-import/configs/global_defaults.json``
2. ``/var/lib/ucs-school-import/configs/global.json``
3. ``/usr/share/ucs-school-import/configs/user_import_defaults.json``
4. ``/var/lib/ucs-school-import/configs/user_import.json``

*Additionally* it will look for a OU-specific configuration file (``$OU`` being the OU of current import): ``/var/lib/ucs-school-import/configs/$OU.json``.

Being the configuration file that is read last, it overwrites settings from previously read configuration files.

To use the HTTP-API copy the JSON file that contains the required configuration to its place::

	$ cp /usr/share/ucs-school-import/configs/user_import_http-api.json \
	    /var/lib/ucs-school-import/configs/user_import.json

Edit the file to your needs.

OU-specific configuration files should contain only the differences to ``user_import_http-api.json``.
