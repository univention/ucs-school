Test installed components
=========================

Check if components are running
-------------------------------

All five services must be running:

.. code-block:: bash

	service apache2 status
	service ucs-school-import-http-api status  # this is Gunicorn
	service postgresql status
	service rabbitmq-server status
	service celery-worker-ucsschool-import status

Check if components are working
-------------------------------

Django, Django REST framework and PostgreSQL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the join script succeeded, the database already contains a list of OUs. Let's say we have two OUs in our domain::

	$ univention-ldapsearch -LLL objectClass=ucsschoolOrganizationalUnit ou

	dn: ou=SchoolOne,dc=uni,dc=dtr
	ou: SchoolOne
	dn: ou=SchoolTwo,dc=uni,dc=dtr
	ou: SchoolTwo

Those OUs should already exist as objects in Djangos database::

	$ python -m ucsschool.http_api.manage shell -c \
	    "from ucsschool.http_api.import_api.models import School; print School.objects.all()"

	<QuerySet [<School: SchoolOne>, <School: SchoolTwo>]>

For this command to succeed Django, Django REST framework and PostgreSQL must be working and be configured. This does not use HTTP, yet.

If those frameworks and services are OK, we can check Apache and Gunicorn next.

Apache and Gunicorn
~~~~~~~~~~~~~~~~~~~~~~~

To check if the the backends frontend components work, go to the API root (``https://$HOST/api/v1/``).
If the page exists, Apache and Gunicorn are working as well.

You'll get a ``HTTP 403`` with ``{"detail": "Authentication credentials were not provided."}``.
That's OK - the API cannot be used without authenticating.

Use the ``Log in`` link in the top right corner and authenticate as ``Administrator``.
You'll now be able to follow two links:

.. code-block:: json

	{
	    "schools": "https://$HOST/api/v1/schools/",
	    "imports/users": "https://$HOST/api/v1/imports/users/"
	}

If the lists behind those links are empty, it is because the logged in user does not have the required import permission on any school.
That may also true for the ``Administrator`` user.

At this point Apache, Gunicorn, Django, Django REST framework and PostgreSQL must be working.

You can log into the UMC with the test user (``myteacher``) you created earlier and start the UMC ``schoolimport`` module.

It the module tells you that ``The permissions to perform a user import are not sufficient enough.``, then either the user is not part of any security group (circle back to section :ref:`add-user-to-security-group`) or you need to restart the UMC server: ``service univention-management-console-server restart``.

Assuming you have a user with import permissions, you can log in with that user and retrieve the list of schools and finished import jobs.
The web site ``https://$HOST/api/v1/schools/`` should list the schools for which the user was given permissions now.

Instead of using a browser, the HTTP-API can of cause be queried directly through HTTP::

	$ curl -s -k -H "Content-Type: application/json" -u myteacher:univention \
	    https://$(hostname -f)/api/v1/schools/ | python -m json.tool

.. code-block:: json

	{
	    "count": 2,
	    "next": null,
	    "previous": null,
	    "results": [
	        {
	            "displayName": "$OU",
	            "name": "$OU",
	            "url": "https://$HOST/api/v1/schools/$OU/"
	        },
	        {
	            "displayName": "$OU2",
	            "name": "$OU2",
	            "url": "https://$HOST/api/v1/schools/$OU2/"
	        }
	    ]
	}


In this example the user was given access to a second OU (added to group ``$OU2-import-all``).

If an error occurred, use ``-v`` instead of ``-s`` to make the ``curl`` call verbose instead of silent.

RabbitMQ and Celery
~~~~~~~~~~~~~~~~~~~

To check if the RabbitMQ and Celery services work, we'll need to start an import.
But to start an import, we'll need a CSV file and a matching import configuration.
