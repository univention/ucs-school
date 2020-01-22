Installation and configuration
==============================

Installation
------------

The app `UCS\@school Kelvin REST API` *must* be installed on the DC master or DC backup.
This can be done either through the UMC module `Univention App Center` or on the command line::

    $ univention-app install ucsschool-kelvin-rest-api

The join script ``50ucsschool-kelvin-rest-api.inst`` should run automatically.
To verify if it succeeded, open the `Domain join` UMC module or run::

    $ univention-check-join-status

If it hasn't run, start it in the UMC module or execute::

    $ univention-run-join-scripts

If problems occur during installation or join script execution, relevant log files are:

#. ``/var/log/univention/appcenter.log``
#. ``/var/log/univention/join.log``

Configuration
-------------

The `UCS\@school Kelvin REST API` can be used out of the box, but there are various parameters that can be configured:

Token validity
^^^^^^^^^^^^^^

All HTTP requests to resources must carry a valid JWT token. The number of minutes a token is valid can be configured. The default is ``60``. The value can be changed through the `app settings` of the `UCS\@school Kelvin REST API` app in the `Univention App Center` UMC module.

Log level
^^^^^^^^^

The minimum severity for log messages written to ``/var/log/univention/ucsschool-kelvin-rest-api/http.log`` can be configured. The default is ``INFO``. The value can be changed through the `app settings` of the `UCS\@school Kelvin REST API` app in the `Univention App Center` UMC module.

Configuration of user object management (import configuration)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The directory ``/var/lib/ucs-school-import/configs`` is mounted as a `volume` into the Docker container where the `UCS\@school Kelvin REST API` runs. This makes it accessible from the host as well as from inside the container.

The directory contains the file ``kelvin.json``, which is the top level configuration file for the UCS\@school import code, executed when `user` objects are managed.
Documentation for the UCS\@school import configuration is available only in german in the `Handbuch zur CLI-Import-Schnittstelle`_.

Additionally to the usual import configuration options, there is now a configuration key ``mapped_udm_properties``.
It points to a list of UDM properties that should show up - and be modifiable - in the user resources ``udm_properties`` attribute.
For example::

    {
        "mapped_udm_properties": [
            "description",
            "gidNumber",
            "employeeType",
            "organisation",
            "phone",
            "title",
            "uidNumber"
        ]
    }

Python hooks for user object management (import-user)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The directory ``/var/lib/ucs-school-import/kelvin-hooks`` is mounted as a `volume` into the Docker container, so it can be accessed from the host. The directory content is scanned when the Kelvin API server starts.
If it contains classes that inherit from ``ucsschool.importer.utils.import_pyhook.ImportPyHook``, they are executed when users are managed through the Kelvin API.
The hooks are very similar to the Python hooks for the UCS\@school import (see `Handbuch zur CLI-Import-Schnittstelle`_).
The differences are explained in chapter **TODO**.


.. _`Handbuch zur CLI-Import-Schnittstelle`: https://docs.software-univention.de/ucsschool-import-handbuch-4.4.html
