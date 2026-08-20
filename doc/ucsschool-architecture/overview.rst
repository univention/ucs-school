.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-overview:

*********
Übersicht
*********

.. _arch-overview-summary:

Kurzfassung
===========

|UCSUAS| erweitert UCS/Nubus um schulische Fachobjekte, Rollen,
Benutzeroberflächen, Importmechanismen und Standortlogik. Der zentrale
technische Kern bleibt das UCS/Nubus-IAM mit OpenLDAP, |UCSUDM| (UDM),
|UCSUMC|, Identity Provider und Provisionierung.

.. _arch-overview-fig:

.. figure:: /images/arch-overview.*
   :alt: Zugriffskette von Benutzern über die Benutzeroberflächen und die
         UCS@school-Fachlogik bis zu OpenLDAP und den Schuldiensten

   Zugriffskette von den Benutzeroberflächen bis zum Verzeichnisdienst

.. _arch-overview-principles:

Zentrale Architekturprinzipien
==============================

Die Architektur von |UCSUAS| folgt diesen Prinzipien:

* OpenLDAP ist der zentrale Verzeichnisdienst für Identitäts- und
  Domänenobjekte.

* Schreibzugriffe erfolgen über UDM beziehungsweise die UDM REST API, weil dort
  Geschäftslogik und Konsistenzprüfungen liegen.

* |UCSUAS| ergänzt schulische Objektstrukturen unterhalb von Schul-OUs.

* Schulserver erhalten über selektive LDAP-Replikation nur die für den Standort
  relevanten Daten.

* Integrationen erfolgen bevorzugt über dokumentierte APIs und
  Provisionierungsmechanismen.

Die :ref:`arch-interfaces` und :ref:`arch-operations` beschreiben, welche
Konsequenzen sich aus diesen Prinzipien für Integrationen und den Betrieb
ergeben.
