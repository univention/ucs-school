.. _school-setup-cli:

*****************************************
Verwaltung von Schulen über Importskripte
*****************************************

|UCSUAS| bietet für viele der regelmäßig wiederkehrenden Verwaltungsaufgaben
spezielle UMC-Module und Assistenten an, die beim Anlegen, Modifizieren und
Löschen von z.B. Schulen, Benutzerkonten und Rechnern unterstützen. Diese werden
in :ref:`school-setup-umc` beschrieben).

Ergänzend hierzu gibt es Programme für die Kommandozeile, die auch eine
automatisierte Pflege der |UCSUAS|-Umgebung zulassen und werden nachfolgend
beschrieben.

.. caution::

   Seit der |UCSUAS|-Version 3.2 R2 halten die kommandozeilenbasierten
   Importskripte zu Beginn des jeweiligen Imports den |UCSUDN| auf dem
   |UCSPRIMARYDN| an. Nach Abschluss des Imports wird der |UCSUDN| wieder
   gestartet.

.. _school-setup-cli-importusers:

Pflege von Benutzerkonten für Schüler, Lehrer und Mitarbeiter
=============================================================

Für |UCSUAS| gibt es momentan mehrere Möglichkeiten Nutzer in das System
zu importieren.

Die Konfiguration des kommandozeilenbasierten Benutzerimports ist in
:cite:t:`ucsschool-import` beschrieben.

.. _school-setup-cli-classes:

Import von Schulklassen
=======================

Beim Import schon Schulklassen ist zu beachten, dass die Klassennamen
domänenweit eindeutig sein müssen. Das heißt, eine Klasse *1A* kann nicht in
mehreren OUs verwendet werden. Daher sollte jedem Klassennamen die OU und ein
Bindestrich vorangestellt werden.

Bei der Erstellung von Klassen über das UMC-Modul *Klassen (Schulen)* geschieht
dies automatisch. Sprechende Namen, wie zum Beispiel ``Igel`` oder
``BiologieAG``, sind für Klassennamen ebenso möglich wie
Buchstaben-Ziffern-Kombinationen (``10R``).

Beispiele für die Schule ``gym123``:

.. code-block::

   gym123-1A
   gym123-1B
   gym123-2A
   gym123-Igel

Der Import von Benutzern erfolgt über das Skript
:command:`/usr/share/ucs-school-import/scripts/import_group`, das auf dem
|UCSPRIMARYDN| als Benutzer ``root`` gestartet werden muss. Es erwartet den
Namen einer CSV-Datei als ersten Parameter. Das Dateiformat für die
Gruppen-Importdatei ist wie folgt aufgebaut:

.. _school-setup-cli-classes-table:

.. list-table:: Aufbau der Datenzeilen für den Gruppen-Import
   :header-rows: 1
   :widths: 2 5 3 2

   * - Feld
     - Beschreibung
     - Mögliche Werte
     - Beispiel

   * - Aktion
     - Art der Gruppenmodifikation
     - ``A``\ =Hinzufügen, ``M``\ =Modifizieren, ``D``\ =Löschen
     - ``A``

   * - OU
     - OU, in der die Gruppe modifiziert werden soll
     - ---
     - ``g123``

   * - Gruppenname
     - Der Name der Gruppe
     - ---
     - ``g123m-1A``

   * - (Beschreibung)
     - Optionale Beschreibung der Gruppe
     - ---
     - ``Klasse 1A``

Ein Beispiel für eine Importdatei:

.. code-block::

   A     g123m     g123m-1A         Klaaassen 1A
   A     g123m     g123m-LK-Inf     Leistungskurs Informatik
   M     g123m     g123m-1A         Klasse 1A
   D     g123m     g123m-LK-Inf     Leistungskurs Informatik
   D     g123m     g123m-R12        Klasse R12


.. _school-setup-cli-annualrotation:

Vorgehen zum Schuljahreswechsel
===============================

Zum Schuljahreswechsel stehen zahlreiche Änderungen in den Benutzerdaten an.
Schüler werden in eine höhere Klasse versetzt, der Abschlussjahrgang verlässt
die Schule und ein neuer Jahrgang wird eingeschult.

Ein Schuljahreswechsel erfolgt in vier Schritten:

#. Eine Liste aller Schulabgänger wird aus der Schulverwaltungssoftware
   exportiert und die Konten werden über das Import-Skript entfernt (Aktion D,
   siehe :ref:`school-setup-cli-importusers`). Die Klassen der Schulabgänger
   müssen ebenfalls über das Import-Skript für Gruppen entfernt werden.

#. Die bestehenden Klassen sollten umbenannt werden. Dies stellt sicher, dass
   Dateien, die auf einer Klassenfreigabe gespeichert werden und somit einer
   Klasse zugeordnet sind, nach dem Schuljahreswechsel weiterhin der Klasse
   unter dem neuen Klassennamen zugeordnet sind.

   Die ältesten Klassen (die der Abgänger zum Schulende) müssen zuvor gelöscht
   werden. Die Umbenennung erfolgt über das Skript
   :command:`/usr/share/ucs-school-import/scripts/rename_class`, das auf dem
   |UCSPRIMARYDN| als Benutzer ``root`` aufgerufen werden muss. Es erwartet den
   Namen einer tab-separierten CSV-Datei als ersten Parameter. Die CSV-Datei
   enthält dabei pro Zeile zuerst den alten und dann den neuen Klassennamen,
   z.B.

   .. code-block::

      gymmitte-6B     gymmitte-7B
      gymmitte-5B     gymmitte-6B

   Die Reihenfolge der Umbenennung ist wichtig, da die Umbenennung
   sequentiell erfolgt und der Zielname nicht existieren darf.

   .. note::

      Beim Umbenennen der Klassen-Freigaben werden auch deren Werte für
      *Samba-Name* sowie die *erzwungene Gruppe* automatisch angepasst, sofern
      diese noch die Standardwerte des |UCSUAS|-Importskriptes aufweisen.

      Bei manuellen Änderungen müssen diese Werte nach dem Umbenennen der Klasse
      nachträglich manuell angepasst werden.

#. Eine aktuelle Liste aller verbleibenden Schülerdaten wird über das
   Import-Skript neu eingelesen (Aktion ``M``, siehe
   :ref:`school-setup-cli-importusers`).

#. Eine Liste aller Neuzugänge wird aus der Schulverwaltungssoftware exportiert
   und über das Import-Skript importiert (Aktion ``A``, siehe
   :ref:`school-setup-cli-importusers`).

.. _school-schoolcreate-network-import:

Skriptbasierter Import von Netzwerken
=====================================

Durch den Import von Netzwerken können IP-Subnetze im LDAP angelegt werden und
diverse Voreinstellungen wie Adressen von Router, DNS-Server etc. für diese
Subnetze konfiguriert werden. Darunter fällt z.B. auch ein Adressbereich aus dem
für neuangelegte Systeme automatisch IP-Adressen vergeben werden können.

Das Importieren von Subnetzen empfiehlt sich in größeren |UCSUAS|-Umgebungen.
Kleinere Umgebungen können diesen Schritt häufig überspringen, da fehlende
Netzwerke beim Import von Rechnerkonten automatisch angelegt werden.

Netzwerke können derzeit nur auf der Kommandozeile über das Skript
:command:`/usr/share/ucs-school-import/scripts/import_networks` importiert
werden. Das Skript muss auf dem |UCSPRIMARYDN| als Benutzer ``root`` aufgerufen
werden. In der Import-Datei sind die einzelnen Felder durch ein Tabulatorzeichen
zu trennen. Das Format der Import-Datei ist wie folgt aufgebaut:

.. list-table::
   :header-rows: 1
   :widths: 3 5 4

   * - Feld
     - Beschreibung
     - Mögliche Werte

   * - OU
     - OU des zu modifizierenden Netzwerks
     - ``g123m``

   * - Netzwerk
     - Netzwerk und Subnetzmaske
     - ``10.0.5.0/255.255.255.0``

   * - (IP-Adressbereich)
     - Bereich, aus dem IP-Adressen für neuangelegte Systeme automatisch
       vergeben werden
     - ``10.0.5.10-10.0.5.140``

   * - (Router)
     - IP-Adresse des Routers
     - ``10.0.5.1``

   * - (DNS-Server)
     - IP-Adresse des DNS-Servers
     - ``10.0.5.2``

   * - (WINS-Server)
     - IP-Adresse des WINS-Servers
     - ``10.0.5.2``

Beispiel für eine Importdatei:

.. code-block::

   g123m  10.0.5.0                          10.0.5.1  10.0.5.2  10.0.5.2
   g123m  10.0.6.0/25  10.0.6.5-10.0.6.120  10.0.6.1  10.0.6.2  10.0.6.15


Wird für das Feld *Netzwerk* keine Netzmaske angegeben, so wird automatisch die
Netzmaske ``255.255.255.0`` verwendet. Sollte der *IP-Adressbereich* nicht
explizit angegeben worden sein, wird der Bereich X.Y.Z.20-X.Y.Z.250 verwendet.

Zur Vereinfachung der Administration der Netzwerke steht zusätzlich das Skript
:command:`import_router` zur Verfügung, das nur den Default-Router für das
angegebene Netzwerk neu setzt. Es verwendet das gleiche Format wie
:command:`import_networks`.

.. _school-schoolcreate-computers:

Import von Rechnerkonten für Windows-PCs
========================================

Rechnerkonten können entweder einzeln über ein spezielles UMC-Modul oder über
ein spezielles Import-Skript als Massenimport angelegt werden. Die Rechnerkonten
sollten vor dem Domänenbeitritt von z.B. Windows-PCs angelegt werden, da so
sichergestellt wird, dass die für den Betrieb von |UCSUAS| notwendigen
Informationen im LDAP-Verzeichnis vorhanden sind und die Objekte an der
korrekten Position im LDAP-Verzeichnis abgelegt wurden.

Nach dem Anlegen der Rechnerkonten können Windows-PCs über den im UCS-Handbuch
beschriebenen Weg der Domäne beitreten.

.. _school-schoolcreate-computers-import:

Skriptbasierter Import von PCs
------------------------------

Der Import mehrerer PCs erfolgt über das Skript
:command:`/usr/share/ucs-school-import/scripts/import_computer`, das auf dem
|UCSPRIMARYDN| als Benutzer ``root`` aufgerufen werden muss. Es erwartet den
Namen einer CSV-Datei als ersten Parameter, die in folgender Syntax definiert
wird. Die einzelnen Felder sind durch ein Tabulatorzeichen zu trennen.

Es ist zu beachten, dass Computernamen domänenweit eindeutig sein müssen. Das
heißt, ein Computer ``windows01`` kann nicht in mehreren OUs verwendet werden.

Um die Eindeutigkeit zu gewährleisten, wird empfohlen, jedem Computernamen die
OU voranzustellen oder zu integrieren (z.B. ``340win01`` für Schule *340*).

.. list-table::
   :header-rows: 1
   :widths: 2 5 2 3

   * - Feld
     - Beschreibung
     - Mögliche Werte
     - Beispiel

   * - Rechnertype
     - Typ des Rechnerobjektes
     - ``ipmanagedclient``, ``macos``, ``windows``
     - ``windows``

   * - Name
     - zu verwendender Rechnername
     - ---
     - ``wing123m-01``

   * - MAC-Adresse
     - MAC-Adresse (wird für DHCP benötigt)
     - ---
     - ``00:0c:29:12:23:34``

   * - OU
     - OU; in der das Rechnerobjekt modifiziert werden soll
     - ---
     - ``g123m``

   * - IP-Adresse (/Netzmaske) oder IP Subnetz
     - IP-Adresse des Rechnerobjektes und optional die passende Netzmaske;
       alternativ das Ziel-IP-Subnetz
     - ---
     - ``10.0.5.45/255.255.255.0``

   * - (Inventarnr.)
     - Optionale Inventarnummer
     - ---
     - ``TR47110815-XA-3``

   * - (Zone)
     - Optionale Zone
     - ``edukativ``, ``verwaltung``
     - ``edukativ``

Die Subnetzmaske kann sowohl als Präfix (``24``) als auch in Oktettschreibweise
(``255.255.255.0``) angegeben werden. Die Angabe der Subnetzmaske ist optional.
Wird sie weggelassen, wird die Subnetzmaske ``255.255.255.0`` angenommen.

Wird im Feld *IP-Adresse (/ Netzmaske)* nur ein Subnetz angegeben (z.B.
``10.0.5.0``), wird dem Computerobjekt automatisch die nächste freie IP-Adresse
aus diesem IP-Subnetz zugewiesen.

Beispiel für eine Importdatei:

.. code-block::

   ipmanagedclient  routerg123m-01   10:00:ee:ff:cc:02  g123m  10.0.5.1
   windows          wing123m-01      10:00:ee:ff:cc:00  g123m  10.0.5.5
   windows          wing123m-02      10:00:ee:ff:cc:01  g123m  10.0.5.6
   macos            macg123m-01      10:00:ee:ff:cc:03  g123m  10.0.5.7
   ipmanagedclient  printerg123m-01  10:00:ee:ff:cc:04  g123m  10.0.5.250


Die importierten Rechner werden so konfiguriert, dass ihnen die angegebene
IP-Adresse automatisch per DHCP zugeordnet wird, sofern auf dem Schulserver der
DHCP-Dienst installiert ist, und der angegebene Rechnername über das Domain Name
System (DNS) aufgelöst werden kann.

Ab |UCSUAS| 5.0 v2 wird das Ausführen von Python Hooks während des Computer
Imports unterstützt (siehe :ref:`pyhooks`).

.. _school-setup-cli-printers:

Konfiguration von Druckern an der Schule
========================================

Der Import der Drucker kann skriptbasiert über das Skript
:command:`/usr/share/ucs-school-import/scripts/import_printer` erfolgen, das auf
dem |UCSPRIMARYDN| als Benutzer ``root`` aufgerufen werden muss. Es erwartet den
Namen einer CSV-Datei als ersten Parameter, die in folgender Syntax definiert
wird. Die einzelnen Felder sind durch ein Tabulatorzeichen zu trennen.

.. list-table::
   :header-rows: 1
   :widths: 2 4 3 3

   * - Feld
     - Beschreibung
     - Mögliche Werte
     - Beispiel

   * - Aktion
     - Art der Druckermodifikation
     - ``A``\ =Hinzufügen, ``M``\ =Modifizieren, ``D``\ =Löschen
     - ``A``

   * - OU
     - OU, in der das Druckerobjekt modifiziert werden soll
     - ---
     - ``g123m``

   * - Druckerserver
     - Name des zu verwendenden Druckservers
     - ---
     - ``dcg123m-01``

   * - Name
     - Name der Druckerwarteschlange
     - ---
     - ``laserdrucker``

   * - URI
     - URI, unter dem der Drucker erreichbar ist
     - ---
     - ``lpd://10.0.5.250``

Die Druckerwarteschlange wird beim Anlegen eines neuen Druckers auf dem im Feld
*Druckserver* angegebenen Druckserver eingerichtet. Das URI-Format unterscheidet
sich je nach angebundenem Drucker und ist in :ref:`print-shares` in
:cite:t:`ucs-manual` beschrieben.
