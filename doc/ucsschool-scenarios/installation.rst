.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _install:

************
Installation
************

Die Installation von |UCSUAS| ist grundlegend in :ref:`installation-chapter` in
:cite:t:`ucs-manual` und in :external+uv-ucsschool-manual:ref:`install` in
:cite:t:`ucsschool-admin` beschrieben. In diesem Abschnitt geben wir zusätzliche
Hinweise zur Installation, insbesondere im Hinblick auf die Umsetzung der
definierten Konzepte.

* Zur Installation wird das `aktuellste UCS Installationsmedium
  <https://www.univention.de/ucs-download/>`_
  empfohlen.

* Der Pfad :file:`/var/log` sollte auf eine eigene Partition gelegt werden,
  damit bei erhöhten Aufkommen an Log-Informationen nicht die Systempartition
  voll läuft und in der Folge die Funktionsfähigkeit des Gesamtsystems
  zusammenbricht.

* Ist die Verfügbarkeit von performanten Festplatten (zum Beispiel SSDs)
  begrenzt und reicht nicht für das gesamte System aus, so sollte zumindest
  :file:`/var/lib` als eigene Partition auf performanten Festplatten angelegt
  werden.

* Je nach System und verwendeten Diensten (beispielsweise für Schulserver mit
  lokalen Benutzerdaten) sollte die Auslagerung auf einem eigenen Dateisystem
  auch für den Pfad :file:`/home` erfolgen.

.. _installation-primary-directory-node:

Installation des |UCSPRIMARYDN|
===============================

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

* Die IP-Adresskonfiguration erfolgt entsprechend dem Netzkonzept.

* Als Externer DNS-Server bzw. DNS-Forwarder ist die IP-Adresse des DNS-Servers
  des Internetproviders oder des Rechenzentrum-Betreibers einzutragen.

* Die folgende Option ist auszuwählen, um den |UCSPRIMARYDN| zu installieren:
  *Erstellen einer neuen |UCSUCS|-Domäne*.

* Nach der Eingabe des Domänennamen wird automatisch eine LDAP-Basis
  vorgeschlagen. Diese sollte entsprechend des Namenskonzeptes angepasst werden.

* Das installierte System ist abschließend bis zum letzten verfügbaren
  Errata-Update zu aktualisieren.

* Nach Abschluss der Installation ist über das Univention App Center die App
  |UCSUASp| zu installieren.

* Im Anschluss an die Installation der App |UCSUASp| ist in der |UCSUMC| in der
  Kategorie *Schuladministration* der *UCS\@school Einrichtungsassistent* zu
  starten und die Option *Multi-Server Umgebung* zu wählen und der Assistent bis
  zum Ende auszuführen.

* Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`:

  Um Gruppenrichtlinien für alle Schulen über eine zentrale Stelle verwalten zu
  können, muss zudem über das Univention App Center die App :program:`Active
  Directory kompatibler Domänen-Controller` installiert werden.

  Soll der NetBIOS-Domänenname nicht automatisch erzeugt werden, ist dieser vor
  der Installation explizit zu konfigurieren (siehe auch
  :ref:`concepts-names-domain`).

  Sollen in der |UCSUAS|-Domäne mehr als 50.000 Benutzer verwaltet werden,
  setzen Sie sich bitte vorab mit Univention in Verbindung, um Möglichkeiten zur
  Performanceoptimierung zu besprechen.

* Abschließend ist zu prüfen, ob alle Join-Skripte erfolgreich ausgeführt
  wurden. Dies kann in der |UCSUMC| in der Kategorie *Domäne* mit dem Modul
  *Domänenbeitritt* geprüft werden.

.. _installation-backup-directory-node:

Installation eines |UCSBACKUPDN|
================================

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Zur Lastverteilung bei der LDAP-Replikation können neben dem ersten, unbedingt
notwendigen |UCSBACKUPDN| Server zusätzlich noch weitere |UCSBACKUPDN| Systeme
aufgesetzt werden.

* Es ist sicherzustellen, dass zuvor auf dem |UCSPRIMARYDN| alle verfügbaren
  Updates installiert wurden.

* Die IP-Adresskonfiguration erfolgt entsprechend des Netzkonzepts.

* Als DNS-Server ist die IP-Adresse des |UCSPRIMARYDN| einzutragen. Der
  DNS-Forwarder wird beim Domänenbeitritt automatisch vom |UCSPRIMARYDN|
  übernommen und braucht somit nicht eingetragen zu werden.

* Die folgende Option ist auszuwählen, um den |UCSBACKUPDN| als Mitglied der
  Domäne zu installieren: *Einer bestehenden UCS-Domäne beitreten*. Anschließend
  ist die Rolle |UCSBACKUPDN_e| auszuwählen.

* Das installierte System ist abschließend bis zum letzten verfügbaren
  Errata-Update zu aktualisieren. Anschließend ist der Domänenbeitritt zu
  starten.

* Während des Domänenbeitritts wird die App |UCSUASp| automatisch installiert.
  Dies ist über das Univention App Center zu prüfen.

* Alle benötigten Pakete werden während des Domänenbeitritts installiert.

* Im Anschluss an die Installation der App |UCSUASp| ist in der |UCSUMC| in der
  Kategorie *Schuladministration* zu prüfen, dass der *UCS\@school
  Einrichtungsassistent* erfolgreich abgeschlossen wurde.

* Abschließend ist zu prüfen, ob alle Join-Skripte erfolgreich ausgeführt wurden.
  Dies kann in der |UCSUMC| in der Kategorie *Domäne* mit dem Modul
  *Domänenbeitritt* geprüft werden.

Weitere Hinweise zur Installation eines Schulservers und zum |UCSUAS|
Einrichtungsassistent finden sich auch in
:ref:`school-installation-replica-directory-node` in :cite:t:`ucsschool-admin`.

.. _installation-replica-directory-node:

Installation eines zentralen |UCSREPLICADN| für RADIUS, Groupware, Collaboration, Lernplattformen usw.
======================================================================================================

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Nach Möglichkeit sollte für jeden Dienst ein separater Server mit der
Rolle |UCSREPLICADN_e| verwendet werden.

* Es ist sicherzustellen, dass zuvor auf dem |UCSPRIMARYDN| alle verfügbaren
  Updates installiert wurden.

* Die IP-Adresskonfiguration erfolgt entsprechend des Netzkonzepts.

* Als DNS-Server sind die IP-Adressen des |UCSPRIMARYDN| und des |UCSBACKUPDN|
  einzutragen. Der DNS-Forwarder wird beim Domänenbeitritt automatisch vom
  |UCSPRIMARYDN| übernommen und braucht somit nicht eingetragen zu werden.

* Die folgende Option ist auszuwählen, um den |UCSREPLICADN| als Mitglied der
  Domäne zu installieren: *Einer bestehenden UCS-Domäne beitreten*. Anschließend
  ist die Rolle |UCSREPLICADN_e| auszuwählen und zu bestätigen, dass es sich um
  einen zentralen |UCSREPLICADN| handelt und explizit nicht um einen
  Schulserver.

* Das installierte System ist abschließend bis zum letzten verfügbaren
  Errata-Update zu aktualisieren. Falls noch nicht erfolgt, ist der
  Domänenbeitritt zu starten.

* Nach Abschluss der Installation ist über das Univention App Center die
  gewünschte App, zum Beispiel :program:`RADIUS`, zu installieren.

* Die App |UCSUASp| soll hier **nicht** installiert werden.

* Abschließend ist zu prüfen, ob alle Join-Skripte erfolgreich ausgeführt wurden.
  Dies kann in der |UCSUMC| in der Kategorie *Domäne* mit dem Modul
  *Domänenbeitritt* geprüft werden.

.. _installation-managed-node:
.. _installation-replica-node-monitoring:

Installation eines zentralen |UCSREPLICADN| für Monitoring
==========================================================

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

* Es ist sicherzustellen, dass zuvor auf dem |UCSPRIMARYDN| alle verfügbaren
  Updates installiert wurden.

* Die IP-Adresskonfiguration erfolgt entsprechend des Netzkonzepts.

* Als DNS-Server sind die IP-Adressen des |UCSPRIMARYDN| und des |UCSBACKUPDN|
  einzutragen. Der DNS-Forwarder wird beim Domänenbeitritt automatisch vom
  |UCSPRIMARYDN| übernommen und braucht somit nicht eingetragen zu werden.

* Die folgende Option ist auszuwählen, um den |UCSREPLICADN| als Mitglied der
  Domäne zu installieren: *Einer bestehenden UCS-Domäne
  beitreten*. Anschließend ist die Rolle |UCSMANAGEDNODE_e| auszuwählen.

* Es ist sicherzustellen, dass der |UCSPRIMARYDN| alle verfügbaren Updates
  installiert hat.

* Das installierte System ist abschließend bis zum letzten verfügbaren
  Errata-Update zu aktualisieren. Anschließend ist der Domänenbeitritt zu
  starten.

* Nach Abschluss der Installation ist über das Univention App Center die App
  :program:`UCS Dashboard`, zu installieren. Zur Installation, siehe dazu
  :ref:`Installation von UCS Dashboard <dashboard-installation>` in
  :cite:t:`ucs-manual`.

* Es ist empfohlen, das Monitoring des aktuellen Zustands der Umgebung um die
  Speicherung von Langzeitinformationen zu ergänzen. Weitere Informationen sind
  in :ref:`concepts-monitoring` zu finden.

* Die App |UCSUASp| darf **nicht** installiert werden.

* Abschließend ist zu prüfen, ob alle Join-Skripte erfolgreich ausgeführt
  wurden. Dies kann in der |UCSUMC| in der Kategorie *Domäne* mit dem Modul
  *Domänenbeitritt* geprüft werden.

* Damit :program:`UCS Dashboard` umfassend funktioniert, muss sichergestellt
  sein, dass die App :program:`UCS Dashboard Client` auf allen UCS Systemen
  installiert ist, die über das Monitoring überwacht werden sollen.

* Wenn Benachrichtigungen beim Erreichen von Alarmen versendet werden sollen,
  hilft die App :program:`Prometheus Alertmanager` weiter. Nähere Informationen
  finden sich unter :ref:`monitoring` in :cite:t:`ucs-manual`.

.. _installation-schulserver:

Installation eines |UCSREPLICADN| als Schulserver
=================================================

.. admonition:: Gültigkeit

   Für :ref:`Szenario 3 <scenario-3>`

Vor der Installation des Schulservers muss die zugehörige Schule mitsamt dem
Namen für den Schulserver auf dem |UCSPRIMARYDN| angelegt werden. Es ist zudem
empfehlenswert auch die der Schule zugehörigen Netzwerke vorab zu importieren.
Bitte fahren Sie zunächst mit dem :ref:`import` fort, importieren mindestens
Schulen und Netzwerke und kommen dann zu diesem Abschnitt für die Installation
des Schulservers zurück.

* Es ist sicherzustellen, dass zuvor auf dem |UCSPRIMARYDN| alle verfügbaren
  Updates installiert wurden.

* Es ist sicherzustellen, dass zuvor die Schule mitsamt dem Namen für den
  Schulserver sowie die Netzwerke auf dem |UCSPRIMARYDN| entsprechend der
  Beschreibung in :ref:`import-schools` angelegt bzw. importiert wurden.

* Bei der Partitionierung sollte darauf geachtet werden, dass der Pfad
  :file:`/home` auf einem eigenen Dateisystem abgelegt wird, damit aufgrund von
  übermäßig vielen Benutzerdaten die Systempartition nicht voll läuft.

* Die IP-Adresskonfiguration erfolgt entsprechend des Netzkonzepts.

* Als DNS-Server sind die IP-Adressen des |UCSPRIMARYDN| und des |UCSBACKUPDN|
  einzutragen. Der DNS-Forwarder wird beim Domänenbeitritt automatisch vom
  |UCSPRIMARYDN| übernommen und braucht somit nicht eingetragen zu werden.

* Die folgende Option ist auszuwählen, um den |UCSREPLICADN| als Mitglied der
  Domäne zu installieren: *Einer bestehenden UCS-Domäne beitreten*. Anschließend
  ist die Rolle |UCSREPLICADN_e| auszuwählen.

* Es ist darauf zu achten, dass der bei der Installation angegebene Rechnername
  mit dem Namen des Schulservers übereinstimmt, der beim Anlegen der Schule
  angegeben wurde. Dies muss der Fall sein, damit der Server im weiteren Verlauf
  als edukativer Schulserver eingerichtet werden kann und explizit nicht als
  zentraler |UCSREPLICADN|.

* Das installierte System automatisch bis zum letzten verfügbaren Errata-Update
  aktualisieren, den Domänenbeitritt starten und dabei die App |UCSUASp|
  installieren.

* Alle benötigten Pakete werden während des Domänenbeitritts installiert und für
  die zu replizierende Schule konfiguriert.

* Abschließend ist zu prüfen, ob alle Join-Skripte erfolgreich ausgeführt
  wurden. Dies kann in der |UCSUMC| in der Kategorie *Domäne* mit dem Modul
  *Domänenbeitritt* geprüft werden.

* Soll der Schulserver auch als DHCP-Server fungieren (empfohlen), muss noch die
  App :program:`DHCP-Server` über das Univention App Center installiert werden.

Weitere Hinweise zur Installation eines Schulservers und zum |UCSUAS|
Einrichtungsassistent finden sich auch in
:ref:`school-installation-replica-directory-node` in :cite:t:`ucsschool-admin`.
