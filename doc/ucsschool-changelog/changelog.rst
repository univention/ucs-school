.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-9999-99-99:

Released on 9999-99-99
======================

Source package *ucs-school-import* in version ``18.0.50``:

* Fix for LUSD import (:uv:bug:`57547`).

* Fix SiSoPi missing :code:`ucsschoolPurgeTimestamp` for "deleted" users (:uv:bug:`50848`).

Source package *ucs-school-import-lusd* in version ``1.0.0``:

* New package for LUSD import (:uv:bug:`57547`).


.. _changelog-ucsschool-2024-08-15:

Released on 2024-08-15
======================

Source package *ucs-school-import* in version ``18.0.48``:

* Fixed a bug that would lead to a faulty configuration if there
  was a user with the role ``teacher_and_staff`` (:uv:bug:`57208`).

Source package *ucs-school-umc-exam* in version ``10.0.13``:

* Fixed a bug that lead to skips in the cron controlled cleanup jobs on
  single server installations (:uv:bug:`53232`).

Source package *ucs-school-umc-users* in version ``16.0.10``:

* Fixed an issue that would lead to an :code:`UnknownPropertyError` when
  mapping extended attributes from :code:`LDAP` to :code:`UDM` and leads
  to crashes of the module (:uv:bug:`55740`).

Source package *ucs-school-umc-users* in version ``16.0.9``:

* Fixed a bug which would prevent teachers to reset passwords of students
  when they have unset extended attributes (:uv:bug:`55740`).

.. _changelog-ucsschool-2024-07-11:

Released on 2024-07-11
======================

Source package *ucs-school-import* in version ``18.0.47``:

* Fixed a performance regression which could cause significant longer startup
  times for the UCS\@school import (:uv:bug:`57408`).

Source package *ucs-school-umc-computerroom* in version ``12.0.17``:

* Added the UCR variable ``ucsschool/umc/computerroom/screenshot_dimension``, with
  which you can set the base screenshot size in the computer room module. A lower
  base screenshot size can help to improve performance (:uv:bug:`57443`).

.. _changelog-ucsschool-2024-07-02:

Released on 2024-07-02
======================

Source package *ucs-school-import* in version ``18.0.46``:

* The ``ucs-school-purge-expired-users`` now ignores users without a UCS\@school
  role that is recognized by the UCS\@school Importer (:uv:bug:`55179`).

Source package *ucs-school-metapackage* in version ``13.0.18``:

* Add the Keycloak Kerberos user SPN to the samba SPN list on replicas for new
  joins (:uv:bug:`57348`).

Source package *ucs-school-netlogon-user-logonscripts* in version ``16.0.6``:

* The new Nubus logo replaces the UCS logo. Users who have the link for the UMC
  on the desktop will see the new logo (:uv:bug:`57395`).

Source package *ucs-school-umc-computerroom* in version ``12.0.16``:

* If a local user is logged into a computer that is in a computer room, the
  username is prefixed with ``LOCAL\`` in the computer room module instead of
  showing an error message (:uv:bug:`56937`).

Source package *ucs-school-umc-exam* in version ``10.0.12``:

* Added validation for students when they are added to an exam. This helps to
  detect validation errors before the exam is started (:uv:bug:`57319`).

* If errors occur due to incorrect samba share configuration files, they are
  displayed during the preparation and not during the exam (:uv:bug:`57367`).

Source package *ucs-school-umc-import* in version ``3.0.8``:

* The selection in the UCS\@school UMC import was not properly localized. An
  updated image was placed in the documentation (:uv:bug:`56519`).


.. _changelog-ucsschool-2024-05-16:

Released on 2024-05-16
======================

Source package *ucs-school-veyon-windows* in version ``4.8.3.0-ucs5.0-0``:

* Update Veyon windows client to version 4.8.3.0 (:uv:bug:`53907`).

.. _changelog-ucsschool-2024-03-21:

Released on 2024-03-21
======================

Source package *ucs-school-import* in version ``18.0.45``:

* When importing a computer with an IP address starting with "255.", the user
  gets a warning that is logged to the console (:uv:bug:`55376`).

* Internal change: Improve search filter for mac addresses for importing a
  computer. (:uv:bug:`55015`).

* Fixed an issue that caused the user importer to not properly detect the
  encoding of a given CSV file (:uv:bug:`56846`).

Source package *ucs-school-info* in version ``10.0.3``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-lib* in version ``13.0.45``:

* Fixed a consistency check for non default admins group prefix. See UCRV
  ``ucsschool/ldap/default/groupprefix/admins``. (:uv:bug:`55884`).

Source package *ucs-school-metapackage* in version ``13.0.17``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-netlogon-user-logonscripts* in version ``16.0.5``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-netlogon* in version ``10.0.3``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-old-sharedirs* in version ``15.0.4``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-ox-support* in version ``4.0.4``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-roleshares* in version ``8.0.4``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-umc-internetrules* in version ``16.0.5``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-umc-lists* in version ``3.0.10``:

* Fixed issues that would lead to unexpected behavior while exporting class
  lists (:uv:bug:`57018`).

Source package *ucs-school-umc-rooms* in version ``17.0.10``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-veyon-client* in version ``2.0.5``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *ucs-school-webproxy* in version ``16.0.8``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

Source package *univention-management-console-module-selective-udm* in version ``9.0.4``:

* Internal Change: Reformatted source code for better readability and
  maintainability. (:uv:bug:`55751`).

