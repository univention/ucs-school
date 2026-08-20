.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-components:

***********
Komponenten
***********

.. _arch-components-platform:

UCS/Nubus-Komponenten
=====================

Die UCS/Nubus-Plattform stellt die folgenden generischen Komponenten bereit.

.. _arch-components-platform-table:

.. list-table:: Komponenten der UCS/Nubus-Plattform
   :header-rows: 1
   :widths: 4 6

   * - Komponente
     - Aufgabe

   * - Identity Store and Directory Service
     - OpenLDAP-basierte Persistenz für Benutzer, Gruppen und Assets

   * - Directory Manager und UDM REST API
     - Geschäftslogik und CRUD-Zugriff auf Verzeichnisobjekte

   * - Management-Oberfläche und |UCSUMC|
     - webbasierte Administration

   * - Identity Provider
     - Authentifizierung über Keycloak, SAML, OIDC und OAuth 2.0

   * - Portal Service
     - Einstiegspunkt und Integration der Benutzeroberflächen

   * - End User Self Service
     - Passwort- und Profildienste für Benutzer

   * - Provisioning Service
     - Ereignisse aus Verzeichnisänderungen für Konsumenten

   * - IAM Connector und Directory Importer
     - Anbindung externer IAM- und LDAP-Systeme

.. _arch-components-ucsschool:

|UCSUAS|-Komponenten
====================

|UCSUAS| ergänzt die Plattform um die folgenden Komponenten.

.. _arch-components-ucsschool-table:

.. list-table:: Komponenten von |UCSUAS|
   :header-rows: 1
   :widths: 4 6

   * - Komponente
     - Aufgabe

   * - |UCSUAS|-Bibliotheken
     - Fachlogik für Schulobjekte und Rollen

   * - Importskripte
     - CSV- beziehungsweise dateibasierter Import von Benutzern, Klassen,
       Rechnern und Netzwerken

   * - |UCSUAS|-UMC-Module
     - Verwaltung von Schulen, Benutzern, Klassen, Rechnern, Räumen und
       Unterrichtsfunktionen

   * - Kelvin REST API
     - HTTP-API für |UCSUAS|-Objekte

   * - Schulserver
     - lokaler |UCSREPLICADN| mit schulstandortbezogenen Diensten

   * - Klassenarbeitsmodus
     - temporäre Prüfungsumgebung mit Prüfungsbenutzern und Gruppen

Die Bedienung der UMC-Module und der Importskripte beschreibt
:cite:t:`ucsschool-admin`. Details zur dateibasierten Importschnittstelle
enthält :cite:t:`ucsschool-import`.

.. _arch-components-kelvin:

Kelvin REST API
===============

Kelvin stellt HTTP-Endpunkte zur Verwaltung von |UCSUAS|-Domänenobjekten bereit,
etwa Schulen, Schulbenutzer, Klassen und Computerräume. Die Konfiguration der
App beschreibt
:external+uv-ucsschool-manual:ref:`school-setup-kelvin-rest-api`.

.. _arch-components-kelvin-fig:

.. figure:: /images/arch-kelvin.*
   :alt: Zugriffspfad eines HTTP-Clients über die Kelvin REST API und die
         UCS@school-Bibliotheken bis zu OpenLDAP sowie Aktualisierung des
         SQL-Lesecache über Provisioning Events

   Einordnung der Kelvin REST API

Kelvin v1 liest und schreibt im Wesentlichen über die |UCSUAS|-Bibliotheken, die
UDM REST API und teilweise direkt über LDAP. Kelvin v2 ergänzt einen
SQL-Lesecache, der über Provisioning Events aktualisiert wird. Der
:ref:`arch-flows-kelvin` beschreibt die zugehörigen Lese- und Schreibpfade.
