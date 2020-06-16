.. :changelog:

.. The file can be read on the installed system at https://FQDN/ucsschool/kelvin/changelog

Changelog
---------

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
