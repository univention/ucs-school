.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-2025-08-06:

Released on 2025-08-06
======================

Source package *ucs-school-import-lusd* in version ``1.0.6``:

* School names are now correctly prepended to class names (:uv:bug:`58499`).

.. _changelog-ucsschool-2025-06-04:

Released on 2025-06-04
======================

Source package *ucs-school-umc-distribution* in version ``18.0.11``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-printermoderation* in version ``17.1.5``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-wizards* in version ``12.0.15``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-exam* in version ``10.0.18``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-computerroom* in version ``12.0.26``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-groups* in version ``10.0.11``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-internetrules* in version ``16.0.6``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-rooms* in version ``17.0.11``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-users* in version ``16.0.11``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

Source package *ucs-school-umc-installer* in version ``8.0.11``:

* Security fix: The package has been checked and additional measures have been added to prevent possible cross-site scripting in the UMC module(s) (:uv:bug:`58366`).

.. _changelog-ucsschool-2025-04-28:

Released on 2025-04-28
======================

Source package *ucs-school-umc-exam* in version ``10.0.17``:

* Fix: The permissions of the PDF printer queue directory of exam users are now automatically corrected when the exam is started. Previously, it could happen that print jobs were sent by the exam user, but no print jobs appeared in the print moderation (:uv:bug:`58236`).

.. _changelog-ucsschool-2025-04-03:


Released on 2025-04-03
======================

Source package *ucs-school-umc-exam* in version ``10.0.16``:

* Fixed a bug for students in multiple exams, if the :envvar:`ucsschool/exam/user/disable` was set to ``yes``.
  Their exam users would not be configured properly (:uv:bug:`58116`).


.. _changelog-ucsschool-2025-03-10:

Released on 2025-03-10
======================

Source package *ucs-school-metapackage* in version ``13.0.19``:

* Updated: In preparation for the UCS@school 5.2 update, two join hooks are now installed in the system. The first uses Python 2.7 and is registered for UCS 4.4 systems only. The second uses Python 3 and is registered in the LDAP for UCS 5.0 and newer (:uv:bug:`57897`).

Source package *ucs-school-import-lusd* in version ``1.0.5``:

* Fixed: The default value for the LUSD ``issuer``, used for authentication, has been changed for production use (:uv:bug:`57974`).
