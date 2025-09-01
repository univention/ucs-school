.. SPDX-FileCopyrightText: 2021-2025 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.2v3 to 5.2v4.

The change information for previous version jumps can be found at :external+uv-navigation:ref:`the changelog overview page <ucsschool-changelog>`.

.. _changelog-prepare:

General notes on the update
===========================

During the update, services within the domain may fail. For this reason, the
update should be performed within a maintenance window. It is generally
recommended to install and test the update in a test environment first. The test
environment should be identical to the production environment.

Please note that depending on the size of the |UCSUAS| environment,
this update may take longer than usual to complete.
This is because additional LDAP structures for new role Legal Guardians need to be created
and LDAP indices must be updated.

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

New |UCSUAS| role
====================
|UCSUAS| 5.2v4 adds a new role to |UCSUAS|: the Legal Guardian.

The new role "Legal Guardian" gives administrators the ability to assign legal guardians to students.
A legal guardian can be a parent or a person appointed by a court to care for a minor child.
This enables school authorities to maintain a single source of truth across all integrated applications
that require contact with legal guardians.
The centralized approach significantly enhances data consistency and security, especially in communication and service platforms
by avoiding data fragmentation across schools.

What's new?

* Administrators can create legal guardians in the UMC module “Users (Schools)”.
* Administrators can link legal guardians to students on the student detail page and students to Legal Guardians on the legal guardian detail page.
* Administrators can import legal guardians via CLI and web-based import and link them to existing students.
* The Kelvin API supports backward compatibility for reading, creating, and deleting guardians, as well as assigning guardians to existing students.
* A student can have up to 4 legal guardians assigned and a legal guardian can be assigned to up to 10 students.
