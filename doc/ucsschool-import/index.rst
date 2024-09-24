.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _audience:
.. _introduction:

###################################################
UCS\@school - Handbuch zur CLI-Import Schnittstelle
###################################################

Dieses Handbuch richtet sich an Administratoren und Programmierer. Die
Importsoftware ist im Auslieferungszustand stark konfigurierbar, kann aber
zusätzlich programmatisch erweitert werden. In diesem Handbuch werden der Ablauf
eines Importvorganges, Konfigurationsoptionen und Programmierschnittstellen
beschrieben.

|UCSUAS| bringt für viele regelmäßig wiederkehrende Verwaltungsaufgaben
Werkzeuge und Schnittstellen mit. Die Übernahme von Benutzerdaten aus der
Schulverwaltung ist eine dieser wiederkehrenden Aufgaben, die über die neue
Importschnittstelle für Benutzer automatisiert erledigt werden kann.

Der |UCSUAS| Import ermöglicht es Benutzerdaten aus einer Datei auszulesen, die
Daten zu normieren, automatisch eindeutige Benutzernamen und E-Mail-Adressen zu
generieren und notwendige Änderungen (Hinzufügen/Modifizieren/Löschen)
automatisch zu erkennen. Er wurde so konzipiert, dass die Konten einer UCS
Domäne automatisch mit dem Datenbestand eines vorhandenen Benutzerverzeichnisses
abgeglichen werden können.

Die Importschnittstelle ist darauf ausgelegt, mit möglichst geringem Aufwand an
die unterschiedlichen Gegebenheiten in Schulen angepasst zu werden. So ist die
Basis der Importschnittstelle bereits vorbereitet, um unterschiedliche
Dateiformate einlesen zu können. |UCSUAS| bringt einen Importfilter für
CSV-Dateien mit, der für unterschiedlichste CSV-Formate konfiguriert werden
kann.

Über eigene Python-Plugins kann die Schnittstelle erheblich erweitert werden.
Dies umfasst sowohl die Unterstützung für zusätzliche Dateiformate als auch die
Implementierung von zusätzlichen Automatismen, die während des Imports greifen.

In den nachfolgenden Kapiteln werden der Ablauf eines Imports, die
unterschiedlichen Konfigurationsmöglichkeiten sowie die
Erweiterungsmöglichkeiten der Schnittstelle um neue Funktionalitäten
beschrieben.

.. toctree::
   :numbered:

   procedure
   configuration/index
   school-change
   year-change
   spanning-accounts
   extending
   lusd
   bibliography
   indices
