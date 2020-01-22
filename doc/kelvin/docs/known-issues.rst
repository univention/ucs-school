Known Issues
============

Rebuilding the UDM REST API Client
----------------------------------
The `UCS\@school Kelvin REST API` server connects to the `UDM REST API`_ server to execute modifications of the LDAP database.
So the UCS\@school Kelvin REST API server is itself a `client` of the UDM REST API.
The `Python UDM REST API Client`_ library is used for communication with the UDM REST API.

The UDM REST API does also provide an OpenAPI schema.
A part of the Python UDM REST API Client library is auto-generated from it using the `OpenAPI Generator` mentioned above.

.. warning::
    Whenever a new UDM module, extended option or extended attribute is installed, the `OpenAPI client` library used by the Python UDM REST API Client library **must** be rebuild to be able to access the new module/attribute.

Although the `OpenAPI client` library rebuild is automatically triggered, because of `Bug #50253`_ the UDM REST API server will not have been reloaded.
This will prevent the changes to be incorporated into the UDM REST client of the UCS\@school Kelvin REST API server.

**It is thus currently necessary to rebuild the OpenAPI client manually.**

This can be done with the following commands::

    $ systemctl restart univention-directory-manager-rest.service
    $ univention-app shell ucsschool-kelvin-rest-api /bin/sh -c '. /kelvin/venv/bin/activate; update_openapi_client --generator java --jar /kelvin/openapi-generator/jar/openapi-generator-cli-*.jar --insecure $DOCKER_HOST_NAME'


No pagination
-------------
Pagination of resource collections has not yet been implemented.
When it is, there will be ``<Link>`` entries in the response `headers`.
The format of the JSON response in the `body will not change`.

.. _`UDM REST API`: https://docs.software-univention.de/developer-reference-4.4.html#udm:rest_api
.. _`Python UDM REST API Client`: https://github.com/univention/python-udm-rest-api-client
.. _`Bug #50253`: http://forge.univention.org/bugzilla/show_bug.cgi?id=50253
