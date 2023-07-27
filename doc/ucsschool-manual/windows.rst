.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-windows-general:

********************************************************
Integration und Verwaltung von Microsoft Windows-Clients
********************************************************

Microsoft Windows-Clients werden in |UCSUCS| (UCS) mithilfe von Samba integriert
und verwaltet. Die Windows-Clients authentifizieren sich dabei gegen den
Samba-Server. Auch Datei- und Druckdienste werden für die Windows-Clients über
Samba bereitgestellt. Weitere Hinweise finden sich in
:ref:`school-windows-samba`.

Die Netzkonfiguration der Clients kann zentral über in UCS integrierte DNS- und
DHCP-Dienste durchgeführt werden. Weitere Hinweise finden sich in
:ref:`school-schoolcreate-computers-import`.

Beim Import von neuen Benutzern des Edukativnetzes über die Importskripte oder
über den Assistenten in der UMC werden automatisch windows-spezifische
Einstellungen zum Profilpfad und zum Heimatverzeichnispfad vorgenommen. Weitere
Hinweise finden sich in :ref:`school-setup-generic-windows-attributes`.

Auf den Windows-Clients der Schüler kann die Software *Veyon* installiert
werden. Sie erlaubt es Lehrern, über ein UMC-Modul den Desktop der Schüler
einzuschränken und z.B. Bildschirme und Eingabegeräte zu sperren. Außerdem kann
ein Übertragungsmodus aktiviert werden, der die Bildschirmausgabe des Desktops
des Lehrers auf die Schülerbildschirme überträgt. Die Installation von *Veyon*
wird in :ref:`school-windows-veyon` beschrieben.

Aufgrund einiger Limitierungen (u.a. von *Veyon*) kann auf Windows-Terminalservern
nicht der volle Funktionsumfang von |UCSUAS| genutzt werden. Die Verwendung von
Terminalservern mit |UCSUAS| wird daher nicht unterstützt.

.. important::

   Die App :program:`UCS\@school Veyon Proxy` wird in Single-Server-Umgebungen,
   sowie auf edukativen Schulservern automatisch installiert. Sie wird von
   |UCSUAS| angesprochen und ist nicht zur manuellen Verwendung gedacht.

   Die App **darf nicht** manuell deinstalliert werden.

.. _school-windows-samba:

Anmeldedienste mit Samba
========================

|UCSUAS| integriert *Samba 4*. Die Unterstützung von Domänen-, Verzeichnis- und
Authentifizierungsdiensten, die kompatibel zu Microsoft Active Directory sind,
erlauben den Aufbau von Active Directory-kompatiblen Windows-Domänen. Diese
ermöglichen u.a. die Verwendung der von Microsoft bereit gestellten Werkzeuge
beispielsweise für die Verwaltung von Benutzern oder Gruppenrichtlinien (GPOs).
Univention hat die benötigten Komponenten für die Bereitstellung von Active
Directory kompatiblen Domänendiensten mit Samba 4 getestet und in enger
Zusammenarbeit mit dem Samba-Team in UCS integriert.

.. caution::

   Bei der Verwendung von Samba 4 in einer Multi-Server-Umgebung ist es zwingend
   erforderlich, dass alle Windows-Clients ihren jeweiligen Schul-DC als
   DNS-Server verwenden, um einen fehlerfreien Betrieb zu gewährleisten.

   Windows-Clients des Edukativnetzes, die ihre DNS-Einstellungen über DHCP
   beziehen, erhalten in der Standardeinstellung automatisch die IP-Adresse des
   Schul-DCs als DNS-Server zugewiesen. Dafür wird beim Joinen eines
   Schulservers automatisch am unter dem Schul-OU-Objekt liegenden
   DHCP-Container eine DHCP-DNS-Richtlinie verknüpft. Das automatische
   Verknüpfen dieser Richtlinie kann über das Setzen einer UCR-Variable auf dem
   |UCSPRIMARYDN| *und* dem Schulserver deaktiviert werden. Die folgende
   Variable muss vor der Installation von |UCSUAS| oder dem Update des Systems
   gesetzt werden:

   .. code-block:: console

      $ ucr set ucsschool/import/generate/policy/dhcp/dns/set_per_ou=false


   Dies lässt sich am besten über eine UCR-Richtlinie für die gesamte
   |UCSUAS|-Domäne erledigen. Wurde die Variable versehentlich nicht gesetzt,
   werden automatisch fehlende DHCP-DNS-Richtlinien wieder angelegt und mit den
   entsprechenden DHCP-Container der Schul-OU-Objekte verknüpft. Dies kann
   gerade in Verwaltungsnetzen zu Fehlfunktionen führen (siehe auch
   :ref:`structure-edunet-vs-adminnet`).

Bei Neuinstallationen von |UCSUAS| wird standardmäßig Samba 4 installiert.
Umgebungen, die von einer Vorversion aktualisiert werden, müssen von Samba 3 auf
Samba 4 migriert werden. Das dafür notwendige Vorgehen ist unter der folgenden
URI dokumentiert: :uv:help:`UCS\@school Samba 3 to Samba 4 Migration
<21846>`.

Weiterführende Hinweise zur Konfiguration von Samba finden sich in
:ref:`windows-services-for-windows` in :cite:t:`ucs-manual`.

.. _school-windows-shares:

Server für Dateifreigaben
=========================

Beim Anlegen einer neuen Klasse bzw. eines Benutzers wird automatisch eine
Klassenfreigabe für die Klasse bzw. eine Heimatverzeichnisfreigabe für den
Benutzer eingerichtet. Der für die Einrichtung der Freigabe notwendige
Dateiserver wird in den meisten Fällen ohne manuellen Eingriff bestimmt. Dazu
wird am Schul-OU-Objekt bei der Registrierung einer Schule automatisch der in
der |UCSUMC| angegebene Schulserver als Dateiserver jeweils für Klassen- und
Benutzerfreigaben hinterlegt.

Die an der Schul-OU hinterlegte Angabe bezieht sich ausschließlich auf neue
Klassen- und Benutzerobjekte und hat keinen Einfluss auf bestehende Objekte im
LDAP-Verzeichnis. Durch das Bearbeiten der entsprechenden Schul-OU im UMC-Modul
*LDAP-Verzeichnis* können die Standarddateiserver für die geöffnete Schul-OU
nachträglich modifiziert werden.

Es ist zu beachten, dass die an der Schul-OU hinterlegten Dateiserver nur in
einer Multi-Server-Umgebung ausgewertet werden. In einer Single-Server-Umgebung
wird für beide Freigabetypen beim Anlegen neuer Objekte immer der |UCSPRIMARYDN|
als Dateiserver konfiguriert.

.. _school-windows-samba4netlogon:

Netlogon-Skripte für Samba 4 Umgebung
=====================================

In UCS-Umgebungen mit mehreren Samba 4 Domänencontrollern werden in der
Standardeinstellung alle Dateien der *NETLOGON*-Dateifreigabe automatisch (durch
die *SYSVOL*-Replikation) zwischen allen Samba 4 Domänencontrollern repliziert.
Beim Einsatz von |UCSUAS| kann es bei der Verwendung von domänenweiten
Benutzerkonten und benutzerspezifischen Netlogon-Skripten zu
Synchronisationskonflikten kommen. Konflikte können ebenfalls bei eigenen,
standortbezogenen Netlogon-Skripten auftreten.

In diesen Fällen ist es ratsam, die Synchronisation der *NETLOGON*-Freigabe zu
unterbinden, indem ein abweichendes Verzeichnis für die *NETLOGON*-Freigabe
definiert wird. Das Verzeichnis darf dabei nicht unterhalb der
*SYSVOL*-Dateifreigabe (:file:`/var/lib/samba/sysvol/{REALM}/`) liegen.

Das folgende Beispiel setzt das Verzeichnis der *NETLOGON*-Freigabe auf
:file:`/var/lib/samba/netlogon/` und passt ebenfalls das Verzeichnis für die
automatisch generierten Benutzer NETLOGON-Skripte an:

.. code-block:: console

   $ ucr set samba/share/netlogon/path=/var/lib/samba/netlogon
   $ ucr set ucsschool/userlogon/netlogon/path=/var/lib/samba/netlogon/user


Die zwei UCR-Variablen müssen auf allen Samba 4 Domänencontrollern gesetzt
werden. Dies kann z.B. in der UMC über eine UCR-Richtlinien global definiert
werden. Nach der Änderung müssen die Dienste ``samba`` und
``univention-directory-listener`` neu gestartet werden:

.. code-block:: console

   $ service samba restart
   $ service univention-directory-listener restart


.. _school-windows-veyon:

*Veyon* Installation auf Windows-Clients
========================================

Für die Kontrolle und Steuerung der Schüler-PCs integriert |UCSUAS| optional die
Software *Veyon*. Dieser Abschnitt beschreibt die Installation von *Veyon* auf
den Schüler-PCs. Die Administration durch die Lehrkräfte ist in
:cite:t:`ucsschool-teacher` beschrieben.

Für die Nutzung der Rechnerüberwachungs- und Präsentationsfunktionen in der
Computerraumverwaltung (siehe :ref:`ucsschool-modules`) wird
vorausgesetzt, dass auf den Windows-Clients die Software *Veyon* installiert
wurde und als Computerraum Backend des entsprechenden Computerraums *Veyon*
gesetzt ist (siehe :ref:`school-setup-generic-computerroom`).

.. versionadded:: 4.4v9

   Seit |UCSUAS| 4.4 v9 sind Windows-Binärpakete für die Open Source-Software
   *Veyon* in |UCSUAS| enthalten.

Die Binärpakete sind direkt über die Samba-Freigabe *Veyon-Installation* abruf-
und installierbar. Die Installationsdatei der 64-Bit Version von *Veyon* findet
sich auf dem Schulserver im Verzeichnis
:file:`/usr/share/ucs-school-veyon-windows/`.

Interoperabilitätstests zwischen |UCSUAS| und *Veyon* wurden ausschließlich mit
der von |UCSUAS| mitgelieferten *Veyon* Version unter Windows 7 und Windows 10 (64
Bit) durchgeführt.

.. _school-windows-veyon-fig1:

.. figure:: /images/veyon-installation.png
   :alt: *Veyon* Installation: Auswahl der Komponenten

   *Veyon* Installation: Auswahl der Komponenten

*Veyon* bringt ein Installationsprogramm mit, das durch alle notwendigen Schritte
führt. Während der Installation sollte nur der *Veyon Service* sowie der
*Interception driver* installiert werden. Der *Veyon Master* wird für die
Funktion von |UCSUAS| nicht benötigt.

.. _school-windows-veyon-fig2:

.. figure:: /images/veyon-auth-method.png
   :alt: *Veyon* Konfiguration: Auswahl der Authentifizierungs-Methode

   *Veyon* Konfiguration: Auswahl der Authentifizierungs-Methode

Nach der Installation von *Veyon* auf dem Windows-Client muss das Programm mit
dem installierten *Veyon Configurator* für eine Schlüsseldatei-Authentifizierung
konfiguriert werden. Zunächst muss im *Veyon Configurator* unter
:menuselection:`Allgemein --> Authentifizierung` die Methode
Schlüsseldatei-Authentifizierung ausgewählt werden.

.. _school-windows-veyon-fig3:

.. figure:: /images/veyon-access-control.png
   :alt: *Veyon* Konfiguration: Zugriffskontrolle

   *Veyon* Konfiguration: Zugriffskontrolle

Anschließend muss unter *Zugriffskontrolle* die Checkbox *Verwendung von
Domaingruppen aktivieren* aktiviert werden. Als *Benutzergruppen-Backend* wird
der Standard *Systembenutzergruppen* verwendet.

.. _school-windows-veyon-fig4:

.. figure:: /images/veyon-key-import.png
   :alt: *Veyon* Konfiguration: Schlüsselimport

   *Veyon* Konfiguration: Schlüsselimport

Schließlich muss der öffentliche Schlüssel importiert werden, damit der
Schulserver Zugriff auf das installierte *Veyon* Backend erhält. Der Import kann
mit :menuselection:`Authentifizierungsschlüssl --> Schlüssel importieren` durchgeführt
werden. Dort ist der *Veyon* Schlüssel des Schulservers anzugeben.

Der Schlüssel wird automatisch auf der SYSVOL-Freigabe des Schulservers unter
dem Namen der Schuldomäne unter :file:`scripts/veyon-cert_{SERVERNAME}.pem`
abgelegt. (U.U. liegt dort zusätzlich eine Datei :file:`veyon-cert.pem` *ohne*
den Namen des Servers. Diese sollte nicht verwendet werden.) Im Dialog
*Authentifizierungsschlüsselname* muss der Name *teacher* angegeben werden.
Außer den beschriebenen Konfigurationen müssen keine weiteren Anpassungen
vorgenommen werden.

Der Konfigurationstest im *Veyon Configurator* unter :menuselection:`Allgemein
--> Authentifizierung --> Testen` wird trotz korrekter Einrichtung fehlschlagen.
Die korrekte Einrichtung kann im *Computerraum* Modul überprüft werden. Hier
sollte sich der Punkt neben dem Namen des eingerichteten Windows Clients
dunkelgrau färben.

Außerdem sollte auf den Windows-Clients sichergestellt werden, dass die
installierte System-Firewall so konfiguriert ist, dass Port ``11100`` nicht
blockiert wird. Dies ist Voraussetzung für eine funktionierende Umgebung, da
*Veyon* diesen Port für die Kommunikation mit dem Schulserver bzw. anderen
Computern verwendet.
