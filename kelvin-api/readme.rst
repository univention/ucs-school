Kelvin API
==========

|python| |license| |code style|

.. This file can be read on the installed system at https://FQDN/kelvin/api/v1/readme
.. The changelog can be read on the installed system at https://FQDN/kelvin/api/v1/history


Installation
------------

In the UCS Appcenter search for `kelvin` or run on the command line::

    $ univention-app install ucs-school-kelvin-api

Configuration
-------------

* UCRV ``ucsschool/kelvin-api/access_tokel_ttl``
* ...

Explore API
-----------

Swagger / OpenAPI...
/kelvin/api/v1/openapi.json
/kelvin/api/v1/docs
/kelvin/api/v1/redoc

Authentication
^^^^^^^^^^^^^^

To use the API, a `JSON Web Token (JWT) <https://en.wikipedia.org/wiki/JSON_Web_Token>`_ must be retrieved from ``https://FQDN/kelvin/api/token``. The token will be valid for a configurable amount of time (default 60 minutes), after which they must be renewed. To change the TTL, open the apps `app settings` in the app center. (When released as app - currently set the UCRV ``ucsschool/kelvin-api/access_tokel_ttl``).

Example ``curl`` command to retrieve a token::

    $ curl -i -k -X POST \
        -H "Content-Type:application/x-www-form-urlencoded" \
        -d "username=Administrator" \
        -d "password=univention" \
        https://m66.uni.dtr/kelvin/api/token

Only members of the group ``kelvin-users`` are allowed to access the HTTP-API.

The user ``Administrator`` is automatically added to this group for testing purposes. In production the regular admin user accounts should be used.


Examples
--------

curl...


Known Issues
-------------

After adding an extended attribute, extended option or udm module an update of the openapi client is triggered.
But the udm rest api isn't automatically reloaded (bug 50253), which prevents the openapi update from getting the changes.

Update manually the openapi client manually if needed::

   systemctl restart univention-directory-manager-rest.service
   univention-app shell ucsschool-kelvin /bin/sh -c '. /kelvin/venv/bin/activate; update_openapi_client --generator java --jar /kelvin/openapi-generator/jar/openapi-generator-cli-*.jar --insecure $DOCKER_HOST_NAME'


File locations
--------------

Logfiles
^^^^^^^^

``/var/log/univention/ucs-school-kelvin`` is a volume mounted into the docker container, so it can be accessed from the host.

The directory contains the file ``http.log``, which is the log of the HTTP-API (both ASGI server and API application).

Configuration of user object management (import configuration)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``/var/lib/ucs-school-import/configs`` is a volume mounted into the docker container, so it can be accessed from the host.

The directory contains the file ``kelvin.json``, which is the top level configuration file for the UCS@school import code that runs inside the Docker container when user objects are managed.


Python hooks for user object management (import-user)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``/var/lib/ucs-school-import/kelvin-hooks`` is a volume mounted into the docker container, so it can be accessed from the host.

The directory content is scanned when the Kelvin API server starts.
If it contains hook classes that inherit from ``ucsschool.importer.utils.import_pyhook.ImportPyHook``, they are executed when users are managed through the Kelvin API.
The hooks are very similar to the Python hooks for the UCS@school import (see `UCS@school manual`_).
The differences are:

* Python 3.7 only
* Only three types of hooks are executed: ``UserPyHook``, ``FormatPyHook`` and ``ConfigPyHook`` (all located in modules in the ``ucsschool.importer.utils`` package).
* ``self.dry_run`` is always ``False``
* ``self.lo`` is always a LDAP connection with write permissions (``cn=admin``) as ``dry_run`` is always ``False``
* ``FormatPyHook`` and ``ConfigPyHook`` are the same as in the UCS@school import, but a ``UserPyHook`` hook instance has an additional member ``self.udm``.

``self.udm`` is an instance of ``udm_rest_client.udm.UDM`` (see `Python UDM REST Client`_).
It can be used to comfortably query the UDM REST API running on the DC master.
When using the UCS@school lib or import, it must be used in most places that ``self.lo`` was used before.

**Important**: When calling methods of ucsschool objects (e.g. ``ImportUser``, ``SchoolClass`` etc.) ``self.udm`` must be used instead of ``self.lo`` and those methods may have to be used with ``await``. Thus hooks methods will be ``async``.
For example::

    async def post_create(self, user: ImportUser) -> None:
        user.firstname = "Sam"
        awaituser.modify(self.udm)

        udm_user_obj = await user.get_udm_object(self.udm)
        udm_user_obj["foo"] = "bar"
        await udm_user_obj.save()  # UDM REST Client object: "save", not "modify"


Changelog
---------

The changelog can be found `here <changelog>`_.


.. |license| image:: https://img.shields.io/badge/License-AGPL%20v3-orange.svg
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0
.. |python| image:: https://img.shields.io/badge/python-3.6+-blue.svg
    :alt: Python 3.6+
    :target: https://www.python.org/downloads/release/python-373/
.. |code style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style: black
    :target: https://github.com/python/black
.. _`UCS@school manual`: https://docs.software-univention.de/ucsschool-import-handbuch-4.4.html#extending:hooks
.. _`Python UDM REST Client`: https://udm-rest-client.readthedocs.io/en/latest/