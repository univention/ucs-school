.. SPDX-FileCopyrightText: 2021-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.2v5 to 5.2v6.

The change information for previous version jumps can be found at :external+uv-navigation:ref:`the changelog overview page <ucsschool-changelog>`.

.. _changelog-new-role:

Maintenance release 5.2v6
=========================
|UCSUAS| 5.2v6 is a maintenance release with bug fixes.

What's new?

* The ``ucsschool_purge_timestamp.py`` hook has been updated to use the new ``map``/``unmap`` functions on UCS systems running version 5.2-6 and above. This fixes UMC issues in combination with delegated administration.
* Teachers can now reset passwords regardless of whether the student's account is locked.
* Join failures into domains that previously took part in an AD takeover are now fixed.

.. _changelog-hook-early:

Activating the updated purge timestamp hook early
-------------------------------------------------

.. note::

   UCS 5.2-5 Errata 416 is required on all systems in the domain to activate the hook early.

The updated ``ucsschool_purge_timestamp.py`` hook is automatically activated during the update to UCS 5.2-6.
To activate it on UCS 5.2-5 systems with the required errata applied, run the following commands:

.. code-block:: console

   $ udm settings/udm_hook modify \
       --set ucsversionend=5.2-4 \
       --dn "cn=ucsschool_purge_timestamp_525,cn=udm_hook,cn=univention,$(ucr get ldap/base)"
   $ udm settings/udm_hook modify \
       --set ucsversionstart=5.2-5 \
       --dn "cn=ucsschool_purge_timestamp,cn=udm_hook,cn=univention,$(ucr get ldap/base)"

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
