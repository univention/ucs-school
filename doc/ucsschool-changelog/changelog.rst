.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-changelogs:

*********
Changelog
*********

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

