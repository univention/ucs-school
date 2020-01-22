Resource Roles
==============

The ``Roles`` resource represents the roles a school user can have.
Currently there are exactly three roles supported: ``staff``, ``student`` and ``teacher``.
A user has either one of those roles or the combination of ``staff`` and ``teacher``.

The resource objects have no direct representation in LDAP.
They are only required to classify user objects.

The item list of the ``Roles`` resource is hard coded.
It does only support listing objects.
It does not support creating, modifying or deleting roles.

Resource representation
-----------------------
The following JSON is an example Roles resource in the `UCS\@school Kelvin REST API`::

    {
        "display_name": "staff",
        "name": "staff",
        "url": "https://<fqdn>/ucsschool/kelvin/v1/roles/staff"
    }


.. csv-table:: Property description
   :header: "name", "value", "Description", "Notes"
   :widths: 8, 5, 50, 18
   :escape: '

    "display_name", "string", "The name of the role (for views).", "read only"
    "name", "string", "The name of the role (technically).", "read only"
    "url", "URL", "The URL of the role object in the UCS\@school Kelvin API.", "read only"


List / Search
-------------

Example ``curl`` command to retrieve the list of all roles::

    $ curl -i -k -X GET "https://<fqdn>/ucsschool/kelvin/v1/roles/" \
        -H "accept: application/json"
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...."

The response headers will be::

    HTTP/1.1 200 OK
    Date: Mon, 20 Jan 2020 14:21:00 GMT
    Server: uvicorn
    content-length: 334
    content-type: application/json
    Via: 1.1 <fqdn>

The response body will be::

    [
        {
            "display_name": "staff",
            "name": "staff",
            "url": "https://<fqdn>/ucsschool/kelvin/v1/roles/staff"
        },
        {
            "display_name": "student",
            "name": "student",
            "url": "https://<fqdn>/ucsschool/kelvin/v1/roles/student"
        },
        {
            "display_name": "teacher",
            "name": "teacher",
            "url": "https://<fqdn>/ucsschool/kelvin/v1/roles/teacher"
        }
    ]


Searching for roles (with ``?name=abc*`` or similar) is `not` supported.

Retrieve
--------

Example ``curl`` command to retrieve a single role::

    $ curl -X GET "https://<fqdn>/ucsschool/kelvin/v1/roles/student"\
        -H "accept: application/json" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...."

The queried role must exist, matching is case-sensitive.
The response body will be the second element of the list in the example above.
