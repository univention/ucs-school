.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-data-model:

***********
Datenmodell
***********

.. _arch-data-model-idea:

Grundidee
=========

|UCSUAS| bildet jede Schule als eigene Organisationseinheit (OU) im
LDAP-Verzeichnis ab. Unterhalb der Schul-OU liegen Container für Benutzer,
Gruppen, Rechner, Freigaben und weitere schulbezogene Objekte. Die vollständige
Beschreibung der LDAP-Struktur enthält
:external+uv-ucsschool-manual:ref:`structure-ldap-ou`.

.. _arch-data-model-example:

Beispielstruktur
================

Das folgende Beispiel zeigt die Container unterhalb der OU einer Schule mit dem
OU-Kürzel ``gymmitte``:

.. code-block::

   ou=gymmitte,dc=example,dc=com
   ├─ cn=users
   │  ├─ cn=schueler
   │  ├─ cn=lehrer
   │  ├─ cn=lehrer und mitarbeiter
   │  ├─ cn=mitarbeiter
   │  └─ cn=admins
   ├─ cn=groups
   │  ├─ cn=schueler
   │  │  └─ cn=klassen
   │  └─ cn=raeume
   ├─ cn=computers
   ├─ cn=shares
   │  └─ cn=klassen
   ├─ cn=examusers
   ├─ cn=dhcp
   ├─ cn=networks
   ├─ cn=policies
   └─ cn=printers

.. _arch-data-model-roles:

Rollen
======

Jeder Benutzer in einer |UCSUAS|-Umgebung ist einer Rolle zugeordnet, aus der
sich die Berechtigungen in der Verwaltung ergeben. Die Rollen und ihre
Berechtigungen beschreibt
:external+uv-ucsschool-manual:ref:`structure-userroles` im Detail.

.. _arch-data-model-roles-table:

.. list-table:: Rollen in |UCSUAS|
   :header-rows: 1
   :widths: 4 6

   * - Rolle
     - Bedeutung

   * - Schüler
     - Standardnutzer im Unterrichtskontext

   * - Lehrer
     - erweiterte Rechte für Unterrichtsfunktionen und ausgewählte UMC-Module

   * - Sorgeberechtigte
     - Beziehung zu Schülern, ohne Standardzugriff auf die Administration

   * - Mitarbeiter
     - Rolle für Schulverwaltung und Verwaltungsnetz

   * - Schuladministrator
     - administrative Rechte innerhalb der jeweiligen Schule

   * - System-Administrator
     - voller administrativer Zugriff auf die |UCSUAS|-Systeme

.. _arch-data-model-groups:

Globale Steuergruppen
=====================

|UCSUAS| legt zusätzliche Gruppen zur Steuerung von Replikation, Zugriff und
Schulserver-Zuordnung an. Dazu gehören globale Gruppen für Edukativ- und
Verwaltungsnetz sowie OU-spezifische Gruppen. Die Übersicht der globalen Objekte
enthält :external+uv-ucsschool-manual:ref:`structure-ldap-global`.

.. _arch-data-model-rule:

Wichtige Modellierungsregel
===========================

Die Schul-OU ist die zentrale fachliche Klammer. Viele Namen für Gruppen,
Freigaben und Rechner leiten sich aus dem OU-Kürzel ab. Änderungen am OU-Kürzel
wirken sich deshalb auf zahlreiche abgeleitete Objekte aus.
