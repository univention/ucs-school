Installation and configuration
==============================

Installation
------------

The app *UCS\@school Kelvin REST API* must be installed on the DC master or DC backup.
This can be done either through the UMC module *Univention App Center* or on the command line::

    $ univention-app install ucsschool-kelvin-rest-api

The join script ``50ucsschool-kelvin-rest-api.inst`` should run automatically.
To verify if it succeeded, open the *Domain join* UMC module or run::

    $ univention-check-join-status

If it hasn't run, start it in the UMC module or execute::

    $ univention-run-join-scripts

If problems occur during installation or join script execution, relevant log files are:

#. ``/var/log/univention/appcenter.log``
#. ``/var/log/univention/join.log``

Configuration
-------------

The *UCS\@school Kelvin REST API* can be used out of the box, but there are various parameters that can be configured:

Token validity
^^^^^^^^^^^^^^

All HTTP requests to resources must carry a valid JWT token. The number of minutes a token is valid can be configured. The default is ``60``. The value can be changed through the *app settings* of the *UCS\@school Kelvin REST API* app in the *Univention App Center* UMC module.

Log level
^^^^^^^^^

The minimum severity for log messages written to ``/var/log/univention/ucsschool-kelvin-rest-api/http.log`` can be configured. The default is ``INFO``. The value can be changed through the *app settings* of the *UCS\@school Kelvin REST API* app in the *Univention App Center* UMC module.

Backup count of validation logging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The UCR variable ``ucsschool/validation/logging/backupcount`` sets the amount of copies of the log file ``ucs-school-validation.log``, which should be kept in rotation. The default is ``60``. The host's UCR-V is copied into the Docker container during the join script.
To change it for the *UCS\@school Kelvin REST API*, it has to be modified inside the Docker container.

Configuration of user object management (import configuration)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The directory ``/var/lib/ucs-school-import/configs`` is mounted as a *volume* into the Docker container where the *UCS\@school Kelvin REST API* runs. This makes it accessible from the host as well as from inside the container.

The directory contains the file ``kelvin.json``, which is the top level configuration file for the UCS\@school import code, executed when ``user`` objects are managed.
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

Python hooks for user object management (import hooks)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The directory ``/var/lib/ucs-school-import/kelvin-hooks`` is mounted as a *volume* into the Docker container, so it can be accessed from the host. The directory content is scanned when the Kelvin API server starts.
If it contains classes that inherit from ``ucsschool.importer.utils.import_pyhook.ImportPyHook``, they are executed when users are managed through the Kelvin API.
The hooks are very similar to the Python hooks for the UCS\@school import (see `Handbuch zur CLI-Import-Schnittstelle`_).
The differences are:

* Python 3.7 only
* Only three types of hooks are executed: ``UserPyHook``, ``FormatPyHook`` and ``ConfigPyHook`` (all located in modules in the ``ucsschool.importer.utils`` package).
* ``self.dry_run`` is always ``False``
* ``self.lo`` is always a LDAP connection with write permissions (``cn=admin``) as ``dry_run`` is always ``False``
* ``FormatPyHook`` and ``ConfigPyHook`` are the same as in the UCS\@school import, but a ``UserPyHook`` hook instance has an additional member ``self.udm``.

``self.udm`` is an instance of ``udm_rest_client.udm.UDM`` (see `Python UDM REST Client`_).
It can be used to comfortably query the UDM REST API running on the DC master.
When using the UCS\@school lib or import, it must be used in most places that ``self.lo`` was used before.

**Important**: When calling methods of ucsschool objects (e.g. ``ImportUser``, ``SchoolClass`` etc.) ``self.udm`` must be used instead of ``self.lo`` and those methods may have to be used with ``await``. Thus hooks methods will be ``async``.
For example::

    async def post_create(self, user: ImportUser) -> None:
        user.firstname = "Sam"
        awaituser.modify(self.udm)

        udm_user_obj = await user.get_udm_object(self.udm)
        udm_user_obj["foo"] = "bar"
        await udm_user_obj.save()  # UDM REST Client object: "save", not "modify"


File locations
--------------

Logfiles
^^^^^^^^

``/var/log/univention/ucsschool-kelvin-rest-api`` is a volume mounted into the docker container, so it can be accessed from the host.
The directory contains the file ``http.log``, which is the log of the HTTP-API (both ASGI server and API application)
and the file ``ucs-school-validation.log``, which is used to write sensitive information during the UCS\@school validation.

User object (import) configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``/var/lib/ucs-school-import/configs`` is a volume mounted into the docker container, so it can be accessed from the host.
The directory contains the file ``kelvin.json``, which is the top level configuration file for the UCS\@school import code that is executed as part of the *UCS\@school Kelvin REST API* that runs inside the Docker container when user objects are managed.


Python hooks for user management
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``/var/lib/ucs-school-import/kelvin-hooks`` is a volume mounted into the docker container, so it can be accessed from the host.
Its purpose is explained above in chapter `Python hooks for user object management (import hooks)`_.


.. _`Handbuch zur CLI-Import-Schnittstelle`: https://docs.software-univention.de/ucsschool-import-handbuch-4.4.html
.. _`Python UDM REST Client`: https://udm-rest-client.readthedocs.io/en/latest/
