.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.0v7 or newer to 5.2v1.

If necessary, important notes about the update are covered in a separate
section. The change information for previous version jumps can be found at
https://docs.software-univention.de/.

.. _changelog-prepare:

General notes on the update
===========================

During the update, services within the domain may fail. For this reason, the
update should be performed within a maintenance window. It is generally
recommended to install and test the update in a test environment first. The test
environment should be identical to the production environment.


.. _important-notes:

Important notes about upgrading to |UCSUAS| 5.2v1
=================================================

Python 2 support has been removed
---------------------------------

The support for Python 2 was deprecated with the release of UCS 5.0 and is removed in UCS 5.2.
As a result, all UCS\@school Debian packages for Python 2 are removed with UCS\@school 5.2v1.
Any custom software that is not delivered by Univention and which
depends on UCS\@school packages will need to migrate to the UCS\@school Python 3 equivalent.

Windows naming conventions for user names are now enforced
----------------------------------------------------------

Since 5.0v3, UCS\@school user names are validated with respect to Windows naming conventions,
as user names which don't comply with Windows naming conventions lead to login issues and other problems
(see :uv:bug:`53519`).
This validation can be deactivated with the UCR-Variable ``ucsschool/validation/username/windows-check``.
With 5.2v1, the default of this variable has been changed: UCS\@school user names are now always validated to
comply with `Windows naming conventions <https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#naming-conventions>`_.
Before upgrading, check the system diagnostic tool for warnings about user names that do not comply with Windows naming conventions.
See the :external+uv-changelog-5.0v4:ref:`5.0v4 changelog <changelog-windows-naming-conventions>` for more information on this UCR-V in 5.0.

Exam shell hooks are removed
----------------------------

Before UCS\@school 5.2v1, during the start of an exam, exam shell hooks stored in ``/usr/share/ucs-school-exam/hooks/create_exam_user_post.d/`` were ran for each exam user.
This functionality has been removed in 5.2v1. Python hooks for the exam mode on the Primary Directory Node are not removed and are still available.
Check the directory ``/usr/share/ucs-school-exam/hooks/create_exam_user_post.d/`` for any custom hooks before upgrading.

.. _changelog-newerrata:

Update process
==============

Major updates for |UCSUAS| are released in the Univention App Center as a
standalone app update. Minor updates and bug fixes (errata for |UCSUAS|) that do
not require interaction with the administrator are released in the repository of
the already released app version of |UCSUAS|. The changelog documents that
Univention issues with each |UCSUAS| app version are then expanded accordingly
with a new section that shows which packages were released at what time and
which errors were fixed in the process.
