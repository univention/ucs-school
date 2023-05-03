.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-performance-general:

**************************************
Hinweise für große |UCSUAS|-Umgebungen
**************************************

Die Standardkonfiguration von |UCSUCS| und |UCSUAS| ist für Umgebungen mit
bis zu 5.000 Benutzern optimiert worden. In größeren Umgebungen kann es
notwendig werden, Anpassungen an der Standardkonfiguration vorzunehmen.
Die meisten Schritte werden bereits in :cite:t:`ucs-performance-guide`
beschrieben.

Darüber hinaus sollten einige Punkte bereits bei der Planung und dem Aufbau
einer |UCSUAS|-Umgebung beachtet werden:

* Durch die Verwendung einer Multi-Server-Umgebung und einer geeigneten
  Unterteilung der Benutzerkonten auf mehrere Schul-OUs kann die Last der
  einzelnen Schulserver bei einer großen Gesamtanzahl an Benutzern erheblich
  reduziert werden. Zusätzlich wird durch die Unterteilung für die Nutzer das
  Bedienen der |UCSUAS|-Systeme erleichtert, da zum Beispiel die Menge der
  angezeigten Benutzer, Klassen, Räume usw. auf die jeweilige Schul-OU
  eingeschränkt wird.

* Gruppen mit einer großen Anzahl an Mitgliedern können negative Auswirkungen
  auf die Geschwindigkeit der |UCSUAS|-Systeme haben. Es sollte daher beim
  Anlegen von Benutzern vermieden werden, dass alle Benutzer Mitglied einer
  bestimmten Gruppe (z.B. ``Domain Users``) werden. Die |UCSUAS|-Importskripte
  beachten dies bereits und legen pro Schul-OU eine eigene Gruppe :samp:`Domain
  Users {OUNAME}` an, die als primäre Gruppe für die Benutzerkonten verwendet
  wird.

  Falls für die Rechteverwaltung eine Zusammenfassung der Benutzer notwendig
  ist, können mehrere dieser Gruppen über die *Gruppen in
  Gruppen*-Funktionalität zusammengeführt werden. Die einzelnen :samp:`Domain
  User {OUNAME}`-Gruppen können dann bei Bedarf z.B. als Mitglied in der Gruppe
  ``Domain Users`` eingetragen werden.

.. _school-performance-scaling:

Skalierung von |UCSUAS| Samba 4 Umgebungen
==========================================

.. note::

   Bei |UCSUAS| muss das Backend für BIND zwingend auf Samba 4 gesetzt
   sein (UCR-Variable :envvar:`dns/backend` ``= samba4``).

.. _school-performance-additional-managed-node:

Installation zusätzlicher |UCSMANAGEDNODE| Server
-------------------------------------------------

In |UCSUAS| Umgebungen in denen Samba 4 Active Directory kompatible Dienste
bereitstellt, kann ein zusätzlicher |UCSMANAGEDNODE|-Server an einem
Schulstandort installiert werden.

Um einen solchen zusätzlichen |UCSMANAGEDNODE|-Server an einem Schulstandort zu
installieren und zu joinen, müssen vorbereitende Schritte durchgeführt werden:

#. Für den neuen |UCSMANAGEDNODE|-Server muss im Container ``cn=computers`` der
   gewünschten Schul-OU ein Rechnerobjekt angelegt werden. Der Name des
   Rechnerobjekts muss mit dem Hostnamen übereinstimmen, mit dem der neue
   |UCSMANAGEDNODE|-Server installiert wurde.

#. Der |UCSMANAGEDNODE|-Server muss in die Gruppen ``Member-Edukativnetz`` und
   :samp:`OU{OUNAME}-Member-Edukativnetz` aufgenommen werden.

#. Im |UCSUDM| sollte eine |UCSUCR| Richtlinie angelegt werden, die die
   UCR-Variable :envvar:`ldap/server/name` auf den Namen des gewünschten
   Schulservers setzt. Diese |UCSUCR| Richtlinie sollte dann mit der gewünschten
   Schul-OU oder mit dem Container verknüpft werden, in dem das Rechnerobjekt
   des |UCSMANAGEDNODE|-Servers positioniert ist.

#. Auf dem |UCSMANAGEDNODE|-Server selbst muss vor dem Domänenbeitritt die
   UCR-Variable :envvar:`nameserver1` auf die IP-Adresse des Schulservers
   gesetzt werden. Die UCR-Variablen :envvar:`nameserver2` und
   :envvar:`nameserver3` dürfen nicht gesetzt sein.

#. Nach diesen Schritten kann der |UCSMANAGEDNODE|-Server wie gewohnt der Domäne
   beitreten.

.. _school-performance-autosearch:

Automatische Suche deaktivieren
-------------------------------

Standardmäßig wird beim Öffnen von Modulen der Univention Management Console
eine Suche nach allen Objekten durchgeführt. Je nach Größe der Umgebung kann das
sehr lange dauern, wenn kein Suchfilter angegeben wird. Dieses Verhalten kann
durch Setzen der folgenden |UCSUCRV|\ n für die jeweiligen Module deaktiviert
werden.

Passwörter (Schüler), Passwörter (Lehrer), Passwörter (Mitarbeiter)
   :envvar:`ucsschool/passwordreset/autosearch`

Lehrer zuordnen
   :envvar:`ucsschool/assign-teachers/autosearch`

Klassen zuordnen
   :envvar:`ucsschool/assign-classes/autosearch`

Arbeitsgruppen verwalten
   :envvar:`ucsschool/workgroups/autosearch`

Benutzer
   :envvar:`ucsschool/wizards/schoolwizards/users/autosearch`

Klassen
   :envvar:`ucsschool/wizards/schoolwizards/classes/autosearch`

Rechner
   :envvar:`ucsschool/wizards/schoolwizards/computers/autosearch`

Schulen
   :envvar:`ucsschool/wizards/schoolwizards/schools/autosearch`

Benutzer/Klassen/Rechner/Schulen
   :envvar:`ucsschool/wizards/autosearch`

.. note::

   Wie die automatische Suche auch für andere (nicht schulbezogene) UMC-Module
   deaktiviert wird, steht in :ref:`umc-search-auto` in
   :cite:t:`ucs-performance-guide` (nur in Englisch verfügbar).
