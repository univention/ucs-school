Calling the HTTP-API
====================

Assuming you have a user that is allowed to run imports for at least one role in one OU (see chapter :doc:`import-permissions`), you can query the HTTP-API for existing school and import-job objects and start new imports.
Let's say the user has the username ``myteacher`` and the password ``univention``.

In the context of HTTP-APIs those objects are called *resources*.
An HTTP-API is used to create new resources, fetch a single or a collection of a resource, modify an existing resource or delete it.
The resources in the UCS\@school import HTTP-API can be found on the APIs root URL::

    $ curl -s -k -H "Content-Type: application/json" -u myteacher:univention \
        https://$(hostname -f)/api/v1/ | python -m json.tool

.. code-block:: json

    {
        "imports/users": "https://$HOST/api/v1/imports/users/",
        "schools": "https://$HOST/api/v1/schools/"
    }

.. important::

    Do not hard code those URLs into a client application.
    Always use the URLs found at the APIs root (you may cache them), to access the resources.
    This will allow the APIs developers to modify the resources URLs, without breaking existing clients.

Currently there are two resources available:

* ``school`` resource at URL ``https://$HOST/api/v1/schools/``
* ``user import`` resource at URL: ``https://$HOST/api/v1/imports/users/``

The school resource
-------------------

The school resource represents a school/OU.
It lists only the schools the connected user has permission to import users into (for at least one role).

Technically the school resource is created by the Django REST framework from a Django model: ``ucsschool.http_api.import_api.models.School`` (`models.py:63 <https://github.com/univention/ucs-school/blob/b7d90f21fa89134163610859b8abf1132d0e8d96/ucs-school-import/modules/ucsschool/http_api/import_api/models.py#L63>`_).

The school resource allows only the operations ``list`` and ``get``.

List operation
~~~~~~~~~~~~~~

Assuming the user ``myteacher`` has permissions to do imports for at least one role in schools ``$OU`` and ``$OU2``, listing the collection of schools will look like this::

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

A collection representation can be incomplete with regards to resource attributes.
It may only contain the primary key (``name`` here) and the URL of the resource.

Get operation
~~~~~~~~~~~~~

To fetch the complete resource follow the URL of the object in the previously retrieved collection::

    $ curl -s -k -H "Content-Type: application/json" -u myteacher:password \
        https://$(hostname -f)/api/v1/schools/$OU/ | python -m json.tool

.. code-block:: json

    {
        "displayName": "$OU",
        "name": "$OU",
        "url": "https://$HOST/api/v1/schools/$OU/",
        "user_imports": "https://$HOST/api/v1/schools/$OU/imports/users"
    }

A sub-resource ``user_imports`` is now visible.
When following its URL, a collection of user import resources can be retrieved.
Those are the import jobs that have been run on ``$OU``.

.. important::

    Do not calculate URLs of resources.
    Always follow the links provided by the collection.
    This allows the APIs developers to modify the object URLs, without breaking existing clients.

The user import resource
------------------------

The user import resource represents an ``import job``.
That is a little bit unusual, because it is not a physical or virtual object, but rather a *process*.
The user import resource lists previous imports only from schools the connected user has permissions to do imports for.

Creating a user import resource **starts an import**!

Technically the user import resource is created by the Django REST framework from a Django model: ``ucsschool.http_api.import_api.models.UserImportJob`` (`models.py:155 <https://github.com/univention/ucs-school/blob/b7d90f21fa89134163610859b8abf1132d0e8d96/ucs-school-import/modules/ucsschool/http_api/import_api/models.py#L155>`_).

The user import resource allows only the operations ``create``, ``list`` and ``get``.

attributes
~~~~~~~~~~

The resources ``status`` attribute will be updated by the import process.
It may have one of the following values: ``New``, ``Scheduled``, ``Started``, ``Aborted``, ``Finished`` (`models.py:52 <https://github.com/univention/ucs-school/blob/b7d90f21fa89134163610859b8abf1132d0e8d96/ucs-school-import/modules/ucsschool/http_api/import_api/models.py#L52>`_).
That value is shown in the "Status" column of the UMCs "User Imports" list.

The resources ``result.result.percentage`` attribute may be set to the percentage of the import jobs progress and will be shown in the UMC modules progress bar.


Create operation
~~~~~~~~~~~~~~~~

**TODO**

List operation
~~~~~~~~~~~~~~

If the user has already successfully made an import, at least two resource objects should be in the collection: a dry-run and the real import.

In the following example the first import crashed, because of a configuration error.
The second import was a successful dry-run and the third a successful real run.
The UMC module does not list dry-runs::

    $ curl -s -k -H "Content-Type: application/json" -u myteacher:univention \
        https://$(hostname -f)/api/v1/imports/users/ | python -m json.tool

.. code-block:: json

    {
        "count": 3,
        "next": null,
        "previous": null,
        "results": [
            {
                "date_created": "2018-04-19T15:58:33.804178Z",
                "dryrun": true,
                "id": 1,
                "input_file": "uploads/2018-04-19/1524153513-test-http-import_m65.csv",
                "log_file": "Logfile #1 of importjob #1",
                "password_file": "PasswordsFile #2 of importjob #1",
                "principal": "myteacher",
                "result": {
                    "date_done": "2018-04-19T15:58:40.482007Z",
                    "result": {
                        "exc_message": "Import job exited with 1.",
                        "exc_type": "Exception"
                    },
                    "status": "FAILURE",
                    "traceback": "Traceback (most recent call last): <shortend for brevity>"
                },
                "school": "https://$HOST/api/v1/schools/$OU/",
                "source_uid": "$OU-$ROLE",
                "status": "Aborted",
                "summary_file": "SummaryFile #3 of importjob #1",
                "url": "https://$HOST/api/v1/imports/users/1/",
                "user_role": "$ROLE"
            },
            {
                "date_created": "2018-04-19T15:59:46.262684Z",
                "dryrun": true,
                "id": 2,
                "input_file": "uploads/2018-04-19/1524153585-test-http-import_m65.csv",
                "log_file": "Logfile #4 of importjob #2",
                "password_file": "PasswordsFile #5 of importjob #2",
                "principal": "myteacher",
                "result": {
                    "date_done": "2018-04-19T15:59:52.561835Z",
                    "result": {
                        "description": "UserImportJob #2 (dryrun) ended successfully.",
                        "done": 0,
                        "percentage": 100,
                        "total": 0
                    },
                    "status": "SUCCESS",
                    "traceback": null
                },
                "school": "https://$HOST/api/v1/schools/$OU/",
                "source_uid": "$OU-$ROLE",
                "status": "Finished",
                "summary_file": "SummaryFile #6 of importjob #2",
                "url": "https://$HOST/api/v1/imports/users/2/",
                "user_role": "$ROLE"
            },
            {
                "date_created": "2018-04-19T15:59:56.354740Z",
                "dryrun": false,
                "id": 3,
                "input_file": "uploads/2018-04-19/1524153585-test-http-import_m65_pdJsybe.csv",
                "log_file": "Logfile #7 of importjob #3",
                "password_file": "PasswordsFile #8 of importjob #3",
                "principal": "myteacher",
                "result": {
                    "date_done": "2018-04-19T16:00:04.701670Z",
                    "result": {
                        "description": "UserImportJob #3 ended successfully.",
                        "done": 0,
                        "percentage": 100,
                        "total": 0
                    },
                    "status": "SUCCESS",
                    "traceback": null
                },
                "school": "https://$HOST/api/v1/schools/$OU/",
                "source_uid": "$OU-$ROLE",
                "status": "Finished",
                "summary_file": "SummaryFile #9 of importjob #3",
                "url": "https://$HOST/api/v1/imports/users/3/",
                "user_role": "$ROLE"
            }
        ]
    }


Get operation
~~~~~~~~~~~~~

**TODO**


The school resources ``user_imports`` sub-resource
--------------------------------------------------

**TODO**
