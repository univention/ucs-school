Resource Schools
================

The ``Schools`` resource is represented in the LDAP tree as an ``OU``.

To list those LDAP objects run::

    $ univention-ldapsearch -LLL "objectClass=ucsschoolOrganizationalUnit"

UCS\@school uses the `UDM REST API`_ which in turn uses UDM to access LDAP.
UDM properties have different names than their associated LDAP attributes.
Their values may also differ.
To list the same UDM objects run::

    $ udm container/ou list --filter "objectClass=ucsschoolOrganizationalUnit"


All UCS\@school objects exist below an ``OU`` and have that OUs name as the ``school`` attributes value.
Staff, students and teachers may attend or work at multiple schools.
So ``User`` objects have an additional ``schools`` attribute, that is a list of all schools a user belongs to.

Currently the ``Schools`` resource does only support listing and creating objects.
It does not yet support modifying or deleting OUs.


Resource representation
-----------------------
The following JSON is an example Schools resource in the *UCS\@school Kelvin REST API*::

    {
        "dn": "ou=test,dc=uni,dc=ven",
        "url": "https://<fqdn>/ucsschool/kelvin/v1/schools/test",
        "ucsschool_roles": ["school:school:test"],
        "name": "test",
        "display_name": "Test School",
        "educational_servers": ["dctest-01"],
        "administrative_servers": [],
        "class_share_file_server": "dctest-01",
        "home_share_file_server": "dctest-01"
    }


.. csv-table:: Property description
   :header: "name", "value", "Description", "Notes"
   :widths: 8, 5, 50, 18
   :escape: '

    "dn", "string", "The DN of the OU in LDAP.", "read only"
    "url", "URL", "The URL of the role object in the UCS\@school Kelvin API.", "read only"
    "ucsschool_roles", "list", "List of roles the OU has. Format is ``ROLE:CONTEXT_TYPE:CONTEXT``, for example: ``['"'school:school:gym1'"']``.", "auto-managed by system, setting and changing discouraged"
    "name", "string", "The name of the school (technically: the name of the OU).", "read only"
    "display_name", "string", "The name of the school (for views).", ""
    "educational_servers", "list", "List of server host names for the educational school network.", "(*)"
    "administrative_servers", "list", "List of server host names for the administrative school network.", "(*)"
    "class_share_file_server", "string", "Host name of server with the class shares.", "if unset: the schools educational server, (*)"
    "home_share_file_server", "string", "Host name of server with the home shares.", "if unset: the schools educational server, (*)"

(*) **API CHANGE**: before version ``1.4.0`` this was a DN or list of DNs

List / Search
-------------

Example ``curl`` command to retrieve the list of all schools (OUs)::

    $ curl -i -k -X GET "https://<fqdn>/ucsschool/kelvin/v1/schools/" \
        -H "accept: application/json" \
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
            "dn": "ou=DEMOSCHOOL,dc=uni,dc=ven",
            "url": "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL",
            "name": "DEMOSCHOOL",
            "display_name": "Demo School",
            "educational_servers": ["dc-demoschool"],
            "administrative_servers": [],
            "class_share_file_server": "dc-demoschool",
            "home_share_file_server": "dc-demoschool"
        },
        ...
    ]

To search for schools with a name that starts with ``abc``, append ``?name=abc*`` to the school
resource. The search is case-insensitive. The URL would be: ``https://<fqdn>/ucsschool/kelvin/v1/schools/?name=abc%2A``

``name`` is currently the only attribute that can be used to search for OUs.


Retrieve
--------

Example ``curl`` command to retrieve a single school (OU)::

    $ curl -X GET "https://<fqdn>/ucsschool/kelvin/v1/schools/demoschool" \
        -H "accept: application/json" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...."

With the search being case-insensitive, this matches an OU named ``DEMOSCHOOL``.
The response body will be the first element of the list in the search example above.

Create
------

When creating a school, two attributes must be set:

* ``name``
* ``display_name``


As an example, with the following being the content of ``/tmp/create_ou.json``::

    {
        "name": "example",
        "display_name": "Example School"
    }


This ``curl`` command will create a school from the above data::

    $ curl -i -k -X POST "https://<fqdn>/ucsschool/kelvin/v1/schools/" \
        -H "accept: application/json" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...." \
        -d "$(</tmp/create_ou.json)"

Response headers::

    HTTP/1.1 201 Created
    Date: Mon, 26 Mar 2021 13:10:00 GMT
    Server: uvicorn
    content-length: 335
    content-type: application/json
    Via: 1.1 <fqdn>

Response body::

    {
        "dn": "ou=Example,dc=uni,dc=ven",
        "url": "https://<fqdn>/ucsschool/kelvin/v1/schools/Example",
        "ucsschool_roles": ["school:school:Example"],
        "name": "Example",
        "display_name": "Example School",
        "educational_servers": ["dcExample"],
        "administrative_servers": [],
        "class_share_file_server": "dcExample",
        "home_share_file_server": "dcExample"
    }


Modify / Move
-------------

Currently not supported.

Delete
------

Currently not supported.

.. _`UDM REST API`: https://docs.software-univention.de/developer-reference-4.4.html#udm:rest_api
