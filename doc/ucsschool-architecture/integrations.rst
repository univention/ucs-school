.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-integrations:

*************
Integrationen
*************

.. _arch-integrations-target-picture:

Zielbild
========

Zentrale Dienste werden möglichst am IAM angebunden, statt eigene Benutzer- und
Gruppenbestände zu pflegen. UCS/Nubus stellt dafür Identität, Verzeichnis,
Authentifizierung, Provisionierung und Connector-Konzepte bereit. |UCSUAS|
ergänzt die schulischen Rollen, OUs, Klassen und Gruppen, die für
Bildungsdienste relevant sind.

.. _arch-integrations-target-picture-fig:

.. figure:: /images/arch-integrations.*
   :alt: Anbindung zentraler Dienste, Microsoft 365 und OX App Suite über
         Identity Provider und Provisionierung an das UCS/Nubus-IAM

   Anbindung zentraler Dienste an das IAM

.. _arch-integrations-m365:

Microsoft 365 Connector
=======================

Der Microsoft-365-Anwendungsfall ist typischerweise die Provisionierung von
Benutzern, Gruppen und gegebenenfalls Klassen- und Schulstrukturen in Richtung
Microsoft Cloud sowie die Anbindung der Anmeldung über ein vertrauenswürdiges
Identitätssystem.

Architektonisch sind die folgenden Punkte relevant:

* Das schulische Quellmodell liegt in |UCSUAS| beziehungsweise im angebundenen
  führenden Schulverwaltungssystem.

* UCS/Nubus stellt IAM-Objekte, Authentifizierung und Integrationsmechanismen
  bereit.

* Der Connector bildet |UCSUAS|- und IAM-Objekte auf Microsoft-365-Objekte ab.

* Datenhoheit und Synchronisationsrichtung müssen explizit beschrieben werden.

.. _arch-integrations-ox:

OX Connector
============

OX App Suite ist ein Beispiel für einen zentralen Dienst, der an das IAM
angebunden wird. Die Integration umfasst typischerweise die Provisionierung von
Benutzern und Gruppen sowie Single Sign-on beziehungsweise Authentifizierung
gegen den zentralen Identity Provider.

Architektonisch sind die folgenden Punkte relevant:

* Benutzer und Gruppen stammen aus UCS/Nubus beziehungsweise |UCSUAS|.

* Die Authentifizierung erfolgt über den zentralen Identity Provider, soweit das
  Zielsystem dies unterstützt.

* Änderungen an Schulobjekten werden über Provisionierung oder
  Connector-Mechanismen in OX wirksam.

.. _arch-integrations-central-services:

Zentrale Dienste am IAM anbinden
================================

Für zentrale Dienste gilt das folgende Zielmuster:

.. _arch-integrations-central-services-fig:

.. figure:: /images/arch-central-services.*
   :alt: Weg der Daten vom führenden System über Import, UCS@school-Fachlogik
         und IAM bis zu Single Sign-on und Provisionierung eines zentralen
         Dienstes

   Zielmuster für die Anbindung zentraler Dienste

.. _arch-integrations-decisions:

Integrationsentscheidungen
==========================

Für jeden zentralen Dienst dokumentieren Sie mindestens die folgenden
Entscheidungen:

.. _arch-integrations-decisions-table:

.. list-table:: Entscheidungen bei der Anbindung zentraler Dienste
   :header-rows: 1
   :widths: 4 6

   * - Frage
     - Bedeutung

   * - Führendes System
     - Wo entstehen Benutzer, Gruppen und Rollen fachlich?

   * - Synchronisationsrichtung
     - Nur aus UCS/Nubus heraus oder bidirektional?

   * - Authentifizierung
     - Lokal im Dienst oder zentral über den Identity Provider?

   * - Provisionierung
     - UDM REST API, Kelvin REST API, Provisioning Events oder spezifischer
       Connector?

   * - Objektabbildung
     - Wie werden Schulen, Klassen, Gruppen und Rollen abgebildet?

   * - Deprovisionierung
     - Was passiert bei Schulwechsel, Austritt oder Rollenwechsel?

.. _arch-integrations-classification:

Einordnung
==========

Microsoft 365 und OX App Suite sind keine Kernkomponenten von |UCSUAS|, sondern
angebundene Zielsysteme beziehungsweise zentrale Dienste. Die Architektur stellt
sie deshalb in der Integrationsschicht dar, nicht als Teil des
|UCSUAS|-Kerns (siehe :ref:`arch-layers-applications`).
