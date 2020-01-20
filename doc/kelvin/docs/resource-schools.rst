Resource Schools
================

The ``Schools`` resource is represented in the LDAP tree as an ``OU``.

All UCS\@school objects exist relative to a ``OU`` and as such have a ``school`` attribute (except for ``School`` objects themselves).
Staff, students and teachers may attend or work at multiple schools.
So ``User`` objects have an additional ``schools`` attribute, that is a list of all schools a user belongs to.

Currently the ``Schools`` resource does only support listing objects.
It does not yet support creating, modifying or deleting OUs.

List / Search
-------------

Example ``curl`` command to retrieve the list of all schools (OUs)::

    $ curl -i -k -X GET "https://<fqdn>/ucsschool/kelvin/v1/schools/" \
        -H "accept: application/json"
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...."

The response headers will be::

    HTTP/1.1 200 OK
    Date: Mon, 20 Jan 2020 14:00:41 GMT
    Server: uvicorn
    content-length: 1957
    content-type: application/json
    Via: 1.1 <fqdn>

The response body will be::

    [
        {
            "administrative_servers": [],
            "class_share_file_server": "DEMOSCHOOL",
            "dc_name": null,
            "dc_name_administrative": null,
            "display_name": "Demo School",
            "dn": "ou=DEMOSCHOOL,dc=uni,dc=ven",
            "educational_servers": ["DEMOSCHOOL"],
            "home_share_file_server": "DEMOSCHOOL",
            "name": "DEMOSCHOOL",
            "ucsschool_roles": ["school:school:DEMOSCHOOL"],
            "url": "https://m66.uni.dtr/ucsschool/kelvin/v1/schools/DEMOSCHOOL"
        },
        ...
    ]

To search for schools with a name that starts with ``abc``, append ``?name=abc*`` to the school
resource. The search is case-insensitive. The URL would be: ``https://<fqdn>/ucsschool/kelvin/v1/schools/?name=abc%2A``

``name`` is currently the only attribute that can be used to search for OUs.


Retrieve
--------

Example ``curl`` command to retrieve a single school (OU)::

    $ curl -X GET "https://<fqdn>/ucsschool/kelvin/v1/schools/demoschool"\
        -H "accept: application/json" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...."

With the search being case-insensitive, this matches an OU named ``DEMOSCHOOL``.
The response body will be the first element of the list in the search example above.
