.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _ou-spanning-account:

*********************************
Schulübergreifende Benutzerkonten
*********************************

.. versionadded:: 4.1R2

   Seit |UCSUAS| 4.1 R2 werden schulübergreifende Benutzerkonten unterstützt.

Ein Benutzerobjekt existiert im LDAP-Verzeichnis nur einmal: an seiner primären
Schule (Attribut ``school``). An weitere, festgelegte Schulen (Attribut
``schools``) wird nur ein Ausschnitt des LDAP-Verzeichnisses seiner primären
Schule repliziert: sein Benutzerobjekt und die Standardgruppen.

Verlässt der Benutzer die Schule (durch Entfernen aus dem Attribut ``schools``),
so wird sein Benutzerobjekt dort gelöscht und nicht mehr dorthin repliziert. Bei
der Verwendung von schulübergreifenden Benutzerkonten gilt es einige Dinge zu
beachten.

Der Klassenarbeitsmodus und die Materialverteilung arbeiten grundsätzlich so,
dass sie auf dem Schulserver, an dem sie veranlasst wurden, die hochgeladenen
Dateien in die Heimatverzeichnisse der betroffenen Benutzer kopieren. Befindet
sich ein Heimatverzeichnis nicht auf dem Server, scheitert dies.

Windows-Clients verwenden das LDAP-Attribut ``homeDirectory`` (LDAP-Attribut
``sambaHomePath`` bzw. |UCSUDM|-Attribut ``sambahome``) um beim Einloggen das
Netzwerklaufwerk mit den Dokumenten des Benutzers einzubinden. Wenn die primäre
Schule eines Benutzers eine andere ist, als die, an der er gerade eine
Klassenarbeit schreiben soll, so existiert sein Heimatverzeichnis dort unter
Umständen nicht.

Es existieren drei Varianten des Umgangs mit dem |UCSUDM|-Attribut
``sambahome``, mit folgenden Vor- und Nachteilen:

1. ``sambahome`` wird regulär durch das Import-Skript gesetzt und nicht manuell
   verändert. ``sambahome`` ist dann immer ein Verzeichnis auf dem Schulserver
   der primären Schule des jeweiligen Benutzers.

   * Pro: Es existiert genau ein Heimatverzeichnis auf einem Server für alle
     Clients der Domäne, egal an welcher Schule.

   * Contra: Klassenarbeitsmodus und Materialverteilung funktionieren nicht an
     anderen Schulen als der primären Schule. Beim regulären Arbeiten gibt es
     ein hohes Datenaufkommen zwischen den Schulen.

2. ``sambahome`` wird durch das Import-Skript für alle auf einen (per |UCSUCR|)
   festgesetzten, zentralen, Server gesetzt.

   * Pro: wie bei 1.

   * Contra: wie bei 1.

3. ``sambahome`` wird durch das Import-Skript auf einen Server mit einem
   Alias-Namen gesetzt. Je nach dem, an welcher Schule sich der Benutzer
   befindet, bekommt er vom DNS-Server eine andere IP-Adresse für den gleichen
   Servernamen geliefert.

   * Pro: Klassenarbeitsmodus und Materialverteilung funktionieren, an der
     jeweiligen Schule an der sie stattfinden, für alle Benutzer - egal ob es
     ihre primäre Schule ist oder nicht. Kein Datenverkehr zwischen Schulen.

   * Contra: Es wird an jeder Schule eines Benutzers ein eigenes
     Heimatverzeichnis für ihn angelegt. Einmaliger Installationsaufwand: An
     jeder Schule müssen ein paar |UCSUCR|-Variablen eingestellt werden.

Es folgt eine Anleitung zur Einrichtung der dritten Variante.

.. _ou-spanning-account-sambahome:

Schulspezifisches ``sambahome``
===============================

Die folgenden Befehle müssen, mit angepassten Hostnamen und IP-Adressen, auf
jedem Schulserver ausgeführt werden:

.. code-block:: console

   # UCR Variablen verfügbar machen
   $ eval "$(ucr shell)"

   # Name (Alias) des Servers auf dem das Heimatverzeichnis liegt
   $ ucr set ucsschool/import/set/sambahome=schoolserver

   # DNS-Eintrag schoolserver.$domainname -> IP-Adresse des *jeweiligen* Schulservers
   $ ucr set "connector/s4/mapping/dns/host_record/schoolserver.$domainname/static/ipv4"=172.16.3.12

   # DNS-Eintrag aktivieren
   $ systemctl restart univention-s4-connector.service


Folgendes muss auf dem |UCSPRIMARYDN| ausgeführt werden:

.. code-block:: console

   # UCR Variablen verfügbar machen
   $ eval "$(ucr shell)"

   # Name (Alias) des Servers auf dem das Heimatverzeichnis liegt (wird vom Import ausgewertet)
   $ ucr set ucsschool/import/set/sambahome=schoolserver

   # DNS Forward-Eintrag einrichten (IP-Adresse eines zentralen Servers, z.B. des Primary Directory Node, verwenden)
   $ udm dns/host_record create \
       --superordinate "zoneName=$domainname,cn=dns,$ldap_base" \
       --set name=schoolserver \
       --set a=172.16.1.1


Der Befehl :command:`host schoolserver` sollte nun auf allen Schulservern die
IP-Adresse des jeweiligen Schulservers liefern. Mit :command:`nslookup
schoolserver` kann die gleiche DNS-Anfrage komfortabel an verschiedene
DNS-Server geschickt werden.
