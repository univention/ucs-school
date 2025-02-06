.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-2025-03-11:


Released on 2025-03-11
======================

Source package *ucs-school-umc-exam* in version ``12.0.1``:

* Exam *shell* hooks are no longer supported. In UCS\@school 5.0 exam shell hooks that are stored in ``/usr/share/ucs-school-exam/hooks/create_exam_user_post.d/`` are run during the start of an exam for each exam user.
  This feature has been removed in UCS\@school 5.2.

  Please note: This change does not affect the *Python* hooks for the exam mode that are executed on the Primary Directory Node and are located in the directory ``/usr/share/ucs-school-exam-master/pyhooks/create_exam_user_pre/``.

Source package *ucs-school-metapackage* in version ``15.0.0``:

* Dropping support for Python 2.

Source package *ucs-school-lib* in version ``15.0.0``:

* The UCR-Variable ``ucsschool/validation/username/windows-check`` has been removed. UCS\@school user names are now always validated to comply with Windows naming conventions,
  it is no longer possible to deactivate this check. To prevent problems, conflicting usernames of existing users should be changed before starting the update to UCS\@school 5.2v1.

Source package *ucs-school-umc-diagnostic* in version ``4.0.0``:

* Usernames which do not comply with Windows naming conventions are now shown as critical errors in the system diagnostic tool.

