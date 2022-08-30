.. _infrastructure-and-hardware-requirements:

***********************************************
Netzinfrastruktur- und Hardware-Voraussetzungen
***********************************************

Im Folgenden werden die Netzinfrastruktur- und Hardware-Voraussetzungen für den
Einsatz von |UCSUAS| beschrieben. Die beschriebenen Voraussetzungen sind
Richtwerte, die wir ermittelt haben. Im Einzelfall ist jedoch genau zu prüfen,
ob die Voraussetzungen mit den gestellten Anforderungen übereinstimmen.

Allgemein hat sich für den Betrieb von |UCSUCS| bewährt, eine
Virtualisierungslösung einzusetzen. Die Dimensionierung der
Virtualisierungsserver muss sich dabei an den Anforderungen der virtualisierten
Systeme richten und dabei noch genügend Möglichkeiten zur nachträglichen
Erweiterung bereithalten. Eine Zuweisung von mehr als den vorhandenen Ressourcen
(Überprovisionierung) wird abgeraten. Für den Speicherplatz sollten mindestens
SAS-Festplatten mit 10.000 Umdrehungen pro Minute zum Einsatz kommen,
idealerweise aber SSD-Festplatten (mindestens für die I/O-intensiven Dienste wie
OpenLDAP und Samba unter :file:`/var/lib/`.)

Die genannten Werte sind die Minimalanforderungen für die oben beschriebenen
Szenarien. Abhängig von der Größe der Umgebung und Anzahl der aktiven Geräte und
Personen können die Anforderungen höher liegen. Die tatsächliche Auslastung der
einzelnen Systeme sollte fortlaufend durch das :ref:`concepts-monitoring`
überwacht werden, um Engpässe zu vermeiden. Im Folgenden werden die Server, ihre
Funktionen und die jeweiligen Anforderungen beschrieben.

.. _infrastructure-and-hardware-requirements-servers:

Zentrale Server
===============

.. _infrastructure-and-hardware-requirements-servers-primary-directory-node:

Identity Management
-------------------

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Systeme vom Typ |UCSPRIMARYDN| und |UCSBACKUPDN| stellen das
Identitätsmanagement mit der zugrunde liegenden LDAP-Datenbank zur Verfügung.

Minimale Systemvoraussetzungen:

* 4 CPU-Kerne

* 8 GB RAM

* 100 GB Speicherplatz

Die primären Lastszenarien des |UCSPRIMARYDN| sind:

* Viele lesende Zugriffe auf die LDAP-Datenbank, da neben der Administration
  alle weiteren Systeme regelmäßig Information abfragen.

* Schreibende Zugriffe auf die LDAP-Datenbank, sobald Änderungen vorgenommen
  werden. Insbesondere beim initialen Import und beim Schuljahreswechsel wird
  die LDAP-Datenbank stark belastet.

Die I/O-Performance der Festplatten dieser Server ist besonders wichtig,
zusammen mit ausreichend Arbeitsspeicher, der insbesondere beim initialen Import
und beim Schuljahreswechsel notwendig ist.

|UCSBACKUPDN| dienen der Lastverteilung und Ausfallsicherheit. Es sollte immer
mindestens ein |UCSBACKUPDN| in der Domäne vorhanden sein. Darüber hinaus können
bei Bedarf weitere |UCSBACKUPDN|-Systeme hinzugefügt werden.

Sollte der |UCSPRIMARYDN| durch einen irreparablen Schaden ausfallen, kann ein
|UCSBACKUPDN|-System zum |UCSPRIMARYDN| hochgestuft werden. Dieser Vorgang ist
nicht umkehrbar, daher sollte die Position der |UCSBACKUPDN|-Systeme innerhalb
der Netzinfrastruktur entsprechend gewählt werden, damit jedes einzelne System
im Extremfall alle Aufgaben des |UCSPRIMARYDN| übernehmen kann.

.. _infrastructure-and-hardware-requirements-servers-radius:

RADIUS
------

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Minimale Systemvoraussetzungen:

* 2 CPU-Kerne

* 4 GB RAM

* 50 GB Speicherplatz

.. _infrastructure-and-hardware-requirements-servers-monitoring:

Monitoring
----------

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Minimale Systemvoraussetzungen:

* 2 CPU-Kerne

* 4 GB RAM

* 50 GB Speicherplatz

.. _infrastructure-and-hardware-requirements-servers-replica-directory-node:

IT-Angebote, wie Groupware und Lernplattformen
----------------------------------------------

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Für weitere IT-Angebote können keine Minimalanforderungen genannt werden, da
diese sowohl von der Anzahl der parallelen Benutzer als auch von der Anwendung
selbst abhängig sind. Eine Abstimmung mit dem jeweiligen Hersteller ist in aller
Regel notwendig.

.. _infrastructure-and-hardware-requirements-school:

Dezentrale Systeme
==================

.. _infrastructure-and-hardware-requirements-school-server:

Schulserver
-----------

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Auch hier spielt vor allem die Anzahl gleichzeitig aktiver Benutzerkonten und
Endgeräte eine Rolle.

Minimale Systemvoraussetzungen für *kleine Schulen (z.B. Grundschulen)* (25
Computer, 25 Tablets, 150 Benutzerkonten):

* 2 CPU-Kerne

* 4 GB RAM

* 100 GB Speicherplatz für das System selbst

* bis zu 100 GB Speicherplatz für Benutzerdaten

Minimale Systemvoraussetzungen für *mittelgroße Schulen* (100 Computer, 100
Tablets, 600 Benutzerkonten):

* 4 CPU-Kerne

* 16 GB RAM

* 100 GB Speicherplatz für das System selbst

* ab 400 GB Speicherplatz für Benutzerdaten

Minimale Systemvoraussetzungen für *große Schule (z.B. Berufsschulen)* (300
Computer, 200 Tablets, 1500 Benutzerkonten):

* 8 CPU-Kerne

* 32 GB RAM

* 100 GB Speicherplatz für das System selbst

* ab 1.000 GB Speicherplatz für Benutzerdaten

.. _infrastructure-and-hardware-requirements-infrastructure:

Netzinfrastruktur
=================

.. _infrastructure-and-hardware-requirements-infrastructure-network:

Strukturierte Verkabelung
-------------------------

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Die Schulen sollten über eine strukturierte Verkabelung im Schulgebäude
verfügen. Dies schließt ein, das möglichst nur Switches und Netzkomponenten mit
Management-Funktion verwendet werden. Damit werden Probleme vermieden, die durch
fehlerhafte Verkabelung entstehen und es wird möglich, die Qualität der
erbrachten Leistung bis auf Ebene des Netzes zu messen. Darüber hinaus können
Sicherheitsmechanismen implementiert werden, die bei zunehmender Verwendung der
IT-Infrastruktur immer wichtiger werden.

.. _infrastructure-and-hardware-requirements-infrastructure-wifi:

WLAN-Infrastruktur
------------------

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Für die Einführung von WLAN in Schulen gehen wir hier davon aus, dass die
gesamte Schule mit WLAN ausgestattet werden soll und alle Schüler*innen mit
mindestens einem mobilen Endgerät im WLAN aktiv sein werden, auch wenn dies
nicht sofort realisiert werden kann.

Um dieses Ziel zu erreichen, ist eine
:ref:`infrastructure-and-hardware-requirements-infrastructure-network`
Grundvoraussetzung. Darüber hinaus werden professionelle Access Points benötigt,
die mehr als 40 parallel eingebuchte mobile Geräte unterstützen, ohne dass der
Access Point z.B. aufgrund von Speichermangel abstürzt. Mit professionellen
Access Points lassen sich darüber hinaus auch weitere Sicherheits- und
Administrationsmechanismen, wie VLAN, realisieren.

.. _infrastructure-and-hardware-requirements-infrastructure-internet:

Internetzugang
--------------

.. admonition:: Gültigkeit

   Für Szenario :ref:`2 <scenario-2>` und :ref:`3 <scenario-3>`.

Die Schulen sollten über zuverlässige Internetzugänge verfügen, die maximal 1x
pro Nacht getrennt werden. Die Geschwindigkeit des Zugangs sollte mindestens 16
MBit/s betragen. Ausschlaggebend für die notwendige Geschwindigkeit ist die
Anzahl der gleichzeitig aktiven Endgeräte. Als Richtwert kann von einem Bedarf
von mindestens 0,3 MBit/s pro aktivem Gerät ausgegangen werden. Dies ist
insbesondere bei der Einführung von WLAN und Bring Your Own Device (BYOD) zu
beachten, da Lehrkräfte und Schüler*innen ggf. über mehr als ein Gerät pro
Person verfügen werden.

.. _infrastructure-and-hardware-requirements-infrastructure-bandwidth:

Internetzugang: Schulserver im Rechenzentrum
--------------------------------------------

.. admonition:: Gültigkeit

   Für Szenario :ref:`4 <scenario-4>`.

Die folgende Schätzung der Bandbreite gilt ausschließlich für :ref:`scenario-4`,
in dem alle Schulserver aus den Schulen in ein zentrales Rechenzentrum überführt
werden. In den Schulen verbleiben nur die Endgeräte, die zur Nutzung der IT
notwendig sind.

Die Anforderungen der anderen Szenarien sind in
:ref:`infrastructure-and-hardware-requirements-infrastructure-internet`
beschrieben.

Die nötigen Bandbreiten im lokalen Schulnetz können je nach Anwendungsfall stark
schwanken. Die folgende Tabelle gibt einen groben Überblick über Richtwerte nach
Schultyp. Die benötigte Bandbreite liegt zwischen 2-5 MBit/s für schuleigene
Geräte. Dabei ist zu beachten, dass z.B. zum Schulstundenbeginn oder zum
Pausenbeginn mit Lastspitzen zu rechnen ist.

.. list-table:: Minimalanforderungen für die Anbindung nach Schultyp
   :name: table-infrastructure-and-hardware-requirements-infrastructure-internet
   :header-rows: 1
   :widths: 3 2 5 2

   * - Schultyp
     - Typische Anzahl Clients
     - Typische Netznutzung
     - Mindestens nötige Bandbreite

   * - Grundschulen
     - ~20 Clients
     - Geringe Netznutzung (~2 MBit/s)
     - 40 MBit/s

   * - Weiterführende Schulen
     - ~90 Clients
     - Mittlere Netznutzung (~3 MBit/s)
     - 270 MBit/s

   * - Berufsschulen
     - ~300 Clients
     - Hohe Netznutzung (>5 MBit/s)
     - 1,5 GBit/s

.. _infrastructure-and-hardware-requirements-infrastructure-vpn:

Verbindung zur Zentrale
-----------------------

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Die Schulen müssen an die zentralen Systeme angebunden werden, damit eine
Steuerung der Netze, Endgeräte und ggf. Server von zentraler Stelle möglich
wird. Um die Verbindung aufzubauen, können VPN-Technologien, Standleitungen oder
private Netze verwendet werden.

Die Bandbreite der verfügbaren Anbindung beeinflusst entscheidend die möglichen
Szenarien. :ref:`Szenario 4 <scenario-4>` ist zum Beispiel nur bei einer sehr
guten Anbindung im Bereich von 1 GBit/s oder mehr sinnvoll möglich. Bei VPN über
handelsübliche DSL-Leitungen empfiehlt sich stattdessen die Umsetzung von
:ref:`Szenario 3 <scenario-3>`.
