.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-flows:

***********
Datenflüsse
***********

Dieses Kapitel beschreibt die wichtigsten Datenflüsse in einer
|UCSUAS|-Umgebung.

.. _arch-flows-import:

Benutzerimport
==============

Der Import übernimmt Benutzerdaten aus dem führenden System und schreibt sie
über die Fachlogik und UDM in den Verzeichnisdienst. Von dort gelangen sie über
die Replikation an die Schulstandorte.

.. _arch-flows-import-fig:

.. figure:: /images/arch-flow-import.*
   :alt: Datenfluss von der Schulverwaltung über den UCS@school-Import, die
         Fachlogik und die UDM REST API bis zu OpenLDAP und der
         Schulserver-Replikation

   Datenfluss beim Benutzerimport

Die Bedienung der Importschnittstelle beschreiben
:external+uv-ucsschool-manual:ref:`school-setup-cli` und
:cite:t:`ucsschool-import`.

.. _arch-flows-kelvin:

Lese- und Schreibpfad von Kelvin v2
===================================

Kelvin v2 trennt den Schreibpfad vom Lesepfad. Schreibende Zugriffe laufen über
die UDM REST API in das Verzeichnis. Lesende Zugriffe bedient der SQL-Lesecache,
den ein Provisioning Consumer aus den Provisioning Events aktualisiert.

.. _arch-flows-kelvin-fig:

.. figure:: /images/arch-flow-kelvin-v2.*
   :alt: Schreibpfad eines HTTP-Clients über die Kelvin REST API und die UDM
         REST API nach OpenLDAP sowie Lesepfad über den SQL-Lesecache, den ein
         Provisioning Consumer aktualisiert

   Lese- und Schreibpfad von Kelvin v2

.. _arch-flows-login:

Anmeldung am Schulstandort
==========================

Clients melden sich am Schulserver des Standorts an. Der Schulserver beantwortet
die Anfragen aus dem lokalen Replikatbestand und den lokalen Anmeldediensten.

.. _arch-flows-login-fig:

.. figure:: /images/arch-flow-login.*
   :alt: Anmeldung eines Benutzers über einen Windows- oder Linux-Client am
         Schulserver mit lokalem LDAP-Replikatbestand und Samba-Anmeldediensten

   Datenfluss bei der Anmeldung am Schulstandort

.. _arch-flows-material:

Materialverteilung über Fileshares
==================================

Die Materialverteilung verbindet fachliche Aktionen in |UCSUAS| mit der
Dateiablage auf Freigaben. Das IAM steuert, welche Benutzer und Gruppen Zugriff
auf die jeweiligen Freigaben erhalten.

.. _arch-flows-material-fig:

.. figure:: /images/arch-flow-material.*
   :alt: Materialverteilung durch eine Lehrkraft über IAM-Gruppen und
         Berechtigungen auf eine Klassen- oder Arbeitsgruppenfreigabe für
         Schülerinnen und Schüler

   Datenfluss bei der Materialverteilung

Die Einordnung der Freigaben als fachliche Schnittstelle beschreibt
:ref:`arch-interfaces-fileshares`.

.. _arch-flows-provisioning:

Provisionierung
===============

Änderungen im LDAP-Verzeichnis erzeugen Ereignisse, die Konsumenten nutzen
können. Beispiele sind die Aktualisierung des Portals, Self-Service-nahe
Prozesse oder die Aktualisierung des Kelvin-v2-Lesecaches.
