Authentication and authorization
================================

Authentication
--------------

To use the API, a `JSON Web Token (JWT)`_ must be retrieved from ``https://<fqdn>/ucsschool/kelvin/token``.
The token will be valid for a configurable amount of time (default 60 minutes), after which it must be renewed.
To change the value see chapter :ref:`Token validity`.

The time a token is valid is stored inside the JWT token in the ``exp`` attribute.

Example ``curl`` command to retrieve a token::

    $ curl -i -k -X POST https://<fqdn>/ucsschool/kelvin/token \
        -H "Content-Type:application/x-www-form-urlencoded" \
        -d "username=Administrator" \
        -d "password=s3cr3t"

The response headers will be::

    HTTP/1.1 200 OK
    Date: Mon, 20 Jan 2020 10:32:17 GMT
    Server: uvicorn
    content-length: 176
    content-type: application/json
    Via: 1.1 <fqdn>

The response body will be::

    {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUz...",
        "token_type": "bearer"
    }

*Hint:* to get a JSON response pretty printed omit the ``-i`` in the ``curl`` command and pipe the response through a JSON formatter::

    $ curl -k -X POST https://<fqdn>/ucsschool/kelvin/token \
        -H "Content-Type:application/x-www-form-urlencoded" \
        -d "username=Administrator" \
        -d "password=s3cr3t" | python -m json.tool

Authorization
-------------

Only members of the group ``ucsschool-kelvin-rest-api-admins`` are allowed to access the API.

The user ``Administrator`` is automatically added to this group for testing purposes.
In production a regular admin user account or a dedicated service account should be used.

Irrespective of the actually authenticated user, all operations will be executed using the ``cn=admin`` LDAP account.


.. _`JSON Web Token (JWT)`: https://en.wikipedia.org/wiki/JSON_Web_Token
