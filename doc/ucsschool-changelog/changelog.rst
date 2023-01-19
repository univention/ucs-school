.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-2023-01-19:

Released on 2023-01-19
======================

Source package *ucs-school-umc-diagnostic* in version ``2.0.12A~5.0.0.202301161803``:

* Updated the terminology to replication and primary directory node
  (:uv:bug:`55557`).

Source package *ucs-school-lib* in version ``13.0.31A~5.0.0.202212070852``:

* Internal bugfix: More DNs are now compared case insensitive (:uv:bug:`55455`).

Source package *ucs-school-import* in version ``18.0.28A~5.0.0.202301121201``:

* Allow executing python import hooks during the script ``import_computer``.
  Learn more about the implementation of this type of hook in the `UCS@school
  Administrators manual <https://docs.software-univention.de/ucsschool-
  manual/5.0/de/manage-school-imports.html#skriptbasierter-import-von-pcs>`_
  (:uv:bug:`55014`).

* Internal bugfix: More OU names are now compared case insensitive
  (:uv:bug:`55455`).

.. _changelog-ucsschool-2022-11-17:

Released on 2022-11-17
======================

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

Source package *ucs-school-umc-wizards* in version ``12.0.12A~5.0.0.202211150913``:

* The evaluation of password policies during the creation of new users in the
  UMC can now be enabled by setting the UCR-Variable
  ``ucsschool/wizards/schoolwizards/users/check-password-policies``. It is
  disabled by default (:uv:bug:`55415`).

.. _changelog-ucsschool-2022-11-02:

Released on 2022-11-02
======================

Source package *ucs-school-lib* in version ``13.0.24A~5.0.0.202210061204``:

* UCS\@school validation errors are logged with level ``WARNING`` instead of log
  level ``ERROR`` (:uv:bug:`55233`).

Source package *ucs-school-import* in version ``18.0.24A~5.0.0.202211011527``:

* Fix: Creating large data sets of test users sometimes failed due to non unique
  ``record_uids`` (:uv:bug:`55134`).

* Fix: When importing computers with a specified network instead of specific IP
  address, the import failed (:uv:bug:`55130`).

.. _changelog-ucsschool-2022-08-25:

Released on 2022-08-25
======================

Source package *ucs-school-lib* in version ``13.0.23A~5.0.0.202208241612``:

* Internal: Add `check_name` parameter to the `validate` method of multiple
  classes which allows disabling name checks such as checking if a user with the
  same user name already exists in another school (:uv:bug:`55016`).

* Underscores are now allowed in OU names, when the hostname of the school
  server is also passed (:uv:bug:`55125`).

Source package *ucs-school-import* in version ``18.0.21A~5.0.0.202208241614``:

* Fix user validation in mass import with dry-run (:uv:bug:`55016`).

* Underscores are now allowed in OU names, when the hostname of the school
  server is also passed (:uv:bug:`55125`).

.. _changelog-ucsschool-2022-08-17:

Released on 2022-08-17
======================

Source package *ucs-school-import* in version ``18.0.19A~5.0.0.202208171134``:

* A validation error causing an infinite recursion error was fixed
  (:uv:bug:`55083`).

Source package *ucs-school-umc-internetrules* in version ``16.0.4A~5.0.0.202208110901``:

* A bug was fixed which caused groups not being displayed in the <literal>Assign
  internet rules</literal> module when group prefixes were set via an UCR
  variable (:uv:bug:`55034`).

.. _changelog-ucsschool-2022-08-04:

Released on 2022-08-04
======================

Source package *ucs-school-lib* in version ``13.0.21A~5.0.0.202207281220``:

* User objects now have the workgroups attribute (:uv:bug:`54943`).

* School admins are removed from admins-OU group when
  remove_from_groups_of_school() is called (:uv:bug:`54368`).

Source package *ucs-school-import* in version ``18.0.18A~5.0.0.202207191615``:

* The UCS@School import dryrun does not raise VaidationErrors for all subsequent
  users after an error (:uv:bug:`54118`).

* Internal change: preserve workgroups during import, to avoid a behavior change
  (:uv:bug:`54943`).

Source package *ucs-school-veyon-windows* in version ``4.7.4.0-ucs5.0-1A~5.0.0.202208021248``:

* The veyon windows installer has been updated from 4.5.2 to 4.7.4
  (:uv:bug:`55029`).

Source package *ucs-school-umc-exam* in version ``10.0.6A~5.0.0.202207201619``:

* The directory name validation now detects all incorrect names. Additionally,
  the exam directory name description has been improved (:uv:bug:`52719`).

Source package *ucs-school-umc-distribution* in version ``18.0.6A~5.0.0.202207201625``:

* Invalid project directories named '.' or '..' are now handled correctly
  (:uv:bug:`52719`).

.. _changelog-ucsschool-2022-07-14:

Released on 2022-07-14
======================

Source package *ucs-school-umc-diagnostic* in version ``2.0.10A~5.0.0.202205061538``:

* Correct school admins are not detected as wrong by the diagnostic module
  (:uv:bug:`54415`).

Source package *ucs-school-lib* in version ``13.0.19A~5.0.0.202207071332``:

* Internal: The code which executed shell hooks was removed from the UCS@school
  library (:uv:bug:`54755`, :uv:bug:`53506`).

* The validation was adapted to prevent invalid school names in multiserver
  environments (:uv:bug:`53506`, :uv:bug:`54030`).

* The wording of some descriptions shown in UMC modules was adjusted
  (:uv:bug:`54030`, :uv:bug:`54535`).

* The UCS@school validation does not crash anymore with custom UCS@school roles
  (:uv:bug:`54535`, :uv:bug:`54248`).

* A UCR variable was corrected, which was used to check Marktplatz shares
  consistency inside a diagnostic check (:uv:bug:`54248`, :uv:bug:`54755`).

* Internal: The syntax class of the user's attribute expiration_date was changed
  (:uv:bug:`54812`).

* Internal: The UCS@school lib was adapted to handle UMC searches consistently
  (:uv:bug:`50797`).

Source package *ucs-school-import* in version ``18.0.16A~5.0.0.202205310915``:

* The UCS@school computer import now supports the execution of python hooks. It
  is not possible to use shell hooks anymore (:uv:bug:`54755`, :uv:bug:`54030`).

* A French translation of UDM extended attributes and extended options has been
  added (:uv:bug:`54030`, :uv:bug:`54755`).

Source package *ucs-school-umc-wizards* in version ``12.0.10A~5.0.0.202207071456``:

* Searches in the UMC now handle asterisks consistently (:uv:bug:`50797`).

Source package *ucs-school-umc-internetrules* in version ``16.0.3A~5.0.0.202207071448``:

* Searches in the UMC now handle asterisks consistently (:uv:bug:`50797`).

Source package *ucs-school-umc-exam* in version ``10.0.5A~5.0.0.202206241101``:

* The creation of exam students will no longer copy specific operational LDAP
  attributes from the original user. In effect the LDAP attribute blacklist
  stored in the UCR variable <envar>ucsschool/exam/user/ldap/blacklist</envar>
  is implicitly extended by a hardcoded set of operational attribute names. This
  change is required for compatibility with UCS 5.0-2 where operational LDAP
  attributes are added to the internal user information of UDM
  (:uv:bug:`54896`).

Source package *ucs-school-webproxy* in version ``16.0.7A~5.0.0.202204271758``:

* Resolved warnings that appeared during the installation (:uv:bug:`54571`).

Source package *ucs-school-veyon-client* in version ``2.0.4A~5.0.0.202206231055``:

* An new connection test method has been added (:uv:bug:`53421`)

Source package *ucs-school-umc-users* in version ``16.0.5A~5.0.0.202207071454``:

* Searches in the UMC now handle asterisks consistently (:uv:bug:`50797`).

Source package *ucs-school-umc-rooms* in version ``17.0.9A~5.0.0.202207071451``:

* Searches in the UMC now handle asterisks consistently (:uv:bug:`50797`).

Source package *ucs-school-umc-lists* in version ``3.0.6A~5.0.0.202203181232``:

* Deactivated students can be excluded from the class list export.
  (:uv:bug:`50335`)

* Students that are not assigned to a class are ignored when the class list is
  created. (:uv:bug:`52335`)

* The wording of some descriptions shown in UMC modules was adjusted
  (:uv:bug:`54030`).

Source package *ucs-school-umc-installer* in version ``8.0.8A~5.0.0.202205310922``:

* The wording of some descriptions shown in UMC modules was adjusted
  (:uv:bug:`54030`).

* The creation of a demo school and demo users is now configurable in the
  "UCS@school configuration wizard" UMC module (:uv:bug:`49533`).

Source package *ucs-school-umc-import* in version ``3.0.5A~5.0.0.202207131524``:

* The wording of some descriptions shown in UMC modules was adjusted
  (:uv:bug:`54030`).

Source package *ucs-school-umc-groups* in version ``10.0.7A~5.0.0.202207071445``:

* Verify that the users belong to the work group's school when adding users to
  an existing work group (:uv:bug:`54040`).

* Searches in the UMC now handle asterisks consistently (:uv:bug:`50797`).

Source package *ucs-school-umc-computerroom* in version ``12.0.11A~5.0.0.202206301342``:

* The wording of some descriptions shown in UMC modules was adjusted
  (:uv:bug:`54030`).

* An error message regarding the Veyon WebAPI Server has been improved
  (:uv:bug:`53421`).

* After a Veyon session becomes invalid, a new session is established
  (:uv:bug:`53558`).

Source package *ucs-school-netlogon-user-logonscripts* in version ``16.0.4A~5.0.0.202205171120``:

* Corrected spelling and grammar mistakes in UCR variable descriptions
  (:uv:bug:`54758`).

Source package *ucs-school-metapackage* in version ``13.0.15A~5.0.0.202205190959``:

* Add mail address for demo users (:uv:bug:`48896`).

* Demo users can now be retrieved in the UCS@school Kelvin REST API
  (:uv:bug:`54205`).

* Fix error in script "set_nt_acl_on_shares" when joining backup to single
  master. (:uv:bug:`54735`).

Source package *ucs-school-ldap-acls-master* in version ``18.0.4A~5.0.0.202206011518``:

* Users which don't belong to any school, and which were created outside of
  cn=users could not be replicated to school servers, since they didn't have the
  necessary rights to read all attributes of these users. The LDAP ACLs have
  been adjusted to make the replication possible (:uv:bug:`51279`).

Source package *ucs-school-l10n-fr* in version ``5.0.4A~5.0.0.202207121347``:

* The French translation package has been given a comprehensive update to align
  it to the current source code. All missing translation strings have been added
  and all outdated strings have been updated (:uv:bug:`54030`).

* Update translation of schoolinstaller (:uv:bug:`49533`).

