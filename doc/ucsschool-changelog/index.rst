.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-main:

***************
|UCSUAS|-Update
***************

This document contains the changelogs with the detailed change information for
the update of |UCSUAS| from version 5.0 v2 to 5.0 v3.

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

.. _changelog-veyon-update:

Update of the software for control and monitoring of computer rooms
===================================================================

The performance and stability of computer room monitoring has been improved with
|UCSUAS| 5.0 v3.

.. caution::

   The application :program:`UCS\@school Veyon Proxy` from the App Center must
   be updated to ``4.7.4.6``. In addition, the Windows computers must be
   equipped with the suitable *Veyon* application. A suitable version is supplied
   with |UCSUAS| (4.7.4), and can be installed as described in
   :external+uv-ucsschool-admin:ref:`school-windows-veyon`.

The status indicators of the computer room module page can be updated with a
delay of up to one minute. This is a known issue and will be corrected soon with
an errata update.

Depending on the available hardware, bandwidth, and number of PCs in the
computer room, it may be necessary to make fine adjustments to Presentation Mode
if performance is not satisfactory. See the :uv:help:`Quick Start Guide:
Improving Presentation Mode Performance <20264>`.

This release also removes the update lock for systems with computer rooms. Thus,
systems can be updated from UCS 4.4 to UCS 5.0 if all computer rooms on the
system have been migrated to *Veyon*.

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
