.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-deployment:

**********
Deployment
**********

Für den Betrieb von |UCSUAS| gibt es zwei grundlegende Topologien. Die
Installation beider Varianten beschreibt
:external+uv-ucsschool-manual:ref:`structure-distribution`.

.. _arch-deployment-single:

Single-Server
=============

Eine einzelne Schule kann auf einem |UCSPRIMARYDN| betrieben werden. Alle
relevanten Dienste liegen dann auf einem System.

.. _arch-deployment-single-fig:

.. figure:: /images/arch-deployment-single.*
   :alt: Primary Directory Node mit OpenLDAP, UDM, UMC und
         UCS@school-Komponenten sowie den zugreifenden Clients

   Single-Server-Umgebung

.. _arch-deployment-multi:

Multi-Server
============

Für Schulträger oder größere Umgebungen wird ein zentraler |UCSPRIMARYDN| mit
Schulservern je Standort genutzt.

.. _arch-deployment-multi-fig:

.. figure:: /images/arch-deployment-multi.*
   :alt: Zentraler Primary Directory Node mit optionalem Backup Directory Node
         und selektiver LDAP-Replikation auf die Schulserver zweier Schulen

   Multi-Server-Umgebung

.. _arch-deployment-networks:

Edukativnetz und Verwaltungsnetz
================================

|UCSUAS| kann Edukativ- und Verwaltungsnetz logisch und physisch trennen. Dabei
können getrennte Schulserver und Subnetze eingesetzt werden. Die Replikation
unterscheidet dann zusätzlich nach Benutzerrollen. Die Details dazu enthält
:external+uv-ucsschool-manual:ref:`structure-edunet-vs-adminnet`.

.. important::

   Für neue Umgebungen prüfen Sie kritisch, ob ein separates Verwaltungsnetz
   tatsächlich noch benötigt wird. Mitarbeiter-Benutzerkonten können auf
   Edukativ-Systeme repliziert werden, siehe
   :external+uv-ucsschool-manual:ref:`structure-staff-in-edunet`.

   Häufig ist es robuster, für eine Schule getrennte Schul-OUs zu modellieren,
   zum Beispiel eine OU für die Verwaltung und eine zweite OU für den edukativen
   Bereich. Dieses Muster bietet mehr |UCSUAS|-Funktionalität, ist besser
   integriert und typischerweise besser getestet als neue getrennte
   Verwaltungsnetz-Topologien.

.. _arch-deployment-schoolserver:

Schulserver
===========

Schulserver sind lokale |UCSREPLICADN|-Systeme. Sie bieten lokale LDAP-Abfragen
und standortnahe Dienste, etwa Anmeldung, Datei- und Druckdienste, Fileshares für
Benutzer, Klassen und Arbeitsgruppen sowie je nach Installation Proxy oder
RADIUS.

.. _arch-deployment-limits:

Einschränkungen und Hinweise
============================

Bei der Planung einer Topologie beachten Sie die folgenden Punkte:

* Pro Standort wird für Edukativ- und Verwaltungsnetz jeweils nur ein
  Schulserver unterstützt.

* Eine Schule darf nur auf einen Schulserver repliziert werden.

* Mehrere Schulen können sich in bestimmten Szenarien einen Schulserver teilen,
  jedoch mit Einschränkungen, siehe
  :external+uv-ucsschool-manual:ref:`structure-ou-schoolserver-multiple-ous`.

* Neue Verwaltungsnetz-Implementierungen vermeiden Sie, wenn sich die fachliche
  Trennung sauber über getrennte Schul-OUs und die Replikation von
  Mitarbeiter-Benutzerkonten auf Edukativ-Systeme abbilden lässt.
