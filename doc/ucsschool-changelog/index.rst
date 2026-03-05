.. SPDX-FileCopyrightText: 2021-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.2v4 to 5.2v5.

The change information for previous version jumps can be found at :external+uv-navigation:ref:`the changelog overview page <ucsschool-changelog>`.

.. _changelog-new-role:

Maintenance release to enforce an updated ID Connector
======================================================
|UCSUAS| 5.2v5 adds a preinstallation hook to enforce an updated ID Connector.

What's new?

* Together with the 4.0.0 release of the ID Connector, administrators can now push legal guardians to the ID Broker.
* Together with the Apple School Manager Connector 5.1.1, administrators can now install the Apple School Manager Connector on a central replica node.
* Users now get an error message on the UMC if they reset a password and it fails the dictionary word policy.

.. warning::

  If you have the ID Connector App installed, you must first update it, before updating to |UCSUAS| 5.2v5

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
