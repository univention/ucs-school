.. SPDX-FileCopyrightText: 2021-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.2v8 to 5.2v9.

The change information for previous version jumps can be found at :external+uv-navigation:ref:`the changelog overview page <ucsschool-changelog>`.

.. _changelog-edit-workgroups:

Release 5.2v9
=============

What's new?

* Teachers can again use the UMC module *Edit workgroups*,
  and the |UCSUAS| manual describes how to restrict teachers to this module
  (:uv:bug:`55267`).

.. _changelog-edit-workgroups-teachers:

Restricting teachers to editing workgroups
------------------------------------------

The UMC module *Edit workgroups* lets teachers add and remove the students of existing workgroups
and manage the email address of a workgroup,
without creating or deleting workgroups.
|UCSUAS| 5.2v9 fixes several errors that made the module unusable.

The UMC policy ``ucsschool-umc-teachers-default`` still allows teachers
both *Administrate workgroups* and *Edit workgroups*,
and the |UCSUMC| then shows only *Administrate workgroups*.
To restrict teachers to *Edit workgroups*,
create a UMC policy of your own without the operation set ``schoolgroups-workgroup-admin``
and link it to the teacher groups in place of ``ucsschool-umc-teachers-default``.
Don't change ``ucsschool-umc-teachers-default`` itself:
the join script of :program:`ucs-school-umc-groups` adds both operation sets to it again on every run.
The |UCSUCRV| :envvar:`ucsschool/ldap/default/policy/umc/teachers`
links a policy of your own to the teacher groups of new schools.
For the steps, see :external+uv-ucsschool-admin:ref:`school-setup-generic-configure-workgroup-teachers`.

The join script now resets the operation set ``schoolgroups-workgroup`` to the shipped commands on every run.
Commands that an administrator added to this operation set are removed.

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
