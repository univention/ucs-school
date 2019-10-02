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

Authentication
^^^^^^^^^^^^^^

To use the API, a `JSON Web Token (JWT) <https://en.wikipedia.org/wiki/JSON_Web_Token>`_ must be retrieved from ``https://FQDN/kelvin/api/token``. The token will be valid for a configurable amount of time (default 60 minutes), after which they must be renewed. To change the TTL, open the apps `app settings` in the app center. (When released as app - currently set the UCRV ``ucsschool/kelvin-api/access_tokel_ttl``).

Example ``curl`` command to retrieve a token::

    $ curl -i -k -X POST --data 'username=Administrator&password=s3cr3t' https://FQDN/kelvin/api/token

Only members of the group ``kelvin-users`` are allowed to access the HTTP-API.

The user ``Administrator`` is automatically added to this group for testing purposes. In production the regular admin user accounts should be used.


Examples
--------

curl...


File locations
--------------

Logfiles
^^^^^^^^

``/var/log/univention/ucs-school-kelvin`` is a volume mounted into the docker container, so it can be accessed from the host.

The directory contains the file ``http.log``, which is the log of the HTTP-API (both ASGI server and API application).


Changelog
---------

The changelog can be found `here <changelog>`_.


.. |license| image:: https://img.shields.io/badge/License-AGPL%20v3-orange.svg
    :alt: GNU AGPL V3 license
    :target: https://www.gnu.org/licenses/agpl-3.0
.. |python| image:: https://img.shields.io/badge/python-3.7+-blue.svg
    :alt: Python 3.6+
    :target: https://www.python.org/downloads/release/python-373/
.. |code style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style: black
    :target: https://github.com/python/black
