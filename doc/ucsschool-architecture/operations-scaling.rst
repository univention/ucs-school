.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-operations:

***********************
Betrieb und Skalierung
***********************

.. _arch-operations-dimensions:

Skalierungsachsen
=================

Die folgenden Größen bestimmen die Dimensionierung einer |UCSUAS|-Umgebung:

* Anzahl der Schulen

* Anzahl der Benutzer

* Anzahl der Clients

* Anzahl der Standorte

* Lese- und Schreiblast auf den Verzeichnisdiensten

* Anzahl der externen Integrationen

Hinweise zur Dimensionierung großer Umgebungen enthält
:external+uv-ucsschool-manual:ref:`school-performance-scaling`.

.. _arch-operations-mechanisms:

Relevante Architekturmechanismen
================================

Die Architektur bietet die folgenden Mechanismen, um Last zu verteilen und
Datenmengen zu begrenzen.

.. _arch-operations-mechanisms-table:

.. list-table:: Architekturmechanismen und ihre Wirkung
   :header-rows: 1
   :widths: 4 6

   * - Mechanismus
     - Wirkung

   * - Schulserver
     - lokale Dienste und lokale LDAP-Abfragen am Standort

   * - selektive Replikation
     - Begrenzung der Datenmenge pro Schulserver

   * - Kelvin REST API
     - bevorzugte Schreibschnittstelle für |UCSUAS|-Objekte

   * - UDM REST API
     - generische Schreibschnittstelle für UCS/Nubus-Objekte

   * - Provisioning Events
     - Entkopplung der Folgeverarbeitung

   * - SQL-Lesecache von Kelvin v2
     - Entlastung des Lesepfads für |UCSUAS|-Objekte

.. _arch-operations-risks:

Betriebsrisiken
===============

Im Betrieb sind die folgenden Risiken relevant:

* Direkte LDAP-Schreibzugriffe können Konsistenzregeln umgehen.

* Direkte UDM-Schreibzugriffe auf |UCSUAS|-Objekte können ebenfalls Konsistenz-
  oder Fachlogik umgehen, wenn sie die |UCSUAS|-Domänenlogik nicht vollständig
  berücksichtigen.

* Falsch modellierte OUs oder Gruppen können Replikation und Berechtigungen
  beeinträchtigen.

* Externe Integrationen brauchen eine klare Zuständigkeit für die führenden
  Datenquellen.

* Schulserver-Topologien müssen die dokumentierten Einschränkungen beachten,
  siehe :ref:`arch-deployment-limits`.

.. _arch-operations-recommendations:

Empfehlungen
============

Für Planung und Betrieb gelten die folgenden Empfehlungen:

* Realisieren Sie schreibende Partnerintegrationen für |UCSUAS|-Objekte
  bevorzugt über die Kelvin REST API.

* Verwenden Sie die UDM REST API für generische UCS/Nubus-Objekte. Für
  |UCSUAS|-Objekte setzen Sie sie nur dann ein, wenn die |UCSUAS|-Domänenlogik
  vollständig bekannt und berücksichtigt ist.

* Dokumentieren Sie die Datenhoheit pro Objektart explizit.

* Planen Sie große Importe und Replikationsänderungen mit Wartungsfenstern.

* Nutzen Sie Provisioning Events für nachgelagerte Systeme, statt LDAP
  periodisch großflächig zu durchsuchen.
