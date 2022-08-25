.. _school-installation-primary-directory-node2:

Installation einer Multi-Server-Umgebung
========================================

Das Konzept der Multi-Server-Umgebung von |UCSUAS| sieht zentrale Server für
Cloud-Dienste wie Portal, Mail, Kalender, Dateiablage usw. kombiniert mit
lokalen Schulservern für Anmeldedienste, IT-Infrastruktur und pädagogischen
Funktionen vor. Eine Übersicht an möglichen Szenarien wird in
:cite:t:`ucsschool-scenario` dargestellt.

Der Installationsprozess für die unterschiedlichen Rechnerrollen in der
|UCSUAS|-Domäne wird in den nachfolgenden Abschnitten genauer beschrieben.

.. _installation-multi-primary-directory-node:

Installation des |UCSPRIMARYDN|
-------------------------------

Zunächst muss ein UCS System mit der Systemrolle |UCSPRIMARYDN_e| installiert
werden. Die :ref:`Installation von UCS <installation-chapter>` ist in
:cite:t:`ucs-manual` beschrieben. Sofern der |UCSPRIMARYDN| als Active
Directory-kompatibler Domänencontroller genutzt werden soll, so kann die
Software bereits während der UCS-Installation ausgewählt werden.

Nach der erfolgreichen UCS-Installation muss die App |UCSUAS_p| installiert
werden. Jedes UCS System bietet ein webbasiertes Konfigurationsinterface an,
Univention Management Console, kurz UMC. Dies ist via Webbrowser erreichbar,
dazu kann einfach der Name oder die IP-Adresse des Servers in die Adresszeile
des Webbrowsers eingegeben werden. Es erscheint eine Kachel mit der Bezeichnung
System- und Domäneneinstellungen. Nach einem Klick auf die Kachel wird eine
Anmeldemaske angezeigt. Dort erfolgt die Anmeldung mit dem Benutzer
``Administrator`` und dem während der UCS-Installation vergebenen Passwort für
den Benutzer ``root``.

Nun kann die Kachel *App Center* geöffnet und dort die Applikation |UCSUAS_p|
installiert werden. Für die Installation ist den Anweisungen zu folgen, bspw.
kann eine Lizenzaktivierung notwendig sein. Details dazu sind im
:cite:t:`ucs-manual` unter :ref:`software-appcenter` zu finden.


.. _install-via-appcenter-primary-directory-node:

.. figure:: /images/appcenter_ucsschool.png
   :alt: Installation von |UCSUAS| über das Univention App Center

   Installation von |UCSUAS| über das Univention App Center

Nach dem Abschluss der Installation über das App Center erfolgt die
Konfiguration von |UCSUAS|. Diese wird mit dem
|UCSUAS|-Konfigurationsassistenten durchgeführt. Dieser ist in UMC über
den Bereich *Schul-Administration* erreichbar.

.. _install-umc-wizard-primary-directory-node:

.. figure:: /images/install-umc-wizard.png
   :alt: Starten des |UCSUAS|-Konfigurationsassistenten

   Starten des |UCSUAS|-Konfigurationsassistenten

Auf der ersten Seite fragt der Konfigurationsassistent nach dem
Installationsszenario. Hier ist die
``Multi-Server-Umgebung`` auszuwählen.

.. _install-umc-wizard-multi-server:

.. figure:: /images/installation-multi-server.png
   :alt: Multi-Server-Umgebung

   Multi-Server-Umgebung

Nach der abschließenden Bestätigung startet die Konfiguration von |UCSUAS|.
Dabei werden diverse Pakete installiert und konfiguriert. Die Dauer schwankt je
nach Geschwindigkeit der Internetverbindung und Serverausstattung.

Installation und Konfiguration von |UCSUAS| sollten mit einem Neustart des
Systems abgeschlossen werden.

.. important::

   Nach Abschluss der Installation auf dem |UCSPRIMARYDN| muss auf allen anderen
   gejointen Systemen der Domäne der Befehl
   :command:`univention-run-join-scripts` ausgeführt werden, damit der
   installierte |UCSUAS|-Join-Hook benötigte Konfigurationspakete auf den
   Systemen nachinstallieren kann.

   Dieser Vorgang kann je nach Rolle und Systemperformance mehrere Minuten
   dauern und darf nicht unterbrochen werden.

.. _installation-multi-backup:

Installation eines Backup Directory Node (optional)
---------------------------------------------------

Auf Servern mit der Rolle |UCSBACKUPDN_e| (kurz: Backup) werden alle
Domänendaten und SSL-Sicherheitszertifikate als Nur-Lese-Kopie gespeichert.

Ein Backup Directory Node dient als Fallback-System des |UCSPRIMARYDN|. Sollte
dieser ausfallen, kann ein Backup Directory Node die Rolle des |UCSPRIMARYDN|
dauerhaft übernehmen. Der Einsatz eines Backup Directory Node ist optional.

Es muss ein neues |UCSBACKUPDN| System installiert werden. Während des
Domänenbeitritts (oder der Ausführung von
:command:`univention-run-join-scripts`) werden auf diesem System durch den in
den vorigen Abschnitten bereits erwähnten |UCSUAS|-Join-Hook automatisch die
gleichen Pakete wie auf dem |UCSPRIMARYDN| installiert. Es werden dabei jedoch
nur die Softwarepakete installiert. Falls nach der Installation Änderungen an
der Konfiguration auf dem |UCSPRIMARYDN| vorgenommen werden, müssen diese
manuell auf den/die Backup-Systeme übertragen werden, damit diese in einem
*Backup2Master*-Szenario die Rolle des |UCSPRIMARYDN| ohne Probleme übernehmen
können.

Je nach Systemperformance und Netzanbindung wird der Domänenbeitritt einige
Minuten länger dauern als in reinen UCS-Domänen ohne |UCSUAS|.

Nach dem Domänenbeitritt (und damit der Installation von |UCSUAS|) sollte das
System neu gestartet werden.

.. _school-installation-replica-directory-node:

Installation eines Schulservers
-------------------------------

Der edukative Schulserver, im folgenden Schulserver genannt, liefert die
Anmeldedienste für Schüler und Lehrer an einer Schule.

Zusätzlich bietet der Schulserver die Funktionen für den IT-gestützten
Unterricht. Ob die Installation eines Schulservers für die jeweilige
|UCSUAS|-Umgebung notwendig ist, kann :cite:t:`ucsschool-scenario` entnommen
werden, welches unterschiedliche Anwendungsszenarien aufzeigt.

Soll ein Schulserver installiert werden, muss zunächst für diesen Schulserver
eine Schule angelegt werden. Das Anlegen von Schulen wird in
:ref:`school-setup-umc-schools-create` ausführlich beschrieben. Dieser Schritt
muss zwingend *vor* der Installation des Schulservers bzw. seinem
Domänenbeitritt erfolgen, da dieser sonst als normales UCS-System ohne spezielle
|UCSUAS|-Funktionalitäten eingerichtet wird.

Nach dem Anlegen der Schule muss ein UCS-System mit der Systemrolle
|UCSREPLICADN_e| installiert werden. Die :ref:`Installation von UCS
<installation-chapter>` ist in :cite:t:`ucs-manual` beschrieben. Während der
Installation ist darauf zu achten, dass der Rechnername bei der Installation mit
dem Namen des Schulservers übereinstimmt, der beim Anlegen der Schule angegeben
wurde.

Nach der Angabe des Schulservernamens wird vom UCS-Installer ab UCS 4.4-1 die
Rolle abgefragt, die der Schulserver in der |UCSUAS|-Domäne übernehmen soll. Für
einen edukativen Schulserver ist hier ``Schulserver im Edukativnetz``
auszuwählen. Der UCS-Installer gleicht die gemachte Angabe mit der Konfiguration
der bereits angelegten Schule ab und weist ggf. auf Widersprüche hin. Für die
Installation von |UCSUAS| muss im UCS-Installer keine zusätzliche Software
ausgewählt werden. Für |UCSUAS| notwendige Softwarepakete werden automatisch
mitinstalliert.

Nach der UCS-Installation und erfolgreichem Domänenbeitritt ist auf dem System
auch die App |UCSUAS_p| installiert.

Jedes UCS-System bietet ein webbasiertes Konfigurationsinterface an, Univention
Management Console, kurz UMC. Dies ist via Webbrowser erreichbar, dazu kann
einfach der Name oder die IP-Adresse des Servers in die Adresszeile des
Webbrowsers eingegeben werden. Es erscheint eine Kachel mit der Bezeichnung
*Systemeinstellungen*. Nach einem Klick auf die Kachel wird eine Anmeldemaske
angezeigt. Dort erfolgt die Anmeldung mit dem Benutzer ``Administrator``, sofern
noch nicht geändert, entspricht das Passwort dem während der |UCSPRIMARYDN|
Installation vergebenen Passwort für den Benutzer ``root``.

.. caution::

   Die *nachträgliche* Installation von |UCSUAS| auf
   einem bestehenden |UCSREPLICADN| und die Verwendung als Schulserver ist
   nicht möglich. Der Verwendungszweck des Systems wird während des
   Domänenbeitritts festgelegt.

   Falls das Anlegen der Schule und das Hinterlegen des Rechnernamens an der
   Schule versäumt wurde, wird das System während des Domänenbeitritts als
   normaler |UCSREPLICADN| ohne spezielle |UCSUAS|-Funktionalität eingerichtet.

   Soll das System trotzdem als Schulserver im Edukativ- oder
   Verwaltungsnetz eingesetzt werden, muss zunächst das existierende
   Rechnerobjekt im LDAP-Verzeichnisdienst entfernt werden. Anschließend
   ist der Rechnername, wie in
   :ref:`school-setup-umc-schools-modify` beschrieben, an der Schule
   zu hinterlegen. Abschließend muss das System von Grund auf neu mit
   UCS installiert werden und danach der |UCSUAS|-Domäne neu beitreten.

.. _school-installation-replica-directory-node-administrative:

Installation eines Verwaltungsservers (optional)
------------------------------------------------

Der Verwaltungsserver bietet Anmeldedienste für Mitarbeiter in der Verwaltung
an. Es ist nicht zwingend erforderlich, dass (an jeder Schule) ein
Verwaltungsserver installiert wird.

Für den Verwaltungsserver muss ein vom edukativen Netz physikalisch getrenntes
Netzwerksegment sowie ein eigenes IP-Subnetz verwendet werden, um Konflikte mit
dem Schulserver des Edukativnetzes zu vermeiden (siehe auch
:ref:`structure-edunet-vs-adminnet`).

Die Installation eines Verwaltungsserver erfolgt analog zur in
:ref:`school-installation-replica-directory-node` beschriebenen Installation des
Schulservers. Auch hier muss **vor** dem Domänenbeitritt der Rechnername des
Verwaltungsservers an der Schule eingetragen werden.
:ref:`school-setup-umc-schools-modify` beschreibt dies für bestehende Schulen.
Abweichend zur Installation eines edukativen Schulservers muss bei der
Installation eines Verwaltungsservers (ab UCS 4.4-1) als Rolle ``Schulserver im
Verwaltungsnetz`` ausgewählt werden. Auch hier wird ggf. bei festgestellten
Widersprüchen ein Hinweis angezeigt.

.. note::

   Bei der Verwendung des Verwaltungsnetzes muss vor dem Anlegen der ersten
   Schule bzw. vor der Installation des ersten Schulservers bzw.
   Verwaltungsservers darauf geachtet werden, dass auf allen |UCSUAS|-Systemen
   die UCR-Variable
   :envvar:`ucsschool/import/generate/policy/dhcp/dns/set_per_ou` auf den Wert
   ``false`` gesetzt wird. Dies lässt sich am besten über eine UCR-Richtlinie
   für die gesamte |UCSUAS|-Domäne erledigen.

   IP-Subnetze sowie DNS-Server müssen über das Importskript
   :command:`import_networks` (siehe in
   :ref:`school-schoolcreate-network-import`) importiert bzw. gesetzt werden, um
   einen fehlerfreien Betrieb zu gewährleisten.

.. _school-installation-domjoin:

(Erneuter) Domänenbeitritt eines Schulservers
---------------------------------------------

Die Einrichtung eines Schulservers ist auch ohne das oben beschriebene
UMC-Konfigurationsmodul möglich bzw. notwendig, wenn während des
Konfigurationsprozesses Probleme auftreten sollten. Nur in einem solchen
Szenario müssen die in diesem Abschnitt beschriebenen Schritte manuell
durchgeführt werden:

* Das System muss erneut der Domäne beitreten. Dies erfolgt auf der
  Kommandozeile durch Aufruf des Befehls :command:`univention-join`.

* Der |UCSPRIMARYDN| wird im Regelfall durch eine DNS-Abfrage ermittelt. Wenn
  das nicht möglich sein sollte, kann der Rechnername des |UCSPRIMARYDN| auch
  durch den Parameter :samp:`-dcname {HOSTNAME}` direkt angegeben werden. Der
  Rechnername muss dabei als vollqualifizierter Name angegeben werden, also
  beispielsweise ``primary.example.com``.

* Als Join-Account wird ein Benutzerkonto bezeichnet, das berechtigt ist,
  Systeme der UCS-Domäne hinzuzufügen. Standardmäßig ist dies der Benutzer
  ``Administrator`` oder ein Mitglied der Gruppe ``Domain Admins``. Der
  Join-Account kann durch den Parameter :samp:`-dcaccount {ACCOUNTNAME}` an
  :command:`univention-join` übergeben werden.

.. note::

   Der Name des Schulservers darf nur aus Kleinbuchstaben, Ziffern sowie dem
   Bindestrich bestehen (``a-z``, ``0-9`` und ``-``). Der Name darf nur mit
   einem Kleinbuchstaben beginnen, mit einem Kleinbuchstaben oder einer Ziffer
   enden und ist auf eine Länge von 12 Zeichen beschränkt. Bei Abweichungen von
   diesen Vorgaben kann es zu Problemen bei der Verwendung von Windows-Clients
   kommen.

.. _installation-multi-othersystems:

Installation sonstiger Systeme (optional)
-----------------------------------------

Während des Domänenbeitritts sonstiger Systeme (|UCSREPLICADN| ohne |UCSUAS|
oder |UCSMANAGEDNODE|) wird (sofern notwendig) über den |UCSUAS|-Join-Hook
automatisch die Installation der |UCSUAS|-App und notwendiger |UCSUAS|-Pakete
veranlasst. Weitere manuelle Schritte sind zunächst nicht zu beachten.
