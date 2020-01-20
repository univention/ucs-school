Resource Users
==============

The ``Users`` resource is represented in the LDAP tree as user objects.

The Users resource has a ``school`` attribute whose primary meaning is the position of its LDAP object in the LDAP tree.
More important is its ``schools`` attribute.
It is the list of schools that the student is enrolled in or where the staff and teacher work.

When creating/changing a user and a value for only ``school`` is send, ``schools`` will be a list of that one item.

When creating a user and only ``schools`` is sent, ``school`` will automatically be chosen as the alphabetically first of the list. When changing a user, the user object will stay in its OU, if it is the ``schools`` list, regardless of alphabetical order.

When both ``school`` and ``schools`` is used, the value of ``school`` must be in the list of values in ``schools``.

List / Search
-------------

Example ``curl`` command to retrieve the list of all schools (OUs)::

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
To search for users that are both `staff` and `teacher` with usernames that start with ``demo``, birthday on the 3rd of february, have a lastname that ends with `sam` and are enrolled in school ``demoschool``, the URL is: ``https://<fqdn>/ucsschool/kelvin/v1/users/?school=demoschool&name=demo%2A&birthday=2001-02-03&lastname=%2Asam&roles=staff&roles=teacher``

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

The attribute ``udm_properties`` is an object that can contain arbitrary UDM properties.
It must be configured in the file ``/var/lib/ucs-school-import/configs/kelvin.json``, see :ref:`Configuration of user object management (import configuration)`.

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

When creating a user, a number of attributes must be set, unless formatted from a template (see `Handbuch zur CLI-Import-Schnittstelle`, section `Formatierungsschema`_):

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
        "roles": ["https://<fqdn>/ucsschool/kelvin/v1/roles/teacher"],
        "schools": ["https://<fqdn>/ucsschool/kelvin/v1/schools/DEMOSCHOOL"],
        "source_uid": "Reggae DB",
        "udm_properties": {
            "title": "Mr."
        }
    }

This ``curl`` command will create a user from the above data::

    $ curl -i -k -X POST "https://m66.uni.dtr/ucsschool/kelvin/v1/users/" \
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

Modify
------


Move
----


Delete
------

.. _`Formatierungsschema`: https://docs.software-univention.de/ucsschool-import-handbuch-4.4.html#configuration:scheme_formatting