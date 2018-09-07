Single source, partial import (SiSoPi) scenario
===============================================

Introduction
------------

The scenario in which a single source database for users in all schools exists, but the user import jobs will be run separately for each school, is supported since UCS\@school 4.3 v5 for both the command line and the HTTP-API import (via UMC module).

Features
--------

* OU spanning user accounts (a user can be member of multiple schools)
* Each school imports its users separately at a time and order of their choosing.

Requirements
------------

* A single source database exists that knows all users and has a globally unique ``record_uid`` for each of them.
* The source database exports separate CSV files per school and user type.
* As imports are done in random order, it is possible that to move a user from one school to another, it is first removed in one school and imported at the other school at a later time. The user account must not be deleted in the meantime.

Implementation
--------------

Initial implementation was done through `Bug #47447 <http://forge.univention.org/bugzilla/show_bug.cgi?id=47447>`_.

To make it possible to move a user from school *A* to *B* in two steps (deleting it first in school *A* and adding it later in school *B*), a "in-between school" is used: the ``limbo_ou``. It is a regular school OU, whose name is configurable (defaults to *limbo*).

Users that are deleted by the import from their last/only school (*A*) are a) immediately deactivated and b) moved there (*limbo*).

When/if a user is imported to be created in a school (*B*), and a user with its ``record_uid`` exists in *limbo*, it is moved to the school (*B*) and activated.

Installation & Configuration
----------------------------

Add the configuration in ``/usr/share/ucs-school-import/configs/user_import_sisopi.json`` to your import configuration (in ``/var/lib/ucs-school-import/configs/user_import.json``).

You may wish to adapt the ``deletion_grace_period`` settings:

* ``deletion_grace_period:deactivation`` *must* be ``0``.
* ``deletion_grace_period:deletion`` *should* be (a lot) higher than ``0``. It should be the maximum time in days that the imports of two schools may be apart. It is the time a user can exist in *limbo*, before going to the great beyond.

You may wish to adapt the name of the ``limbo_ou``.

Set the UCR variable ``ucsschool/import/http_api/set_source_uid`` to ``no`` and restart Gunicorn::

	ucr set ucsschool/import/http_api/set_source_uid=no
	service ucs-school-import-http-api restart
