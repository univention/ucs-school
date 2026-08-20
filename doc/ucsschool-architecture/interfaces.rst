.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-interfaces:

**************
Schnittstellen
**************

.. _arch-interfaces-overview:

Überblick
=========

Die folgende Übersicht zeigt die Schnittstellen, über die eine
|UCSUAS|-Umgebung Daten mit Benutzern, Clients und externen Systemen
austauscht.

.. _arch-interfaces-overview-table:

.. list-table:: Schnittstellen einer |UCSUAS|-Umgebung
   :header-rows: 1
   :widths: 4 6

   * - Schnittstelle
     - Typische Nutzung

   * - UDM REST API
     - Schreiben und Lesen von IAM- und Verzeichnisobjekten mit Geschäftslogik

   * - Kelvin REST API
     - Zugriff von Partnern und Fachverfahren auf |UCSUAS|-Objekte

   * - LDAP und LDAPS
     - Lesen, Authentifizierung, interne Synchronisation

   * - Provisioning Events
     - Reaktion auf Verzeichnisänderungen

   * - SAML, OIDC und OAuth 2.0
     - Authentifizierung und Single Sign-on über den Identity Provider

   * - |UCSUMC| und Management-Oberfläche
     - interaktive Administration

   * - SMB und Samba
     - Windows-Anmeldung, Datei- und Druckdienste

   * - Fileshares
     - Austausch von Dateien, Klassen- und Arbeitsgruppenfreigaben sowie
       Materialverteilung

   * - RADIUS
     - WLAN-Authentifizierung

   * - Proxy
     - Steuerung und Filterung von Internetzugriffen

   * - CSV- und Dateiimport
     - Übernahme von Schuldaten aus externen Systemen

.. _arch-interfaces-write-path:

Schreibpfad für Verzeichnisobjekte
==================================

Schreibende Zugriffe durchlaufen die Fachlogik von |UCSUAS| und die
Geschäftslogik von UDM, bevor sie im Verzeichnisdienst landen.

.. _arch-interfaces-write-path-fig:

.. figure:: /images/arch-write-path.*
   :alt: Sequenzdiagramm eines Schreibzugriffs von einem Client über die
         Kelvin API, die UCS@school-Fachlogik und die UDM REST API bis zu
         OpenLDAP und zurück

   Schreibpfad für Verzeichnisobjekte

.. _arch-interfaces-integration-notes:

Integrationshinweise
====================

Für die Anbindung externer Systeme gelten die folgenden Hinweise:

* Für Schreiboperationen auf Objekten der |UCSUAS|-Domäne verwenden Sie die
  Kelvin REST API.

* Die UDM REST API ist die generische Schreibschnittstelle für
  UCS/Nubus-Objekte. Bei |UCSUAS|-Objekten reicht UDM-Wissen allein nicht aus,
  weil zusätzlich die |UCSUAS|-Domänenlogik, Rollen, OU-Strukturen, Gruppen,
  Freigaben und Seiteneffekte berücksichtigt werden müssen.

* Direkte LDAP-Schreibzugriffe sind architektonisch kritisch, weil sie
  Geschäftslogik und Konsistenzprüfungen umgehen können.

* Der gleiche Vorbehalt gilt für direkte UDM-Schreibzugriffe in der
  |UCSUAS|-Domäne, wenn die aufrufende Komponente die |UCSUAS|-Domänenlogik
  nicht vollständig abbildet.

* Für externe Systeme sind Kelvin REST API, UDM REST API und Provisioning Events
  die wichtigsten Integrationspunkte.

.. _arch-interfaces-fileshares:

Fileshares als Schnittstelle
============================

Fileshares sind in |UCSUAS| nicht nur Infrastruktur, sondern auch eine fachliche
Schnittstelle für schulische Arbeitsprozesse. |UCSUAS| verwendet sie unter
anderem für Benutzerablagen, Klassen- und Arbeitsgruppenfreigaben sowie für die
Materialverteilung.

.. _arch-interfaces-fileshares-fig:

.. figure:: /images/arch-fileshares.*
   :alt: Zugriff einer Lehrkraft über ein UCS@school-UMC-Modul auf eine
         Freigabe, die Klassen und Arbeitsgruppen mit Schülerinnen und Schülern
         verbindet

   Fileshares als fachliche Schnittstelle

Architektonisch sind dabei die folgenden Punkte relevant:

* Zugriffe auf Freigaben werden über Benutzer- und Gruppenmitgliedschaften im
  IAM gesteuert.

* Freigabeobjekte sind im LDAP-Modell der Schul-OU verankert, zum Beispiel
  unterhalb von ``cn=shares``.

* Die tatsächliche Dateiübertragung erfolgt über SMB beziehungsweise Samba oder
  über Dateiservermechanismen.

* Die Materialverteilung nutzt diese Dateischnittstelle fachlich, auch wenn
  Verwaltung und Berechtigungen über die |UCSUAS|-Logik und die IAM-Daten
  gesteuert werden.

* Für Partnerintegrationen können Fileshares relevant sein, wenn Systeme Dateien
  bereitstellen, abholen oder schulische Austauschordner nutzen sollen.
