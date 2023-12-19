.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-2023-12-19:

Released on 2023-12-19
======================

Source package *ucs-school-lib* in version ``13.0.42``:

* Fixed a bug that would crash the password reset module within the UMC when a
  teacher tries to read a class, in which there exists a member that is not a
  member of the teachers school (:uv:bug:`50231`).

Source package *ucs-school-import* in version ``18.0.40``:

* Errors which occur during the configuration of ``ucs-school-import`` are now
  properly written to a log file (:uv:bug:`42373`).

* Import no longer fails if a binary input file is provided and a compatible
  reader class exists (:uv:bug:`56728`).

Source package *ucs-school-umc-users* in version ``16.0.8``:

* Fixed a bug that would crash the password reset module within the UMC when a teacher tries to read a class, in which there exists a member that is not a
  member of the teachers school (:uv:bug:`50231`).


.. _changelog-ucsschool-2023-11-16:

Released on 2023-11-16
======================

Source package *ucs-school-umc-groups* in version ``10.0.10``:

* Fixed a bug where the email of a group in the UMC module "Administrate
  workgroups" was incorrectly displayed as empty. This could lead to the email
  being deleted when changes were saved (:uv:bug:`56589`).

Source package *ucs-school-umc-computerroom* in version ``12.0.15``:

* Instead of raising an error, a warning is displayed when computers inside of a
  computer room are missing an IP address and the computer icon is colored
  orange (:uv:bug:`53624`).

* Computers without MAC addresses don't raise an error when opening the computer
  room (:uv:bug:`53571`).

.. _changelog-ucsschool-2023-10-25:

Released on 2023-10-25
======================

Source package *ucs-school-umc-wizards* in version ``12.0.14``:

* The coding style has been improved (:uv:bug:`55751`).

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-umc-printermoderation* in version ``17.1.4``:

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-umc-lists* in version ``3.0.9``:

* The CSV files for the recommended export function are now properly formatted
  (:uv:bug:`56403`).

Source package *ucs-school-umc-installer* in version ``8.0.10``:

* The coding style has been improved (:uv:bug:`55751`).

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-umc-import* in version ``3.0.7``:

* The coding style has been improved (:uv:bug:`55751`).

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-umc-helpdesk* in version ``16.0.7``:

* The coding style has been improved (:uv:bug:`55751`).

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-umc-exam* in version ``10.0.10``:

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-umc-distribution* in version ``18.0.8``:

* The coding style has been improved (:uv:bug:`55751`).

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-umc-computerroom* in version ``12.0.13``:

* The coding style has been improved (:uv:bug:`55751`).

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-lib* in version ``13.0.41``:

* Added missing UCR variable descriptions (:uv:bug:`52844`).

* Deprecated UMC APIs have been replaced with public UMC APIs (:uv:bug:`56390`).

Source package *ucs-school-import* in version ``18.0.36``:

* Added rotation for importer worker logs (:uv:bug:`52167`).

.. _changelog-ucsschool-2023-09-12:

Released on 2023-09-12
======================

Source package *ucs-school-import* in version ``18.0.33``:

* The SiSoPi user import now keeps class memberships for other schools.
  (:uv:bug:`56340`)

.. _changelog-ucsschool-2023-08-02:

Released on 2023-08-02
======================

Source package *ucs-school-umc-diagnostic* in version ``2.0.15``:

* The coding style has been improved (:uv:bug:`55751`).

* Added a new system diagnostic feature: Existing UCS@school usernames will be
  checked for validity. Warnings are issued if deprecated or unsupported
  usernames have been found. (:uv:bug:`56152`, :uv:bug:`55751`).

Source package *ucs-school-lib* in version ``13.0.39``:

* The UCR variable ``ucsschool/validation/username/windows-check`` has been added
  and can be used to control the username validation with respect to Windows
  naming conventions (:uv:bug:`56152`).

