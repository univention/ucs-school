.. to compile run:
..     $ rst2html5 bb-api.rst bb-api.html

BB-API
======

Introduction
------------

The BB-API is written using the `Django REST framework (DRF) <https://www.django-rest-framework.org>`_.
It provides HTTP resources:

* Roles: roles that a ucsschool.lib user object can have: ``staff``, ``student``, ``teacher`` (read only).
* Schools: create and read (no modify or delete) of school OUs.
* Users: CRUD operations for ``ImportUser`` objects.

The `user` resource provides objects with the same attributes as in the Python ``ImportUser`` class. The keys in the ``udm_properties`` attribute are however restricted to a configurable set of UDM property names.

The type of user (staff, student, teacher or teacher and staff) is determined by the combination of roles in the ``roles`` attribute.

All references to other object types are modeled as URLs (links to resources): ``school``, ``schools``, ``roles``. The exception is ``school_classes``, which requires OU names as keys.

The PUT opertation is not supported, only PATCH. It does not accept a JSON-Patch document, but just the same JSON document as POST does, with only the changed atttibutes. The PATCH operation returnes the complete new object.

``dn`` and ``ucsschool_roles`` are read-only attributes. When creating or modifying a user, they cannot be set / changed.

When modifying a user, the ``source_uid`` and ``record_uid`` attributes must not be changed.


Installation
------------

1. Checkout git repository
2. Build and install ``ucs-school-http-api-bb``
3. Enable debugging::

	$ ucr set \
		bb/http_api/users/django_debug=yes \
		bb/http_api/users/wsgi_server_capture_output=yes \
		bb/http_api/users/wsgi_server_loglevel=debug
	# Attention: not safe for production!! django_debug=yes is very dangerous!

4. Allow logging into the browsable API (not required for production, but very nice for development)::

	$ ucr set bb/http_api/users/enable_session_authentication=yes

5. Setup the import configuration (the ``user`` resource is based on the ``ImportUser`` class, and thus uses the import framework)::

	$ cp /usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json /var/lib/ucs-school-import/configs/user_import.json
	$ python
	>>> import json
	>>> with open("/var/lib/ucs-school-import/configs/user_import.json", "r+w") as fp:
	...     config = json.load(fp)
	...     config["configuration_checks"] = ["defaults", "mapped_udm_properties"]
	...     config["mapped_udm_properties"] = ["phone", "e-mail", "organisation"]
	...     fp.seek(0)
	...     json.dump(config, fp, indent=4, sort_keys=True)

6. Restart API server::

	$ service ucs-school-http-api-bb restart

7. Check process (``service ucs-school-http-api-bb status``) and logs (see section below).
8. Quick tests: see `Examples` section.


Log files
---------

Log files are located in ``/var/log/univention/ucs-school-http-api-bb/``:

* ``http_api.log``: the API logs there
* ``gunicorn_access.log``: connection log of Gunicorn
* ``gunicorn_error.log``: Gunicorn log (>=DEBUG) and captured terminal output of API

BB-API README file: ``/usr/share/doc/ucs-school-http-api-bb/README.txt.gz`` (assumes installation of customer LDAP schema in some places)


Authentication
--------------
To use the API, a token must be sent with every query. It must be included in a header named ``Authorization`` with value ``Token <token>``. Alternatively a username and password can be passed in a browser session, when accessing the browsable API.

All API client users have the same (full) administrative powers!

There exists a user from the start: ``Administrator``. That's the Django super user, that is allowed to create more Django (API) users. API user passwords (including that of ``Administrator``) are checked against PAM, if the user account exists in LDAP, and against the Django (PostgreSQL) database. Only one of both checks is required to succeed. When a API client user (a Django user) is created, an associated token is automatically generated aswell.

Create a new API client and determine its API token
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
1) Open https://FQDN/api-bb/admin/ (the Django admin site) and login with ``Administrator``
2) ``Benutzer`` → ``Benutzer hinzufügen`` (do not create a staff or admin user!)
3) Enter username and a very long, indiviual password. Remember: only one password must succeed: that of a user with the same name in LDAP or that of this Django user.
4) ``Sichern``

To get the token that was generated for the user:

1) Jump back to https://FQDN/api-bb/admin/
2) Select ``Tokens``
3) Read out token for new user

Or on the command line::

	$ /usr/share/pyshared/bb/http_api/users/manage.py shell -c \
		"from rest_framework.authtoken.models import Token; print(Token.objects.first().key)"

The token has to be used in every request to the API, e.g.::

	$ curl -H "Authorization: Token eb0a88f554af2107681c3ec7f65ee43836dbfde4" ...


Examples
--------

See ``/usr/share/doc/ucs-school-http-api-bb/README.txt.gz`` for examples using curl.

See tests in ``92_ucsschool-http-api`` (currently in in branch `dtroeder/50087_bb-api-tests <https://github.com/univention/ucs-school/tree/dtroeder/50087_bb-api-tests/ucs-test-ucsschool/92_ucsschool-http-api>`_).

Some examples (to validate and format the output use ``| python -m json.tool``)::

	$ TOKEN="$(/usr/share/pyshared/bb/http_api/users/manage.py shell -c "from rest_framework.authtoken.models import Token; print(Token.objects.first().key)")"
	$ curl --insecure -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" -X GET https://127.0.0.1/api-bb/
	$ curl --insecure -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" -X GET https://127.0.0.1/api-bb/roles/
	$ curl --insecure -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" -X GET https://127.0.0.1/api-bb/roles/student/
	$ curl --insecure -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" -X GET https://127.0.0.1/api-bb/schools/
	$ curl --insecure -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" -X GET https://127.0.0.1/api-bb/schools/DEMOSCHOOL/
	$ curl --insecure -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" -X GET https://127.0.0.1/api-bb/users/
	$ curl --insecure -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" -X GET https://127.0.0.1/api-bb/users/demo_student/

