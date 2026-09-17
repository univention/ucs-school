.. SPDX-FileCopyrightText: 2021-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.2v7 to 5.2v8.

The change information for previous version jumps can be found at :external+uv-navigation:ref:`the changelog overview page <ucsschool-changelog>`.

.. _changelog-radius-rust-helper:

Release 5.2v8
=============

What's new?

* The RADIUS 802.1X integration now uses the rewritten
  :spelling:ignore:`univention-radius-ntlm-auth` helper from UCS 5.2-7 and no
  longer ships its own network access check (:uv:bug:`59894`).

.. _changelog-radius-internet-rules:

RADIUS 802.1X uses the rewritten NTLM authentication helper
-----------------------------------------------------------

|UCSUAS| 5.2v8 requires UCS 5.2-7,
which ships the rewritten :spelling:ignore:`univention-radius-ntlm-auth` helper.
The separate |UCSUAS| implementation of the network access check has been removed;
the helper evaluates the |UCSUAS| internet rules itself.

The package :program:`ucs-school-radius-802.1x` activates this evaluation through the
|UCSUCRV| :envvar:`freeradius/auth/helper/ntlm/network-access/internet-rules/enabled`.
The variable is set during the installation of the package and unset when the package is removed.
A value set by the administrator is kept during package updates.

The WLAN access decision itself does not change.
For more information, see :external+uv-ucsschool-admin:ref:`radius`.

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
