.. :changelog:

.. The file can be read on the installed system at https://FQDN/ucsschool/kelvin/changelog

Changelog
---------

v1.2.0 (2020-10-??)
...................
* Improve user resource search speed: find all matching users with one lookup (Bug #51813).
* Add fallback for retrieving LDAP connection settings from UCR if environment variables are not available (Bug #51154).
* Add attribute ``kelvin_password_hashes`` to user resource. It allows overwriting the password hashes in the UCS LDAP with the ones delivered. Use only if you know what you're doing!

v1.1.2 (2020-08-11)
...................
* The OpenAPI schema of the UDM REST API has been restricted to authenticated users. The Kelvin API now uses the updated ``update_openapi_script``, passing credentials to update the OpenAPI client library (Bug #51072).
* The school class resource has been modified to accept class name containing only one character (Bug #51363).
* Setting and changing the ``password`` attribute has been fixed (Bug #51285).
* The UCS CA is now registered in the HTTP client certification verification backend to prevent SSL certification errors when communicating with the UDM REST API on the Docker host (Bug #51510).
* The ``school_admin`` role is now supported (Bug #51509).
* Update Docker image base to Alpine 3.12, updating Python to 3.8 (Bug #51768).

v1.1.1 (2020-06-15)
...................
* The validation of the ``name`` attribute of the ``SchoolClass`` resource has been fixed to allow short class names like ``1``.
* The ``password`` attribute of the ``User`` resource has been fixed.
* The signatures of the ``UserPyHook`` methods have been adapted to be able to ``await`` async methods.
* The UCS CA is now added to the ``certifi`` SSL certification store.
* Support for the ``school_admin`` role was added.


v1.1.0 (2020-04-15)
...................
* The UDM REST API Python Client library has been updated to version ``0.4.0``, so it can handle authorized access to the UDM REST API OpenAPI schema.

v1.0.1 (2020-02-17)
...................
* The ucsschool lib has been extended to allow for context types other than ``school`` in ``ucsschool_roles`` attribute of most resources.

v1.0.0 (2020-01-20)
...................
* Initial release.
