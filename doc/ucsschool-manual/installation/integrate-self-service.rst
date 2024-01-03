.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-installation-selfservice:

Integration mit Self-Service App
================================

Um die *Self-Service App* in einer |UCSUAS|-Umgebung einzusetzen, wird empfohlen
das Paket :program:`ucs-school-selfservice-support` auf dem |UCSPRIMARYDN| und
den |UCSBACKUPDN| zu installieren. Dies sorgt automatisch dafür, dass den
Benutzern aller Schulen, die in den Gruppen :samp:`Domain Users {OUNAME}`
Mitglied sind, die Benutzung des *Self-Service* Moduls erlaubt wird. Es wird
automatisch die UCR-Variable
:envvar:`umc/self-service/passwordreset/whitelist/groups` beim Erstellen von
neuen Schul-OUs aktuell gehalten.

Die Installation wird folgendermaßen durchgeführt:

.. code-block:: console

   $ univention-install ucs-school-selfservice-support
