.. SPDX-FileCopyrightText: 2021-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.2v6 to 5.2v7.

The change information for previous version jumps can be found at :external+uv-navigation:ref:`the changelog overview page <ucsschool-changelog>`.

.. _changelog-new-role:

Release 5.2v7
=============

What's new?

* The UCS@school UMC modules can now identify users by their primary email address instead of their username, controlled by the new UCR variable ``ucsschool/umc/show-email-instead-of-username``. Independently of this variable, user searches now always match the primary email address as well.

.. _changelog-show-email:

Showing the primary email address instead of the username
---------------------------------------------------------

By default, the UCS@school UMC modules identify users by their username, for example ``Doe, John (jdoe)``.
Environments that use the email address as the primary identifier for their users can now switch the displayed identifier by setting the new UCR variable ``ucsschool/umc/show-email-instead-of-username``:

.. code-block:: console

   $ ucr set ucsschool/umc/show-email-instead-of-username=yes

When the variable is set, the affected views show the primary email address in place of the username, for example ``Doe, John (john.doe@example.com)``.
Users without a primary email address keep being shown with their username.

The setting changes the user identifier in the following UCS@school UMC modules:

* *Passwords (students)* and *Passwords (teachers)* – the *User* column,
* the class and workgroup modules (*Assign teachers*, *Assign classes*, *Edit/Administrate workgroups*) – the *Name* column and the member selection (``MultiObjectSelect``) dialogs,
* the school wizards (*Users (schools)*) – the *Name* column and the "add user" labels, which now additionally include the user's full name

.. note::

   The user search now matches the primary email address as well, **independently** of this variable: search-by-email is always active and is not controlled by ``ucsschool/umc/show-email-instead-of-username``.
   Administrators can therefore filter user lists by email address whether or not the email address is displayed.
   The variable only affects how users are *displayed*; it changes neither the username nor any authentication behavior.

.. _changelog-prepare:

General notes on the update
===========================

During the update, services within the domain may fail. For this reason, the
update should be performed within a maintenance window. It is generally
recommended to install and test the update in a test environment first. The test
environment should be identical to the production environment.

Please note that depending on the size of the |UCSUAS| environment,
this update may take longer than usual to complete.

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
