.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-layers:

***************
Schichtenmodell
***************

Die Architektur von |UCSUAS| lässt sich in vier Schichten gliedern. Jede Schicht
nutzt die Fähigkeiten der darunterliegenden Schicht.

.. _arch-layers-fig:

.. figure:: /images/arch-layers.*
   :alt: Vier Schichten von den schulischen Anwendungen über die
         UCS@school-Erweiterungen und die UCS/Nubus-Plattform bis zur
         Infrastruktur

   Schichtenmodell von |UCSUAS|

.. _arch-layers-infrastructure:

Infrastruktur- und Betriebsbasis
================================

Diese Schicht umfasst die UCS-Domäne, Serverrollen, LDAP-Replikation,
Samba/AD-nahe Dienste, DNS/DHCP, Zertifikate, |UCSAPPC| und bei Nubus for
Kubernetes die Kubernetes-Betriebsumgebung.

.. _arch-layers-platform:

UCS/Nubus IAM- und Management-Plattform
=======================================

Diese Schicht stellt generische Fähigkeiten bereit: Identity Store, Directory
Manager, Management-Oberfläche, Portal, Identity Provider, Self Service,
Provisionierung und Connector-Konzepte.

.. _arch-layers-ucsschool:

|UCSUAS|-Erweiterungen
======================

Diese Schicht ergänzt schulische Rollen, Schul-OUs, Klassen, Arbeitsgruppen,
Räume, Prüfungsbenutzer, Schulserver-Zuordnungen, Importlogik und UMC-Module.

.. _arch-layers-applications:

Schulische Anwendungen und Integrationen
========================================

Diese Schicht umfasst die Kelvin REST API, CSV-Importe, Fachverfahren, Veyon,
RADIUS, Proxy, Windows-/Samba-Clients und weitere Partnerintegrationen.

.. _arch-layers-delimitation:

Abgrenzung
==========

Die folgende Gegenüberstellung zeigt, welche Fähigkeiten aus der
UCS/Nubus-Plattform stammen und welche |UCSUAS| ergänzt.

.. _arch-layers-delimitation-table:

.. list-table:: Abgrenzung zwischen UCS/Nubus und |UCSUAS|
   :header-rows: 1
   :widths: 5 5

   * - UCS/Nubus
     - |UCSUAS|

   * - generisches IAM und Domänenmodell
     - schulisches Rollen- und Objektmodell

   * - UDM, UDM REST API, OpenLDAP
     - Schul-OUs, Klassen, Räume, Prüfungsmodus

   * - Management-Oberfläche und |UCSUMC|
     - schulspezifische UMC-Module

   * - Provisionierung und Connectoren
     - Schulimport und Kelvin REST API

   * - Serverrollen und Replikation
     - selektive Standort- und Schulserver-Replikation
