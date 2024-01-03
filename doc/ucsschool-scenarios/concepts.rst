.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _concepts:

******************************
Konzeptionelle Voraussetzungen
******************************

Die folgenden Empfehlungen bauen auf Erfahrungen auf, die sich in diversen
Projekten bewährt haben. Nicht alle sind zwingend umzusetzen und Abweichungen
sind jederzeit möglich.

.. _concepts-network:

Netzkonzept
===========

.. admonition:: Gültigkeit

   Für die Szenarien :ref:`2 <scenario-2>`, :ref:`3 <scenario-3>` und :ref:`4
   <scenario-4>`.

In |UCSUAS| wird für jede Schule mindestens ein Subnetz benötigt, sobald an den
Schulen Endgeräte eingesetzt werden sollen. Abhängig vom Szenario kann eine
einzelne Schule auch mehr als ein Subnetz erhalten.

Für den Aufbau einer Umgebung mit mehreren Schulen empfehlen wir die Verwendung
des privaten Netzes ``10.0.0.0/8``. Dieses wird für die Schulen in viele
Subnetze unterteilt. Für jede Schule wird ein ``/16``-Netz reserviert, das Platz
für 65.536 IP-Adressen bietet und nach Bedarf in weitere Subnetze unterteilt
wird.

.. list-table:: Zuteilung der Subnetze zu Schulen
   :name: table-network-concept-schools
   :header-rows: 1
   :widths: 4 8

   * - Subnetz (CIDR)
     - Schule

   * - ``10.0.0.0/16``
     - Zentrale Systeme

   * - ``10.1.0.0/16``
     - 1. Schule

   * - ``10.2.0.0/16``
     - 2. Schule

   * - ``10.3.0.0/16``
     - 3. Schule

   * - ``10.4.0.0/16``
     - 4. Schule

   * - ``10...../16``
     - *Weitere Schulen*

Voraussetzung für die Verwendung von Subnetzen ist, dass aus dem Netz, in dem
die zentralen Systeme stehen, alle anderen Subnetze erreicht werden können. Dies
kann beispielsweise über ein Site-to-Site VPN oder eine Standleitung realisiert
werden. Eine Verbindung zwischen Schulen ist nicht notwendig und wird häufig
auch nicht gewünscht.

.. note::

   Bei mehr als 255 Schulen kann das vorgeschlagene Netzkonzept nicht verwendet
   werden.

.. _concepts-network-examples:

Beispiele für Subnetzkonzepte
-----------------------------

Im Folgenden werden zwei Beispiele für die Schulnetze gezeigt. Das erste für ein
Schulnetz für kleinere Schulen mit wenigen Endgeräten, zum Beispiel
Grundschulen, das zweite für sehr große Schulen mit vielen Endgeräten und
mehreren Subnetzen, zum Beispiel Berufsschulen. Vorweg erfolgt die Definition
des Subnetzes für die zentralen Systeme.

Um die Subnetze in |UCSUAS| bekannt zu machen, müssen diese importiert werden.
In :ref:`import-networks` ist beschrieben wie der Import vorzunehmen ist, welche
Informationen anzugeben sind und welche Hilfsmittel dafür zur Verfügung stehen.

.. list-table:: Zentrales Subnetz
   :name: table-network-concept-central
   :header-rows: 1
   :widths: 3 3 3 3

   * - Subnetz (CIDR)
     - DHCP-Adressbereich
     - Anzahl IP-Adressen
     - Verwendung

   * - ``10.0.0.0/24``
     - ``-``
     - 254
     - Subnetz für zentrale Systeme

Alle zentralen Instanzen von |UCSUAS| werden in diesem Netz installiert. Auf
eine Adressvergabe via DHCP wird verzichtet, alle Systeme erhalten eine statisch
zugewiesene IP-Adresse. Weitere Subnetze, wie zum Beispiel eine Demilitarisierte
Zone (DMZ), können bei Bedarf ergänzt werden.

.. _concepts-network-examples-primary:

Beispiel Subnetz Grundschule
----------------------------

.. list-table:: Netze für Beispiel-Grundschule
   :name: table-network-concept-small-school
   :header-rows: 1
   :widths: 3 3 3 3

   * - Subnetz (CIDR)
     - DHCP-Adressbereich
     - Anzahl IP-Adressen
     - Verwendung

   * - ``10.1.0.0/24``
     - ``10.1.0.1-10.1.0.254``
     - 254
     - Kleines Netz für eine Grundschule

In diesem Beispiel werden eventuell vorhandene Server und Endgeräte im selben
Netz betrieben. Dieses Modell richtet sich an kleine Schulen mit wenigen
Endgeräten. Bei Bedarf können weitere Subnetze ergänzt werden, da das für die
Schule reservierte ``/16``-Netz nur zu einem kleinen Teil ausgeschöpft wurde.

.. _concepts-network-examples-highschool:

Beispiel Subnetz Berufsschule
-----------------------------

.. list-table:: Netze für Beispiel-Berufsschule
   :name: table-network-concept-large-school
   :header-rows: 1
   :widths: 2 3 2 5

   * - Subnetz (CIDR)
     - DHCP-Adressbereich
     - Anzahl IP-Adressen
     - Verwendung

   * - ``10.42.1.0/24``
     - ``-``
     - 254
     - Netz für Server und Netzgeräte, statische IP-Adressen

   * - ``10.42.2.0/24``
     - ``10.42.2.10 - 10.42.2.250``
     - 254
     - Netz für Schulverwaltung, erweiterbar auf ``/23`` (510 IP-Adressen)

   * - ``10.42.4.0/24``
     - ``10.42.4.10 - 10.42.4.250``
     - 254
     - Netz für edukativen Bereich 1, erweiterbar auf ``/23`` (510 IP-Adressen)

   * - ``10.42.6.0/24``
     - ``10.42.6.10 - 10.42.6.250``
     - 254
     - Netz für edukativen Bereich 2, erweiterbar auf ``/23`` (510 IP-Adressen)

   * - ``10.42.8.0/24``
     - ``10.42.8.10 - 10.42.8.250``
     - 254
     - Netz für edukativen Bereich 3, erweiterbar auf ``/23`` (510 IP-Adressen)

   * - ``10.42.10.0/24``
     - ``10.42.10.10 - 10.42.10.250``
     - 254
     - Netz für edukativen Bereich 4, erweiterbar auf ``/23`` (510 IP-Adressen)

   * - ``10.42.128.0/20``
     - ``10.42.128.100 - 10.42.143.250``
     - 4094
     - Gäste WLAN / BYOD, erweiterbar auf ``/128`` (16.382 IP-Adressen)

   * - ``10.42.192.0/20``
     - ``10.42.192.100 - 10.42.207.250``
     - 4094
     - Schuleigenes WLAN mit RADIUS-Authentifizierung, erweiterbar auf ``/18``
       (16.382 IP-Adressen)

In diesem Beispiel werden einzelne Subnetze für WLAN, Server, Verwaltung und
edukativen Bereich betrieben. Dieses Modell richtet sich an große Schulen mit
vielen Endgeräten. Die Subnetze sind so gewählt, dass sie sich bei Bedarf noch
erweitern lassen. Die Unterteilung des edukativen Bereichs in einzelne Subnetze
kann beispielsweise pro Gebäude, pro Etage oder sogar pro Computerraum erfolgen.
Netzdrucker können in die Subnetze aufgenommen werden, in denen sich auch die
zugehörigen Endgeräte befinden oder es wird ein eigenes Druckernetz hinzugefügt.

.. _concepts-names:

Konzept zur Benennung von Objekten
==================================

In einer |UCSUAS|-Domäne für ein oder mehrere Schulen gibt es viele Objekte, die
eindeutige Namen benötigen. So brauchen zum Beispiel Benutzerkonten eindeutige
Benutzernamen und E-Mail-Adressen. Schulklassen brauchen eindeutige
Bezeichnungen, um sie von gleichnamigen Klassen in anderen Schulen zu
unterscheiden. Rechnerobjekte benötigen Rechnernamen und Schulen benötigen eine
Kurzbezeichnung für die Organisationseinheit im Verzeichnisdienst, in dem die
zugehörigen Objekte gespeichert werden. Ein Konzept zur Benennung von Objekten
verfolgt die Ziele, Eindeutigkeit herzustellen und gleichzeitig die Bedeutung
und Zuordnung des jeweiligen Objekts offensichtlich zu machen. Im Folgenden
zeigen wir Konzepte für unterschiedliche Objekttypen auf, die sich in der Praxis
bewährt haben.

.. _concepts-names-domain:

Name der Domäne
---------------

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Der Name der Domäne definiert mehrere zugehörige Namen:

* LDAP-Basis des Verzeichnisdienstes

* DNS-Domäne

* Kerberos-Realm

* Samba/Active Directory-Domäne

Die Wahl dieses Namens hat umfangreiche Auswirkungen auf die gesamte
|UCSUAS|-Installation und sollte entsprechend mit Bedacht gewählt werden,
insbesondere weil eine nachträgliche Änderung nicht möglich ist.

In bisherigen Projekten hat es sich als sinnvoll erwiesen, einen bislang nicht
verwendeten Domänennamen sowohl für den Zugriff aus dem Internet als auch für
die Benennung der internen UCS-Domäne zu verwenden.

Wird beispielsweise ``example.org`` als Domänenname ausgewählt, muss auch
|UCSUCS| mit diesem Domänennamen installiert werden. Zudem muss sichergestellt
sein, dass die öffentliche Internet-Domain ``example.org`` vom Betreiber bei
einem Domain-Name-Registrar registriert wurde und dass weitere öffentliche
Subdomains angelegt werden können.

.. note::

   Mit dem hier empfohlenen Vorgehen wird ein sog. *Split-DNS-Szenario*
   eingerichtet. Die von |UCSUCS| für interne Funktionen bereitgestellten
   DNS-Dienste lösen Hostnamen auf internen IP-Adressen auf, während öffentliche
   DNS-Server die selben Hostnamen auf die öffentlichen IP-Adressen auflösen
   müssen.

* Beispiel für die Hauptdomain (auch interne UCS-Domäne): ``example.org``

* Beispiel für das Portal (Zugriff von außen): ``portal.example.org``

* Beispiel für eine Anwendung wie beispielsweise Webmail (Zugriff von außen):
  ``mail.example.org``

Bei der Wahl des Domänennamens sind einige Punkte zu beachten:

* Es ist wichtig, dass die DNS-Domäne vom Betreiber verwaltet wird. Es muss
  sichergestellt werden, dass der gewählte Domänenname für |UCSUAS| im
  öffentlichen Internet noch nicht verwendet wird.

* Für den nicht empfohlenen Fall, dass die Verwendung einer öffentlichen
  DNS-Domäne nicht möglich ist und stattdessen ein selbst ausgewählter, interner
  DNS-Name verwendet wird, so sind folgende Regeln zu beachten:

  * Offizielle DNS-Domänen sollten nicht verwendet werden, wenn sie nicht unter
    eigener Kontrolle stehen, z.B. ``deutschland.de``.

  * Inoffiziell verwendete Top-Level-Domänen sollten nicht verwendet werden, zum
    Beispiel ``.corp`` oder ``.lan``. Bei ihnen besteht die Gefahr, dass es zu
    späteren Namenskollisionen kommt.

  * ``.local`` sollte nicht als Top-Level-Domäne gewählt werden. Die Endung ist
    offiziell für mDNS (Multicast DNS) vorgesehen und führt bei einer Verwendung
    zu Problemen mit macOS, Windows und Linux-Betriebssystemen.

* Im internen Netz werden dem Domänennamen für |UCSUAS| die Namen der Rechner
  und Server vorangestellt, um für diese Systeme einen voll qualifizierten
  DNS-Namen (FQDN) zu bilden. Zum Beispiel ist der Rechner ``ucsrz01`` somit
  intern unter dem FQDN ``ucsrz01.example.org`` zu erreichen.

* In |UCSUAS| werden mindestens im Falle der Schulserver auch Samba Active
  Directory Domaincontroller betrieben. Aus Gründen der Abwärtskompatibilität
  wird dabei auch immer ein NetBIOS- bzw. *Legacy-Domänenname* erstellt. Im Falle
  von ``example.org`` als DNS-Domänenname würde automatisch ``EXAMPLE`` als
  NetBIOS-Domänenname gesetzt sein.

  Der NetBIOS-Domänenname ist auf 15 Zeichen begrenzt. Dies kann zu Situationen
  führen, in denen der NetBIOS-Domänenname ungünstig abgeschnitten wird. Wählt
  man beispielsweise ``schulen-musterstadt.de`` als DNS-Domänenname, würde der
  automatisch abgeleitete NetBIOS-Domänenname ``SCHULEN-MUSTERS`` lauten. Dieser
  Name ist beispielsweise beim Anmeldebildschirm an Windows-Clients der Domäne
  zu sehen. Möchte man nun lieber ``MUSTERSTADT`` als Anzeigename dort sehen, so
  ist auf dem |UCSUAS|-Server bereits während der Installation der gewünschte
  ``NetBIOS-Domänenname`` zu setzen (siehe auch :uv:kb:`How to define the
  NetBIOS name during installation <6390>`).

.. _concepts-names-servers:

Zentrale Server
---------------

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Zentrale Server:

* Schema: ``[System][Standort][Laufnummer]``

* Beispiel: System UCS, Standort Rechenzentrum, erstes System: ``ucsrz01``

* Weitere Beispiele:

  * |UCSPRIMARYDN|: ``ucsrz01``

  * |UCSBACKUPDN|: ``ucsrz02``, ``ucsrz03``

  * |UCSREPLICADN|: ``ucsrz04``

  * |UCSMANAGEDNODE|: ``ucsrz05``

Der Name darf eine Länge von 13 Zeichen nicht überschreiten und sollte nicht mit
einer Ziffer beginnen.

.. _concepts-names-clients-and-servers:

Rechner und Schulserver
-----------------------

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Rechner:

* Schema: ``[Betriebssystem]-[Kurzbezeichnung Schule]-[Laufnummer]``

* Beispiele: ``win-042-001``, ``win-042-002``, ``mac-042-001``

Netzgeräte, wie Router, Switches, USV, Drucker:

* Schema: ``[Gerätetyp]-[Kurzbezeichnung Schule]-[Laufnummer]``

* Beispiele: ``rou-042-001``, ``swi-042-003``, ``usv-042-001``, ``dru-042-012``

Schulserver:

* Schema: ``[Rollenbezeichnung]-[Kurzbezeichnung Schule]-[Laufnummer]``

* Beispiele:

  * Edukativer Schulserver: ``sedu-042-01``

  * Schulserver Schulverwaltung: ``sadm-042-01``

Der Name darf eine Länge von 13 Zeichen nicht überschreiten und sollte nicht mit
einer Ziffer beginnen.

.. _concepts-names-user-classes:

Benutzernamen und Klassenbezeichnungen
--------------------------------------

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Benutzerkonten und Klassen hängen in |UCSUAS| sehr eng zusammen. So werden beim
Import von Benutzerkonten ebenfalls die Klassen angegeben, zu denen die
jeweiligen Konten gehören. Das heißt sowohl beim Import von Klassen, also auch
beim Import von Benutzerkonten müssen die gleichen Bezeichnungen für Klassen
verwendet werden und es ist deshalb hilfreich, ein einheitliches Schema zu
spezifizieren.

Bei Benutzerkonten ergibt sich darüber hinaus die Herausforderung, dass sich die
Benutzernamen ändern können, zum Beispiel aufgrund von Heirat, Scheidung, im
Rahmen einer Namens- oder Personenstandänderung oder zur Behebung von
Tippfehlern. In der Praxis hat sich nicht bewährt, unveränderliche Daten wie
Personal- oder Schülernummern als Benutzernamen zu verwenden, da diese
unpersönlich und schwer zu merken sind.

Die Änderung von Benutzernamen stellt also eine Herausforderung im Betrieb dar,
weil die an |UCSUAS| angeschlossenen Subsysteme ggf. den Benutzernamen als
identifizierendes Merkmal (also zur Zuordnung von Daten zu Benutzerkonten)
verwenden.

Beispiele für Subsysteme sind E-Maildienste, Dateifreigaben und -tauschsysteme
oder Lernplattformen. Ändert sich der Benutzername, müssen in den Subsystemen
ggf. aufwendig Daten dem neuen Benutzernamen zugeordnet werden. Dieses Problem
kann umgangen werden, wenn frühzeitig, vor der Einführung eines neuen Subsystems
darauf geachtet wird, dass die Zuordnung von Daten zu Benutzerkonten über ein
unveränderliches Merkmal geschieht, zum Beispiel die Personalnummer.
Gleichzeitig muss sichergestellt werden, dass die Anmeldung am Subsystem jedoch
über den einfach zu merkenden Benutzernamen erfolgt.

Schüler*innen:

* Schema: ``[Vorname][1. Buchstabe Nachname][Laufnummer]``

* Beispiel: Mary Selig → ``marys``

* Beispiel Namenskonflikt: Mary Sander → ``marys2``

Lehrkräfte und Mitarbeiter*innen:

* Schema: ``[1. Buchstabe Vorname][Nachname][Laufnummer]``

* Beispiel: Mareike Müller → ``mmueller``

* Beispiel Namenskonflikt: Martina Müller → ``mmueller2``


Für Benutzerkonten kann das gewünschte Schema im Importmechanismus hinterlegt
werden, siehe :cite:t:`ucsschool-import`.

Klassennamen müssen mit der Kurzbezeichnung der Schule (hier im Beispiel ``042`` und
``011``) als Präfix beginnen:

* Schema: ``[Kurzbezeichnung Schule]-[Klasse]``

* Beispiele: ``042-1a``, ``042-5a``, ``011-5a``, ``011-5b``

.. _concepts-names-misc:

Allgemeine Konventionen
-----------------------

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Folgende Konventionen haben sich in allen Szenarien bewährt:

* Alle Objektnamen sollten durchgängig Kleinbuchstaben verwenden.

* Sofern nicht anders angegeben, sollte die Länge von Objektnamen 15 Zeichen
  nicht überschreiten. Dies ist wichtig für Benutzernamen, insbesondere von
  Schüler*innen.

.. _concepts-monitoring:

Monitoring
==========

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Die rechtzeitige Erkennung von Fehlern und möglichen Anzeichen ist ein
elementarer Bestandteil des professionellen IT-Betriebs. |UCSUCS| hat deshalb
die App :program:`UCS Dashboard` fest integriert und für viele relevante
Parameter vorkonfiguriert. *UCS Dashboard* überwacht den aktuellen Zustand der
überwachten Systeme.

Das Monitoring erfolgt für |UCSUAS| immer aus der Zentrale heraus. Entsprechend
ist ein Server-System für den Betrieb des Monitoring-Dienstes vorzusehen, siehe
:ref:`installation-replica-node-monitoring`.

*UCS Dashboard* speichert Langzeitinformationen, so dass Informationen darüber
vorliegen, in welche Richtung sich eine Umgebung entwickelt. Ein Beispiel ist
die Entwicklung der Belegung des Festplattenplatzes. Solche Informationen sind
für den Betrieb einer umfangreichen IT-Infrastruktur erforderlich.

.. _concepts-backup:

Datensicherung und Wiederherstellung
====================================

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Eine zentral mit |UCSUAS| verwaltete Umgebung stellt üblicherweise Dienste für
tausende Personen zur Verfügung. Mit der zunehmenden Anforderung nach orts- und
zeitunabhängiger Verfügbarkeit muss sichergestellt werden, dass nicht nur die
Dienste, sondern auch die Daten den Anforderungen entsprechend zur Verfügung
gestellt werden. Dreierlei Daten sind dabei zu unterscheiden:

* Konfigurationen und Einstellungen, die Administratoren vorgenommen haben

* Steuerinformationen, zum Beispiel die Daten im Identitätsmanagement

* Von Personen erzeugte Daten, zum Beispiel E-Mails

Die Sicherung der Daten muss gewährleistet sein, um im Fehlerfall die
Funktionsfähigkeit wiederherzustellen. Als Minimalumfang muss eine
dateibasierte Sicherung, zum Beispiel mit Hilfe des Befehls :command:`rsync`
erfolgen. Folgende Daten sollten in der Sicherung berücksichtigt werden:

Zentrale Server:

* :file:`/var/univention-backup`: Nächtliche Sicherung der |UCSUCR|-, OpenLDAP-
  und Samba-Datenbank, sowie der Inhalte der SYSVOL-Freigabe.

* :file:`/etc/univention/ssl` auf dem |UCSPRIMARYDN| und den
  |UCSBACKUPDN|-Servern: Beinhaltet das Root-Zertifikat der internen
  Zertifizierungsstelle und alle Rechner-Zertifikate.

* :file:`/etc/*.secret` auf allen Systemen.

Schulserver, sofern vorhanden:

* :file:`/var/univention-backup`: Nächtliche Sicherung der |UCSUCR|. Die
  Sicherung der OpenLDAP- und Samba-Datenbanken braucht nicht gesichert werden,
  da diese beim erneuten Domänenbeitritt des Schulservers vom |UCSPRIMARYDN|
  oder |UCSBACKUPDN| repliziert werden.

* :file:`/home`: Beinhaltet die Benutzerprofile und die Heimatlaufwerke der
  Benutzer, sowie die Freigaben der Klassen und Arbeitsgruppen.

Folgende Punkte haben sich als allgemein bewährtes Vorgehen
herauskristallisiert:

* Die Datensicherung sollte auf ein vom |UCSUCS|-System physikalisch getrenntes
  Gerät erfolgen, zum Beispiel ein *Network Attached Storage (NAS)*.

* Die Datensicherung sollte überwacht werden, zum Beispiel durch ein Plugin im
  Monitoring-Dienst, das bei Misserfolg warnt.

* Die Wiederherstellung sollte in regelmäßigen Abständen getestet werden.

.. _concepts-support:

Support-Kanäle
==============

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Für den erfolgreichen Betrieb von |UCSUAS| ist es erforderlich, dass ein
Helpdesk aufgebaut wird, der Fragen aus den Schulen direkt annehmen kann.
Abhängig von der gewünschten :ref:`Servicestufe <scenario-0>` kann es darüber
hinaus notwendig sein, ein Team von technischen Mitarbeiter*innen zu schulen,
die den Betrieb der Umgebung durchführen.

Neben passenden Werkzeugen zur Kommunikation und Fernwartung, zum Beispiel ein
Ticket-System, müssen auch die Support- und Eskalationswege definiert und
abgestimmt werden. Im Folgenden ein Beispiel für Eskalationswege:

* IT-Verantwortliche an den Schulen kontaktieren den Helpdesk über das
  Helpdesk-Modul in |UCSUAS| oder direkt per E-Mail an das Ticketsystem. In
  dringenden Fällen steht eine Hotline zur Verfügung, die telefonisch erreicht
  werden kann.

* Der Helpdesk übernimmt den First- und Second-Level-Support, ggf. in
  Zusammenarbeit mit einem lokalen Dienstleister.

* In weitergehenden Fällen unterstützt Univention mit Third-Level-Support.
