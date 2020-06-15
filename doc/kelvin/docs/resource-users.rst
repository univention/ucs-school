Resource Users
==============

The ``Users`` resource is represented in the LDAP tree as user objects.

To list those LDAP objects run::

    $ FILTER='(|(objectClass=ucsschoolStaff)(objectClass=ucsschoolStudent)(objectClass=ucsschoolTeacher))'
    $ univention-ldapsearch -LLL "$FILTER"

UCS\@school uses the `UDM REST API`_ which in turn uses UDM to access LDAP.
UDM properties have different names than their associated LDAP attributes.
Their values may also differ.
To list the same UDM objects run::

    $ FILTER='(|(objectClass=ucsschoolStaff)(objectClass=ucsschoolStudent)(objectClass=ucsschoolTeacher))'
    $ udm users/user list --filter "$FILTER"

Resource representation
-----------------------
The following JSON is an example User resource in the *UCS\@school Kelvin REST API*::

    {
        "dn": "uid=demo_student,cn=schueler,cn=users,ou=DEMOSCHOOL,dc=uni,dc=ven",
        "url": "https://<fqdn>/ucsschool/kelvin/v1/users/demo_student",
        "ucsschool_roles": ["student:school:DEMOSCHOOL", "student:school:DEMOSCHOOL2"],
        "name": "demo_student",
        "school": "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL",
        "firstname": "Demo",
        "lastname": "Student",
        "birthday": "2003-10-24",
        "disabled": false,
        "email": "demo_student@uni.ven",
        "record_uid": "demo_student12",
        "roles": ["https://<fqdn>/ucsschool/kelvin/v1/roles/student"],
        "schools": [
            "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL",
            "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL2"
        ],
        "school_classes": {
            "DEMOSCHOOL": ["Democlass"],
            "DEMOSCHOOL2": ["demoklasse2"]
        },
        "source_uid": "Kelvin",
        "udm_properties": {
            "description": "An example user attending two school.",
            "gidNumber": 5023,
            "employeeType": null,
            "organisation": null,
            "phone": ["+49 177 3578031", "+49 241 3456232"],
            "title": null,
            "uidNumber": 2007
        }
    }


.. csv-table:: Attribute description
   :header: "name", "value", "Description", "Notes"
   :widths: 8, 5, 50, 18
   :escape: '

    "dn", "string", "The DN of the user in LDAP.", "read only"
    "name", "string", "The users username.", ""
    "url", "URL", "The URL of the user object in the UCS\@school Kelvin API.", "read only"
    "firstname", "string", "The users given name.", ""
    "lastname", "string", "The users family name.", ""
    "birthday", "date", "The users birthday in ISO 8601 format: ``YYYY-MM-DD``.", ""
    "disabled", "boolean", "Whether the user should be deactivated.", ""
    "email", "string", "The users email address (``mailPrimaryAddress``), used only when the emails domain is hosted on UCS, not to be confused with the *contact* attribute ``e-mail``.", ""
    "roles", "list", "The users UCS\@school roles. A list of URLs in the ``roles`` resource.", "read only, but required when creating"
    "school", "string", "School (OU) the user belongs to. A URL in the ``schools`` resource.", "required for creation when ``schools`` is not set"
    "schools", "list", "List of schools (OUs) the user belongs to. A list of URLs in the ``schools`` resource.", "required for creation when ``school`` is not set"
    "school_classes", "nested object", "School classes the user is a member of. A mapping from school names to class names, for example: ``{'"'school1'"': ['"'class1'"', '"'class2'"'], '"'school2'"': ['"'class3'"']}``.", "The schools must also be listed (as URLs) in the ``schools`` attribute."
    "record_uid", "string", "Unique identifier of the user in the upstream database the user was imported from. Used in combination with ``source_uid`` by the UCS\@school import to uniquely identify users in both LDAP and upstream databases.", "changing is strongly discouraged"
    "source_uid", "string", "Identifier of the upstream database the user was imported from. Defaults to ``Kelvin`` if unset.", "changing is strongly discouraged"
    "ucsschool_roles", "list", "List of roles the user has in to each school. Format is ``ROLE:CONTEXT_TYPE:CONTEXT``, for example: ``['"'teacher:school:gym1'"', '"'school_admin:school:school2'"']``.", "auto-managed by system, setting and changing discouraged"
    "udm_properties", "nested object", "Object with UDM properties. For example: ``{'"'street'"': '"'Luise Av.'"', '"'phone'"': ['"'+49 30 321654987'"', '"'123 456 789'"']}``", "Must be configured, see below."

The ``password`` attribute is not listed, because it cannot be retrieved, it can only be *set* when creating or modifying a user.
UCS systems never store or send clear text passwords.

school[s]
^^^^^^^^^
The Users resource has a ``school`` attribute whose primary meaning is the position of its LDAP object in the LDAP tree.
More important is its ``schools`` attribute.
It is the list of schools that students are enrolled in or where staff and teachers work.

When creating/changing a user and sending only a value for ``school``, ``schools`` will be a list of that one item.

When creating a user and only ``schools`` is sent, ``school`` will automatically be chosen as the alphabetically first of the list.
When changing a user, the user object will stay in its OU, if it is the ``schools`` list, regardless of alphabetical order.

When both ``school`` and ``schools`` are used, the value of ``school`` must be in the list of values in ``schools``.

school_classes
^^^^^^^^^^^^^^
All school names in ``school_classes`` must exist (as URLs) in ``schools``.

udm_properties
^^^^^^^^^^^^^^
The attribute ``udm_properties`` is an object that can contain arbitrary UDM properties.
It must be configured in the file ``/var/lib/ucs-school-import/configs/kelvin.json``, see :ref:`Configuration of user object management (import configuration)`.


List / Search
-------------
Example ``curl`` command to retrieve the list of all users::

    $ curl -i -k -X GET "https://<fqdn>/ucsschool/kelvin/v1/users/" \
        -H "accept: application/json"
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...."

The response headers will be::

    HTTP/1.1 200 OK
    Date: Mon, 20 Jan 2020 15:11:14 GMT
    Server: uvicorn
    content-length: 43274
    content-type: application/json
    Via: 1.1 <fqdn>

The response body will be::

    [
        {
            "dn": "uid=demo_admin,cn=lehrer,cn=users,ou=DEMOSCHOOL,dc=uni,dc=ven",
            "url": "https://<fqdn>/ucsschool/kelvin/v1/users/demo_admin",
            "ucsschool_roles": ["teacher:school:DEMOSCHOOL"],
            "name": "demo_admin",
            "school": "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL",
            "firstname": "Demo",
            "lastname": "Admin",
            "birthday": null,
            "disabled": false,
            "email": null,
            "record_uid": null,
            "roles": ["https://<fqdn>/ucsschool/kelvin/v1/roles/teacher"],
            "schools": ["https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL"],
            "school_classes": {},
            "source_uid": null,
            "udm_properties": {}
        },
        ...
    ]

To search for users with usernames that contain ``Brian``, append ``?name=*Brian*`` to the school
resource. The search is case-insensitive. The URL would be: ``https://<fqdn>/ucsschool/kelvin/v1/users/?name=%2ABrian%2A``

The Users resource supports searching for all attributes and to combine those.
To search for users that are both ``staff`` and ``teacher`` with usernames that start with ``demo``, birthday on the 3rd of february, have a lastname that ends with ``sam`` and are enrolled in school ``demoschool``, the URL is: ``https://<fqdn>/ucsschool/kelvin/v1/users/?school=demoschool&name=demo%2A&birthday=2001-02-03&lastname=%2Asam&roles=staff&roles=teacher``

The user in the example response is working in two schools as both staff and teacher::

    [
        {
            "dn": "uid=test.staff.teach,cn=lehrer und mitarbeiter,cn=users,ou=test,dc=uni,dc=ven",
            "url": "https://<fqdn>/ucsschool/kelvin/v1/users/test.staff.teach",
            "ucsschool_roles": [
                "staff:school:test",
                "teacher:school:test",
                "staff:school:other",
                "teacher:school:other"
            ],
            "name": "test.staff.teach",
            "school": "https://<fqdn>/ucsschool/kelvin/v1/schools/test",
            "firstname": "staffer",
            "lastname": "teach",
            "birthday": "1988-03-18",
            "disabled": false,
            "email": "test.staff.teach@uni.dtr",
            "record_uid": "test.staff.teach12",
            "roles": [
                "https://<fqdn>/ucsschool/kelvin/v1/roles/staff",
                "https://<fqdn>/ucsschool/kelvin/v1/roles/teacher"
            ],
            "schools": [
                "https://<fqdn>/ucsschool/kelvin/v1/schools/test",
                "https://<fqdn>/ucsschool/kelvin/v1/schools/other"
            ],
            "school_classes": {
                "test": ["testclass", "testclass2"],
                "other": ["otherklasse", "otherklasse2"]
            },
            "source_uid": "TESTID",
            "udm_properties": {
                "description": "Working at two schools.",
                "gidNumber": 9319,
                "employeeType": "Lehrer und Mitarbeiter",
                "organisation": "School board",
                "phone": ["+123-456-789", "0321-456-987"],
                "title": "Mr.",
                "uidNumber": 12503
            }
        },
        ...
    ]


Retrieve
--------
Example ``curl`` command to retrieve a single user object::

    $ curl -k -X GET "https://<fqdn>/ucsschool/kelvin/v1/users/demo_staff" \
        -H "accept: application/json" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...." | python -m json.tool

With the search being case-insensitive, the URL could also have ended in ``DeMo_StAfF``.
The response body will be similar to the following (shortened)::

    {
        "dn": "uid=demo_staff,cn=mitarbeiter,cn=users,ou=DEMOSCHOOL,dc=uni,dc=ven",
        "url": "https://<fqdn>/ucsschool/kelvin/v1/users/demo_staff",
        "ucsschool_roles": ["staff:school:DEMOSCHOOL"],
        "name": "demo_staff",
        ...
    }

Create
------
When creating a user, a number of attributes must be set, unless formatted from a template (see *Handbuch zur CLI-Import-Schnittstelle*, section `Formatierungsschema`_):

* ``name``
* ``firstname``
* ``lastname``
* ``record_uid``
* ``roles``
* ``school`` or ``schools`` (or both)
* ``source_uid``

As an example, with the following being the content of ``/tmp/create_user.json``::

    {
        "name": "bob",
        "school": "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL",
        "firstname": "Bob",
        "lastname": "Marley",
        "birthday": "1945-02-06",
        "disabled": true,
        "email": null,
        "record_uid": "bob23",
        "password": "s3cr3t.s3cr3t.s3cr3t",
        "roles": ["https://<fqdn>/ucsschool/kelvin/v1/roles/teacher"],
        "schools": ["https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL"],
        "source_uid": "Reggae DB",
        "udm_properties": {
            "title": "Mr."
        }
    }

This ``curl`` command will create a user from the above data::

    $ curl -i -k -X POST "https://<fqdn>/ucsschool/kelvin/v1/users/" \
        -H "accept: application/json" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...." \
        -d "$(</tmp/create_user.json)"

Response headers::

    HTTP/1.1 201 Created
    Date: Mon, 20 Jan 2020 16:24:33 GMT
    Server: uvicorn
    content-length: 714
    content-type: application/json
    Via: 1.1 <fqdn>

Response body::

    {
        "dn": "uid=bob,cn=lehrer,cn=users,ou=DEMOSCHOOL,dc=uni,dc=ven",
        "url": "https://<fqdn>/ucsschool/kelvin/v1/users/bob",
        "ucsschool_roles": ["teacher:school:DEMOSCHOOL"],
        "name": "bob",
        "school": "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL",
        "firstname": "Bob",
        "lastname": "Marley",
        "birthday": "1945-02-06",
        "disabled": true,
        "email": null,
        "record_uid": "bob23",
        "roles": ["https://<fqdn>/ucsschool/kelvin/v1/roles/teacher"],
        "schools": ["https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL"],
        "school_classes": {},
        "source_uid": "Reggae DB",
        "udm_properties": {
            "description": null,
            "gidNumber": 5023,
            "employeeType": null,
            "organisation": null,
            "phone": [],
            "title": "Mr.",
            "uidNumber": 12711
        }
    }

The ``password`` attribute is missing in the response, because UCS systems never stores or sends clear text passwords.

Modify / Move
-------------

It is possible to perform complete and partial updates of existing user objects.
The ``PUT`` method expects a JSON object with all user attributes set.
The ``password`` attribute should *not* be sent repeatedly, as most password policies forbid reusing the same password.
The ``PATCH`` method will update only those attributes sent in the request.
Both methods return a complete Users resource in the response body, exactly as a ``GET`` request would.

PUT example
^^^^^^^^^^^
All required attributes must be sent with a ``PUT`` request.

As an example, with the following being the content of ``/tmp/mod_user.json``::

    {
        "name": "bob",
        "school": "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL",
        "firstname": "Bob72",
        "lastname": "Marley72",
        "record_uid": "bob72",
        "roles": ["https://<fqdn>/ucsschool/kelvin/v1/roles/teacher"],
        "schools": ["https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL"],
        "source_uid": "Kelvin Test2",
        "udm_properties": {"title": "Mr.2"}
    }

This ``curl`` command will modify the user with the above data::

    $ curl -i -k -X PUT "https://<fqdn>/ucsschool/kelvin/v1/users/bob" \
        -H "accept: application/json" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...." \
        -d "$(</tmp/mod_user2.json)"

Response headers::

    HTTP/1.1 200 OK
    Date: Tue, 21 Jan 2020 22:40:21 GMT
    Server: uvicorn
    content-length: 721
    content-type: application/json
    Via: 1.1 <fqdn>

Response body::

    {
        "birthday": null,
        "disabled": false,
        "dn": "uid=bob,cn=lehrer,cn=users,ou=DEMOSCHOOL,dc=uni,dc=ven",
        "email": null,
        "firstname": "Bob72",
        "lastname": "Marley72",
        "name": "bob",
        "record_uid": "bob72",
        "roles": ["https://<fqdn>/ucsschool/kelvin/v1/roles/teacher"],
        "school": "https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL",
        "school_classes": {},
        "schools": ["https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL"],
        "source_uid": "Kelvin Test2",
        "ucsschool_roles": ["teacher:school:DEMOSCHOOL"],
        "udm_properties": {
            "description": null,
            "employeeType": null,
            "gidNumber": 5023,
            "organisation": null,
            "phone": [],
            "title": "Mr.2",
            "uidNumber": 12816
        },
        "url": "https://<fqdn>/ucsschool/kelvin/v1/users/bob"
    }

PATCH example
^^^^^^^^^^^^^
Only the attributes that should be changed are sent with a ``PATCH`` request.
The following ``curl`` command will modify the users given name only::

    $ curl -i -k -X PATCH "https://<fqdn>/ucsschool/kelvin/v1/users/bob" \
        -H "accept: application/json" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...." \
        -d '{"firstname": "Robert Nesta"}'

Response headers::

    HTTP/1.1 200 OK
    Date: Tue, 21 Jan 2020 22:51:40 GMT
    Server: uvicorn
    content-length: 728
    content-type: application/json
    Via: 1.1 <fqdn>

Response body::

    {
        "birthday": null,
        "disabled": false,
        "dn": "uid=bob,cn=lehrer,cn=users,ou=DEMOSCHOOL,dc=uni,dc=ven",
        "email": null,
        "firstname": "Robert Nesta",
        ... # abbreviated: the rest is the same
    }

Move
^^^^

When a ``PUT`` or ``PATCH`` request change the ``school`` or ``schools`` attribute, the users LDAP object may be moved to a new position in the LDAP tree.

A move will only happen, when the new value for ``school`` is not in ``schools``.

When using ``PATCH`` and changing only ``school``, ``schools`` may be updated to contain the new value of ``school``.

While changing the ``name`` attribute is technically also a move, the objects *position* in the LDAP tree will not change - only its name.

Delete
------
The ``DELETE`` method is used to delete a user object::

    $ curl -i -k -X DELETE "https://<fqdn>/ucsschool/kelvin/v1/users/bob" \
        -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJh...."

Response headers::

    HTTP/1.1 204 No Content
    Date: Tue, 21 Jan 2020 22:57:03 GMT
    Server: uvicorn
    content-type: application/json
    Via: 1.1 <fqdn>

No response body.


.. _`Formatierungsschema`: https://docs.software-univention.de/ucsschool-import-handbuch-4.4.html#configuration:scheme_formatting
.. _`UDM REST API`: https://docs.software-univention.de/developer-reference-4.4.html#udm:rest_api
