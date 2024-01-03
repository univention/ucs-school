.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.0 v3 to 5.0 v4.

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

.. _changelog-windows-naming-conventions:

Change in the Windows naming conventions
========================================

In Windows there are some usernames that are reserved for
`special use <https://learn.microsoft.com/en-us/troubleshoot/windows-server/identity/naming-conventions-for-computer-domain-site-ou>`_.
Using a `username schema <https://docs.software-univention.de/ucsschool-import/latest/de/configuration/scheme-formatting.html>`_
for the import can lead to invalid usernames in Windows.
If this happens, this can lead to errors in Windows
environments, such as users being unable to login.

We have added username validation when importing users, to prevent such
invalid usernames from occurring. However, administrators can disable this
check using the ``ucsschool/validation/username/windows-check`` UCR variable.
When the variable is set to ``true``, the import will check if usernames are
valid for Windows. If you have only Linux systems, you may choose to disable
this check.

The join script for this release will scan your usernames for invalid usernames.
If none are found, it will set the ``ucsschool/validation/username/windows-check``
UCR variable to ``true``, so you can start getting the benefit of the checks right
away.

If you have any invalid usernames, the join script will leave the UCR variable
unset. You may choose to do one of the following:

#. Use the System Diagnostic UMC module to see a list of invalid usernames and correct them, then set the ``ucsschool/validation/username/windows-check`` UCR variable to ``true``.
#. Set the ``ucsschool/validation/username/windows-check`` UCR variable to ``false``, to temporarily ignore invalid usernames for this minor release.

After the join script runs, you may update the UCR variable at any time before
running a user import. You may also run the diagnostic for invalid usernames
at any time using the System Diagnostic UMC module.

.. warning::

   In UCS 5.2, which will be the next minor release, invalid Windows usernames
   will no longer be allowed in any UCS\@school system, including domains that
   only have Linux machines. Please check your usernames with the System
   Diagnostic UMC module and fix any that are invalid, before doing the upgrade.

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
