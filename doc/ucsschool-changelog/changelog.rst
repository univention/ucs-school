.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-2022-08-04:

Released on 2022-08-04:
-----------------------

Source package *ucs-school-import* in version ``18.0.18A~5.0.0.202207191615``:

* The |UCSUAS| import *dry-run* does not raise *ValidationErrors* for all
  subsequent users after an error (:uv:bug:`54118`).

* Internal change: preserve workgroups during import, to avoid a behavior change
  (:uv:bug:`54943`).

Source package *ucs-school-lib* in version ``13.0.21A~5.0.0.202207281220``:

* User objects now have the ``workgroups`` attribute (:uv:bug:`54943`).

* School admins are removed from ``admins-OU`` group when
  :py:meth:`remove_from_groups_of_school` is called (:uv:bug:`54368`).

Source package *ucs-school-umc-distribution* in version
``18.0.6A~5.0.0.202207201625``:

* Invalid project directories named ``.`` or ``..`` are now handled
  correctly (:uv:bug:`52719`).

Source package *ucs-school-umc-exam* in version ``10.0.6A~5.0.0.202207201619``:

* The directory name validation now detects all incorrect names. Additionally,
  the exam directory name description has been improved (:uv:bug:`52719`).

Source package *ucs-school-veyon-windows* in version
``4.7.4.0-ucs5.0-1A~5.0.0.202208021248``:

* The *Veyon* windows installer has been updated from 4.5.2 to 4.7.4
  (:uv:bug:`55029`).

.. _changelog-ucsschool-2022-08-17:

Released on 2022-08-17:
-----------------------

Source package *ucs-school-import* in version ``18.0.19A~5.0.0.202208171134``:

* A validation error causing an infinite recursion error was fixed
  (:uv:bug:`55083`).

Source package *ucs-school-umc-internetrules* in version
``16.0.4A~5.0.0.202208110901``:

* A bug was fixed which caused groups not being displayed in the *Assign
  internet rules* module when group prefixes were set via an UCR variable
  (:uv:bug:`55034`).

.. _changelog-ucsschool-2022-08-25:

Released on 2022-08-25:
-----------------------

Source package *ucs-school-import* in version ``18.0.21A~5.0.0.202208241614``:

* Fix user validation in mass import with *dry-run* (:uv:bug:`55016`).

* Underscores are now allowed in OU names, when the hostname of the school
  server is also passed (:uv:bug:`55125`).

Source package *ucs-school-lib* in version ``13.0.23A~5.0.0.202208241612``:

* Internal: Add ``check_name`` parameter to the :py:meth:`validate` method of
  multiple classes which allows disabling name checks such as checking if a user
  with the same user name already exists in another school (:uv:bug:`55016`).

* Underscores are now allowed in OU names, when the hostname of the school
  server is also passed (:uv:bug:`55125`).
