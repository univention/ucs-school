.. SPDX-FileCopyrightText: 2021-2025 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog-changelogs:

*********
Changelog
*********

.. _changelog-ucsschool-2025-04-17:

Released on 2025-04-17
======================

Source package *univention-management-console-module-selective-udm* in version ``10.0.0``:

* Technical: This package was updated to conform with new versioning guidelines (:uv:bug:`58213`).

Source package *ucs-school-umc-computerroom* in version ``14.0.2``:

* Feature: When observing multiple student computers, the full width of the browser window is now used to display the screenshots (:uv:bug:`58165`).
* Fix: The zoomed in image on the "Watch" overview is now updated like the thumbnails.
  The styling has been adapted to always show the enlarged image in the center of the screen.
  The zoomed in image will now be shown after clicking on the thumbnail and not after a hovering on it (:uv:bug:`58160`).
* *Please note*: For the two changes mentioned above, adjustments were made to JavaScript and CSS files. Due to the caching of these files by the browser, the changes may not be visible immediately. It is therefore advisable to invalidate the browser cache. Otherwise it will take at least 1 hour before the web browsers request the new version of the files from the server.
