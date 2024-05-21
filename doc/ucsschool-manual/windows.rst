.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
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

Computerraumüberwachung in |UCSUAS| mit Veyon
=============================================

`Veyon <https://veyon.io/de/>`__ ist eine freie und quelloffene Software zur
plattformübergreifenden Überwachung und Steuerung von Computern.
In |UCSUAS| können Sie *Veyon* verwenden,
um in Computerräumen die Computer von Schülern zu steuern und zu überwachen.

Sie können *Veyon* mit den folgenden Möglichkeiten nutzen:

* über die integrierte |UCSUAS|-Web-Oberfläche
* direkt über die von *Veyon* bereitgestellte Windows Applikation :program:`Veyon Master`.

Damit Sie die Web-Oberfläche nutzen können, müssen Sie die folgenden Installations- und Konfigurationsschritte abschließen:

#. :ref:`school-windows-veyon-clients-students`
#. :ref:`school-windows-veyon-config-web`

Alternativ können Sie die Rechner so einrichten,
dass Sie die Windows Applikation :program:`Veyon Master` verwenden.
Für :program:`Veyon Master` müssen Sie die folgenden Schritte abschließen:

#. :ref:`school-windows-veyon-clients-students`
#. :ref:`school-windows-veyon-clients-teachers`
#. :ref:`school-windows-veyon-master`

Lehrende, die den :program:`Veyon Master` verwenden,
finden Informationen im :external+veyon-docs:doc:`Veyon-Benutzerhandbuch <user/index>`.

Welche Möglichkeit Sie wählen,
hängt neben den verfügbaren Features auch von der Anzahl der gleichzeitig zu überwachenden Computer bzw. Computerräume ab.
Ab einer Anzahl von mehr als 80 aktiven Computern,
empfiehlt sich die Nutzung von :program:`Veyon Master`, siehe :ref:`school-windows-veyon-master`.

.. important::

   Auf den Windows-Clients muss in jedem Fall sichergestellt werden,
   dass die installierte System-Firewall den Port ``11100`` nicht blockiert.
   Der offene Port ``11100`` ist Voraussetzung für eine funktionierende Veyon-Umgebung,
   da Veyon diesen Port für die Kommunikation mit dem Schulserver bzw. anderen Computern verwendet.

.. seealso::

   :external+veyon-docs:ref:`ConfImportExport` im Veyon-Administrationshandbuch
      für Information über Werkzeuge,
      die die Übertragung von Konfigurationen erleichtern.


.. _schools-windows-veyon-proxy-requirements:

Systemanforderungen des UCS\@school Veyon Proxy
-----------------------------------------------

Wenn Sie die integrierte Web-Oberfläche zur Überwachung der Computerräume verwenden,
steigen die Hardwareanforderungen an den Schulserver.
:numref:`schools-windows-veyon-proxy-requirements-table` liefert eine Orientierung über die Hardwareanforderungen.

.. list-table:: Benötigte Systemressourcen unter Last
   :widths: 4 4 4
   :header-rows: 1
   :name: schools-windows-veyon-proxy-requirements-table

   * - Anzahl gleichzeitig aktiver Computer
     - Arbeitsspeicher
     - Ausgelastete Prozessoren
   * - 20
     - 500 MB
     - 2 vCPU / Threads
   * - 40
     - 1000 MB
     - 3 vCPU / Threads
   * - 80
     - 2000 MB
     - 6 vCPU / Threads

Die Prozessorauslastung hängt stark vom eingesetzten System bzw. der Umgebung ab.
Die aufgeführten benötigten Systemressourcen wurden mit einem
``Intel® Xeon® Silver 4314 Prozessor`` gemessen.

.. note::

   Bei mehr als 80 aktiven Computern ist der direkte Einsatz von :program:`Veyon Master` empfehlenswert.

.. _school-windows-veyon-clients-students:

Veyon Installation auf Windows-Clients von Schülern
---------------------------------------------------

Dieser Abschnitt beschreibt die Installation von *Veyon* auf den Schüler-PCs.
Für Informationen über die Administration über die |UCSUAS| Web-Oberfläche durch Lehrkräfte,
siehe :cite:t:`ucsschool-teacher`.

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

*Veyon* bringt ein Installationsprogramm mit, das durch alle notwendigen Schritte führt.
Installieren Sie *Veyon Service* sowie *Interception driver*.
Auf den Schüler-PCs ist kein :program:`Veyon Master` nötig.

.. _school-windows-veyon-config-web:

Veyon Konfiguration für die |UCSUAS| Web-Oberfläche
---------------------------------------------------

Falls eine direkte Steuerung über den :program:`Veyon Master` gewünscht ist, ist dieser
Abschnitt nicht notwendig und kann übersprungen werden.


Nach der Installation von *Veyon* auf dem Windows-Client muss das Programm mit
dem installierten *Veyon Configurator* für eine Schlüsseldatei-Authentifizierung
konfiguriert werden. Zunächst muss im *Veyon Configurator* unter
:menuselection:`Allgemein --> Authentifizierung` die Methode
Schlüsseldatei-Authentifizierung ausgewählt werden.

.. _school-windows-veyon-fig2:

.. figure:: /images/veyon-auth-method.png
   :alt: *Veyon* Konfiguration: Auswahl der Authentifizierungs-Methode

   *Veyon* Konfiguration: Auswahl der Authentifizierungs-Methode

Anschließend muss unter *Zugriffskontrolle* die Checkbox *Verwendung von
Domaingruppen aktivieren* aktiviert werden. Als *Benutzergruppen-Backend* wird
der Standard *Systembenutzergruppen* verwendet.

.. _school-windows-veyon-fig3:

.. figure:: /images/veyon-access-control.png
   :alt: *Veyon* Konfiguration: Zugriffskontrolle

   *Veyon* Konfiguration: Zugriffskontrolle


Schließlich muss der öffentliche Schlüssel importiert werden, damit der
Schulserver Zugriff auf das installierte *Veyon* Backend erhält. Der Import kann
mit :menuselection:`Authentifizierungsschlüssl --> Schlüssel importieren` durchgeführt
werden. Dort ist der *Veyon* Schlüssel des Schulservers anzugeben.

.. _school-windows-veyon-fig4:

.. figure:: /images/veyon-key-import.png
   :alt: *Veyon* Konfiguration: Schlüsselimport

   *Veyon* Konfiguration: Schlüsselimport

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


.. _school-windows-veyon-clients-teachers:

Veyon Installation auf Windows-Clients von Lehrern
--------------------------------------------------

Dieser Abschnitt beschreibt die Installation von *Veyon* auf Lehrer-PCs.
Wenn Sie nur die |UCSUAS| Web-Oberfläche verwenden, können Sie diesen Abschnitt überspringen.

Sie können die *Veyon* Binärpakete direkt über die Samba-Freigabe *Veyon-Installation* abrufen und installieren.
Die Installationsdatei der 64-Bit Version von *Veyon* finden Sie auf dem Schulserver im Verzeichnis
:file:`/usr/share/ucs-school-veyon-windows/`.

Univention hat Interoperabilitätstests zwischen |UCSUAS| und *Veyon* mit
der von |UCSUAS| mitgelieferten *Veyon* Version unter Windows 7 und Windows 10 (64
Bit) durchgeführt.

*Veyon* bringt ein Installationsprogramm mit, das durch alle notwendigen Schritte führt.
Während der Installation müssen Sie alle aufgelisteten Komponenten installieren.

.. _school-windows-veyon-fig5:

.. figure:: /images/veyon-installation-teacher.png
   :alt: *Veyon* Installation: Auswahl der Komponenten

   *Veyon* Installation: Auswahl der Komponenten

Für eine erfolgreiche Authentifizierung zwischen Lehrer- und Schüler-PCs
zur Überwachung und Steuerung wählen Sie entweder die *Anmeldeauthentifizierung* oder die *Schlüsselauthentifizierung*
im Abschnitt *Allgemein* des *Veyon Configurator*, sowohl auf den Lehrer- als auch auf den Schüler-PCs.
Weitere Details finden Sie unter :external+veyon-docs:ref:`ConfAuthentication` im Veyon-Administrationshandbuch.

.. tip::

   Bei einer Migration von der |UCSUAS| Web-Oberfläche hin zum :program:`Veyon Master` können Sie die bestehenden
   Schlüssel wiederverwenden. Kopieren Sie den privaten Schlüssel :file:`/etc/ucsschool-veyon/key.pem`
   von dem Schulserver auf den Lehrer-Computer und importieren Sie diesen mit dem *Veyon Configurator*.
   Eine Änderung der Schüler-PCs ist damit nicht notwendig.

.. _school-windows-veyon-master:

Einrichten des :program:`Veyon Master`
--------------------------------------

Alternativ zur Kontrolle von Computern über die Computerraum-Weboberfläche von |UCSUAS| können Sie :program:`Veyon Master` direkt verwenden.
Gehen Sie durch die nachfolgenden Konfigurationsschritte, um :program:`Veyon Master` auf mehreren Computern einzurichten.

.. tip::

   Es gibt Integrationstests für *Veyon*,
   die Sie nach Abschluss aller Konfigurationsschritte im Veyon Configurator durchführen können.
   Die Tests müssen erfolgreich sein.
   Die Tests finden Sie auf der letzten Seite der *LDAP-Basic* Einstellungen.


.. note::

   Zu allen Bildern der grafischen Benutzerschnittstelle des Veyon Configurator
   enthält dieses Kapitel ergänzend Programmblöcke in PowerShell,
   die auf die Veyon CLI zurückgreifen.
   Sie können die Programmblöcke z.B. als Bausteine zur Automatisierung verwenden.

.. _school-windows-veyon-master-create-user:

Erstellen eines Veyon Benutzers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Erstellen Sie ein :external+uv-manual:ref:`einfaches Authentisierungskonto <users-general>`
auf dem Primary Directory Node mit dem UMC-Modul :guilabel:`Benutzer`.
*Veyon* verwendet das Authentisierungskonto für die LDAP-Verbindung.
:numref:`school-windows-veyon-master-create-user-cli` zeigt die Erstellung des Kontos auf der
Kommandozeile.

.. code-block:: bash
   :caption: Einrichten eines einfachen Authentisierungskonto mit UDM.
   :name: school-windows-veyon-master-create-user-cli

   VEYON_PASSWORD="veyon-user-account-password"  # Passen Sie dieses Passwort an!
   SCHOOL_NAME="school1"

   udm users/ldap create --position "cn=users,ou="$SCHOOL_NAME",$(ucr get ldap/base)" \
      --set username="veyon-$SCHOOL_NAME" \
      --set lastname="veyon-$SCHOOL_NAME" \
      --set password="$VEYON_PASSWORD"

LDAP-Basiseinstellungen
~~~~~~~~~~~~~~~~~~~~~~~

Als nächstes müssen Sie die Einstellungen für die Authentisierung setzen.
Hierfür können Sie sowohl den *Veyon Configurator* als auch die ``veyon-cli`` Kommandozeilen-Schnittstelle verwenden.
Beide Werkzeuge wurden in den vorangegangenen Schritten mit *Veyon* auf den Windows-Clients installiert.
Viele der Einstellungen in diesem Abschnitt hängen von der Umgebung ab und müssen angepasst werden.
Die Kommentare am Ende einer Zeile mit ``veyon-cli config set ...`` verweisen auf die Kennzeichnung in der grafischen Benutzeroberfläche des *Veyon Configurator*.

Vor der Ausführung der Befehle in :numref:`school-windows-veyon-master-ldap-settings-cli`
müssen Sie das öffentliche Zertifikat der Zertifizierungsstelle der UCS Domäne auf den lokalen Rechner kopieren.
Das Wurzelzertifikat können Sie über die |UCSUMC| herunterladen.
Setzen Sie anschließend die Variable ``$CA_CERTIFICATE_PATH`` auf den Wert,
der dem Pfad des Zertifikats entspricht.
Wenn Sie die grafische Benutzeroberfläche zur Konfiguration verwenden, muss der Dateipfad
manuell eingetragen werden, da bei der interaktiven Dateiauswahl nur PEM-Dateien angezeigt werden.

..
   The comment at the end of a 'config set' statement corresponds to the
   label of the option in the Veyon configurator interface.

.. code-block:: powershell
   :caption: Setzen der LDAP-Basiseinstellungen über die Veyon Kommandozeilen-Schnittstelle
   :name: school-windows-veyon-master-ldap-settings-cli

   # Diese Variablen müssen auf das Zielsystem angepasst werden:
   $LDAP_BASE = 'dc=univention,dc=de'
   $SCHOOL_FQDN = 'school1.univention.de'
   $VEYON_USER = "uid=veyon-school1,cn=users,ou=school1,$LDAP_BASE"
   $VEYON_PASSWORD = 'veyon-user-account-password'  # Passen Sie dieses Passwort an!
   $CA_CERTIFICATE_PATH = 'path-to-tls-ldap-certificate'

   cd 'C:\Program Files\Veyon\'

   .\veyon-cli config set LDAP/ServerHost "$SCHOOL_FQDN"  # LDAP-Server
   .\veyon-cli config set LDAP/ServerPort 7389  # LDAP-Port
   .\veyon-cli config set LDAP/BindPassword $VEYON_PASSWORD # Bind-Passwort
   .\veyon-cli config set LDAP/BindDN "$VEYON_USER"  # Bind-DN

   .\veyon-cli config set LDAP/ConnectionSecurity 1  # Verschlüsselungsprotokoll (1 = TLS)
   .\veyon-cli config set LDAP/TLSVerifyMode 2  # TLS-Zertifikatsüberprüfung
   .\veyon-cli config set LDAP/TLSCACertificateFile "$CA_CERTIFICATE_PATH"  # Benutzerdefinierte CA-Zertifikatsdatei
   .\veyon-cli config set LDAP/UseBindCredentials true  # Bind-Zugangsdaten verwenden

   .\veyon-cli config set LDAP/BaseDN "$LDAP_BASE"  # Fester Base-DN
   .\veyon-cli config set NetworkObjectDirectory/Plugin '{6f0a491e-c1c6-4338-8244-f823b0bf8670}'  # Backend (Setzt das Netzwerkobjektverzeichnis zu "LDAP Basic ...")



.. figure:: /images/veyon-master-configuration-ldap-base-settings.png
   :alt: :program:`Veyon Master` Konfiguration: Beispiel für LDAP Grundeinstellungen

   :program:`Veyon Master` Konfiguration: Beispiel für LDAP Grundeinstellungen

.. _school-windows-veyon-master-ldap-env:

LDAP-Umgebungseinstellungen
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Die folgenden Einstellungen sind so gewählt, dass Standorte im :program:`Veyon Master` den Computerräumen
von |UCSUAS| entsprechen.

.. code-block:: powershell
   :caption: Setzen der LDAP-Umgebungseinstellungen über die Veyon Kommandozeilen-Schnittstelle

   cd 'C:\Program Files\Veyon\'

   .\veyon-cli config set LDAP/RecursiveSearchOperations true  # Rekursive Suchoperationen in Objektbäumen durchführen
   .\veyon-cli config set LDAP/UserLoginNameAttribute uid  # Attribut Benutzeranmeldename
   .\veyon-cli config set LDAP/GroupMemberAttribute uniqueMember  # Attribut Gruppenmitglied
   .\veyon-cli config set LDAP/ComputerDisplayNameAttribute displayName  # Attribut Computeranzeigename
   .\veyon-cli config set LDAP/ComputerHostNameAttribute cn  # Attribut Computerhostname
   .\veyon-cli config set LDAP/ComputerHostNameAsFQDN false  # Hostnamen sind als vollqualifizierte Domainnamen gespeichert
   .\veyon-cli config set LDAP/ComputerMacAddressAttribute macAddress  # macAddress
   .\veyon-cli config set LDAP/LocationNameAttribute cn  # Attribute Standortname


.. figure:: /images/veyon-master-configuration-ldap-environment-settings.png
   :alt: :program:`Veyon Master` Konfiguration: LDAP Umgebungseinstellungen

   :program:`Veyon Master` Konfiguration: LDAP Umgebungseinstellungen

.. _school-windows-veyon-master-ldap-advanced-settings:

Erweiterte Einstellungen
~~~~~~~~~~~~~~~~~~~~~~~~

Dieser Abschnitt zeigt, wie Sie die erweiterten LDAP Einstellungen setzen müssen,
um relevante Benutzer, Gruppen und Computer zu identifizieren.
Die folgenden Einstellungen sind so gewählt, dass Standorte im :program:`Veyon Master` den Computerräumen von |UCSUAS| entsprechen:

.. code-block:: powershell
   :caption: Setzen der erweiterten LDAP-Einstellungen über die Veyon Kommandozeilen-Schnittstelle

   cd 'C:\Program Files\Veyon\'

   .\veyon-cli config set LDAP/UsersFilter '(|(ucsschoolRole=student*)(ucsschoolRole=teacher*))' # Filter für Benutzer
   .\veyon-cli config set LDAP/UserGroupsFilter '(objectClass=ucsschoolGroup)'  # Filter für Benutzergruppen
   .\veyon-cli config set LDAP/ComputersFilter '(objectClass=ucsschoolComputer)'  # Filter für Computer
   .\veyon-cli config set LDAP/QueryNestedUserGroups false  # Verschachtelte Benutzergruppen abfragen
   .\veyon-cli config set LDAP/IdentifyGroupMembersByNameAttribute false  # Identifizierung von Gruppenmitgliedern
   .\veyon-cli config set LDAP/ComputerGroupsFilter '(&(ucsschoolRole=computer_room:school:*)(!(cn=*all-windows-hosts*)))' # Filter für Computergruppen
   .\veyon-cli config set LDAP/ComputerLocationsByContainer false  # Computercontainer oder OUs
   .\veyon-cli config set LDAP/ComputerLocationsByAttribute false  # Attribut Standort in Computerobjekten

.. figure:: /images/veyon-master-configuration-ldap-advanced-settings.png
   :alt: :program:`Veyon Master` Konfiguration: LDAP Erweiterte Einstellungen

   :program:`Veyon Master` Konfiguration: LDAP Erweiterte Einstellungen

.. _school-windows-veyon-master-behavior-settings:

Verhaltenseinstellungen des :program:`Veyon Master`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dieser Abschnitt zeigt optionale empfohlene Einstellungen.
In Umgebungen mit vielen Computerräumen kann es sinnvoll sein, nur den Standort bzw. Computerraum anzuzeigen,
in welchem sich auch der aktuell genutzte Computer befindet.
Bei Umgebungen mit vielen Computerräumen kann es sonst unübersichtlich werden.
Die Einstellung ``HideLocalComputer`` verbirgt den eigenen Computer in der Darstellung.

.. code-block:: powershell
   :caption: Setzen der :program:`Veyon Master` Verhaltens-Einstellungen über die Veyon Kommandozeilen-Schnittstelle

   cd 'C:\Program Files\Veyon\'

   .\veyon-cli config set Master/ShowCurrentLocationOnly true  # Nur aktuellen Standort anzeigen
   .\veyon-cli config set Master/HideLocalComputer true  # Lokalen Computer ausblenden

.. figure:: /images/veyon-master-configuration-master-behavior.png
   :alt: :program:`Veyon Master` Konfiguration: Verhalten des :program:`Veyon Masters`

   :program:`Veyon Master` Konfiguration: Verhalten des :program:`Veyon Master`
