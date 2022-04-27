.. :changelog:

.. The file can be read on the installed system at https://FQDN/ucsschool/kelvin/changelog

Changelog
---------

v1.5.4 (2022-04-27)
.........
* A new App Setting was added to configure the amount CPU cores utilized by the UCS@school Kelvin REST API (Bug #54575).
* It is now possible to define multiple schools for users via PATCH and PUT requests (Bug #54481, Bug #54690).

v1.5.3 (2022-02-08)
...................
* Fixed token requests with authorized user and wrong password leading to ``HTTP 500`` (Bug #54431).
* The user get route now uses the correct filter when searching for UDM mapped properties (Bug #54474).

v1.5.2 (2022-01-07)
...................
* The Kelvin API can now be installed on servers with the role DC Primary and DC Backup (Bug #54310).

v1.5.1 (2021-11-30)
...................
* The Open Policy Agent component was added to components documentation (Bug #53960).
* The log output of the Open Policy Agent is now written to ``/var/log/univention/ucsschool-kelvin-rest-api/opa.log`` (Bug #53961).
* The test suite for the ``ucsschool.lib`` component was improved (Bug #53962).
* Username generation counter can now be raised above 100 (Bug #53987).
* The ``no_proxy`` environment variable is now honored by the Kelvin REST API when accessing the UDM REST API (Bug #54066).
* The user resource now has an ``expiration_date`` attribute, which can be used to set the account expiration date. A user won't be able to login from that date on (Bug #54126).

v1.5.0 (2021-09-10)
...................
* Unixhomes are now set correctly for users. (Bug #52926)
* The Kelvin API now supports udm properties on all Kelvin resources except roles. (Bug #53744)

v1.4.4 (2021-06-29)
...................
* The Kelvin API now supports UDM REST APIs using certificates, which are not signed by the UCS-CA. (Bug #52766)
* The UCS@school object validation now validate groups, schools and roles case-insensitive. (Bug #53044)

v1.4.3 (2021-06-16)
...................
* A security error was fixed, that allowed the unrestricted use of the Kelvin API with unsigned authentication tokens.
  Please update as fast as possible (Bug #53454)!

v1.4.2 (2021-05-26)
...................
* Support for hooks for objekts managed by classes from the package ``ucsschool.lib.models`` was added. See manual section `Python hooks for pre- and post-object-modification actions <https://docs.software-univention.de/ucsschool-kelvin-rest-api/installation-configuration.html#python-hooks-for-pre-and-post-object-modification-actions>`_ for details (Bug #49557).
* An error when creating usernames with templates was fixed (Bug #52925).

v1.4.1 (2021-05-03)
...................
* No error message is logged anymore after the deletion of an object (Bug #52896).
* Repeated restarts of the Kelvin server have been fixed.

v1.4.0 (2021-04-20)
...................
* The FastAPI framework has been updated to version ``0.63.0``.
* Open Policy Agent was added for access control and implemented partially for the user resource.
* The Kelvin API now supports creating schools.

v1.3.0 (2021-02-18)
...................
* It is now possible to change the roles of users. See manual section `Changing a users roles <https://docs.software-univention.de/ucsschool-kelvin-rest-api/resource-users.html#changing-a-users-roles>`_ for details (Bug #52659).
* Validation errors when reading malformed user objects from LDAP now produce more helpful error messages (Bug #52368).
* UCS@school user and group objects are now validated before usage, when loading them from LDAP. See manual sections `Resources <https://docs.software-univention.de/ucsschool-kelvin-rest-api/resources.html#resources>`_ and `Backup count of validation logging <https://docs.software-univention.de/ucsschool-kelvin-rest-api/installation-configuration.html#backup-count-of-validation-logging>`_ for details (Bug #52309).
* A bug setting the properties ``profilepath`` and ``sambahome`` to empty values when creating users has been fixed (Bug #52668).

v1.2.0 (2020-11-12)
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
