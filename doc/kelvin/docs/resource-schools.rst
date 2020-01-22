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

Currently the ``Schools`` resource does only support listing objects.
It does not yet support creating, modifying or deleting OUs.


Resource representation
-----------------------
The following JSON is an example Schools resource in the `UCS\@school Kelvin REST API`::

    {
        "administrative_servers": [],
        "class_share_file_server": "cn=dctest-01,cn=dc,cn=server,cn=computers,ou=test,dc=uni,dc=ven",
        "dc_name": null,
        "dc_name_administrative": null,
        "display_name": "Test School",
        "dn": "ou=test,dc=uni,dc=ven",
        "educational_servers": ["cn=dctest-01,cn=dc,cn=server,cn=computers,ou=test,dc=uni,dc=ven"],
        "home_share_file_server": "cn=dctest-01,cn=dc,cn=server,cn=computers,ou=test,dc=uni,dc=ven",
        "name": "test",
        "ucsschool_roles": ["school:school:test"],
        "url": "https://m66.uni.dtr/ucsschool/kelvin/v1/schools/test"
    }


.. csv-table:: Property description
   :header: "name", "value", "Description", "Notes"
   :widths: 8, 5, 50, 18
   :escape: '

    "dn", "string", "The DN of the OU in LDAP.", "read only"
    "name", "string", "The name of the school (technically: the name of the OU).", "read only"
    "url", "URL", "The URL of the role object in the UCS\@school Kelvin API.", "read only"
    "administrative_servers", "list", "List of DNs of servers for the administrative school network.", ""
    "class_share_file_server", "string", "DN of server with the class shares.", "if unset: the schools educational server DN"
    "dc_name", "string", "Hostname of the schools educational server.", ""
    "dc_name_administrative", "string", "Hostname of the schools administrative server.", ""
    "display_name", "string", "The name of the school (for views).", ""
    "educational_servers", "list", "List of DNs of servers for the educational school network.", ""
    "home_share_file_server", "string", "DN of server with the home shares.", "if unset: the schools educational server DN"
    "ucsschool_roles", "list", "List of roles the OU has. Format is ``ROLE:CONTEXT_TYPE:CONTEXT``, for example: ``['"'school:school:gym1'"']``.", "auto-managed by system, setting and changing discouraged"


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


.. _`UDM REST API`: https://docs.software-univention.de/developer-reference-4.4.html#udm:rest_api
