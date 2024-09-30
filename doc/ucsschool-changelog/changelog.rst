.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-2024-10-01:

Released on 2024-10-01
======================

Source package *ucs-school-umc-computerroom* in version ``12.0.22``:

* Fixed: The computer room UMC module will no longer have large response times when offline computers are present (:uv:bug:`57631`).

.. _changelog-ucsschool-2024-09-26:

Released on 2024-09-26
======================

Source package *ucs-school-umc-computerroom* in version ``12.0.21``:

* Improved the performance of the UMC computer room module: More computers can be monitored at the same time (:uv:bug:`57610`).
* Improved the resource usage of the UMC computer room module: Unused computer room sessions will consume less resources (:uv:bug:`57099`).

Source package *ucs-school-veyon-client* in version ``2.0.9``:

* Improved the performance of the Veyon Python client (:uv:bug:`57610`).
* The authentication error pop up which is sometimes shown on the monitored Windows clients will no longer appear (:uv:bug:`53995`).

.. _changelog-ucsschool-2024-09-24:

Released on 2024-09-24
======================

Source package *ucs-school-import-lusd* in version ``1.0.0``:

* Added: A new package which supports importing users and groups from the LUSD API into UCS\@school. See the :external+uv-import:ref:`LUSD Import section <lusd-import>` in the UCS\@school Import manual for more information (:uv:bug:`57547`).
