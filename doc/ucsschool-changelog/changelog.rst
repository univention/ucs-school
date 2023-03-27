.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-2023-03-27:

Released on 2023-03-27
======================

Source package *ucs-school-lib* in version ``13.0.33A~5.0.0.202303141409``:

* The coding style has been improved (:uv:bug:`55751`).

* Colons can now be used in exam names (:uv:bug:`55768`).

Source package *ucs-school-import* in version ``18.0.30A~5.0.0.202303091544``:

* The coding style has been improved (:uv:bug:`55751`).

* When passing nested command line arguments like ``output`` for ``ucs-school-
  user-import``, only the last one was used. This has been fixed
  (:uv:bug:`53632`).

.. _changelog-ucsschool-2023-02-23:

Released on 2023-02-23
======================

Source package *ucs-school-umc-exam* in version ``10.0.8A~5.0.0.202302211433``:

* The coding style has been improved (:uv:bug:`55751`).

* Prevent ``exam-exam-`` users from being created. (:uv:bug:`55619`).

.. _changelog-ucsschool-2023-01-19:

Released on 2023-01-19
======================

Source package *ucs-school-umc-diagnostic* in version ``2.0.12A~5.0.0.202301161803``:

* Updated the terminology to replication and primary directory node
  (:uv:bug:`55557`).

Source package *ucs-school-lib* in version ``13.0.31A~5.0.0.202212070852``:

* Internal bug fix: More DNs are now compared case insensitive (:uv:bug:`55455`).

Source package *ucs-school-import* in version ``18.0.28A~5.0.0.202301121201``:

* Allow executing python import hooks during the script ``import_computer``.
  Learn more about the implementation of this type of hook in the `UCS@school
  Administrators manual <https://docs.software-univention.de/ucsschool-
  manual/5.0/de/manage-school-imports.html#skriptbasierter-import-von-pcs>`_
  (:uv:bug:`55014`).

* Internal bug fix: More OU names are now compared case insensitive
  (:uv:bug:`55455`).

.. _changelog-ucsschool-2022-11-17:

Released on 2022-11-17
======================

Source package *ucs-school-umc-wizards* in version ``12.0.12A~5.0.0.202211150913``:

* The evaluation of password policies during the creation of new users in the
  UMC can now be enabled by setting the UCR Variable
  ``ucsschool/wizards/schoolwizards/users/check-password-policies``. It is
  disabled by default (:uv:bug:`55415`).

Source package *ucs-school-lib* in version ``13.0.30A~5.0.0.202211151535``:

* |UCSUAS| users now might be created with context types, which are unknown to
  the |UCSUAS| library (:uv:bug:`55355`).

* Internal: Added an option to evaluate password policies when creating or
  modifying |UCSUAS| users (:uv:bug:`55392`).

* Internal: Add classes UbuntuComputer and LinuxComputer to |UCSUAS| library
  (:uv:bug:`55119`).

Source package *ucs-school-import* in version ``18.0.26A~5.0.0.202211151540``:

* The evaluation of password policies during the import of new users can now be
  enabled by setting the configuration option ``evaluate_password_policies``. It
  is disabled by default (:uv:bug:`55400`).

* Regression: The script ``import_computers`` supports computers of type
  ``linux`` and ``ubuntu`` again (:uv:bug:`55119`).

Released on 2022-11-02
======================

Source package *ucs-school-lib* in version ``13.0.24A~5.0.0.202210061204``:

* |UCSUAS| validation errors are logged with level ``WARNING`` instead of log
  level ``ERROR`` (:uv:bug:`55233`).

Source package *ucs-school-import* in version ``18.0.24A~5.0.0.202211011527``:

* Fix: Creating large data sets of test users sometimes failed due to non unique
  ``record_uids`` (:uv:bug:`55134`).

* Fix: When importing computers with a specified network instead of specific IP
  address, the import failed (:uv:bug:`55130`).

.. _changelog-ucsschool-2022-08-25:


Released on 2022-08-25:
=======================

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

.. _changelog-ucsschool-2022-08-17:

Released on 2022-08-17:
=======================

Source package *ucs-school-import* in version ``18.0.19A~5.0.0.202208171134``:

* A validation error causing an infinite recursion error was fixed
  (:uv:bug:`55083`).

Source package *ucs-school-umc-internetrules* in version
``16.0.4A~5.0.0.202208110901``:

* A bug was fixed which caused groups not being displayed in the *Assign
  internet rules* module when group prefixes were set via an UCR variable
  (:uv:bug:`55034`).

.. _changelog-ucsschool-2022-08-04:

Released on 2022-08-04:
=======================

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




