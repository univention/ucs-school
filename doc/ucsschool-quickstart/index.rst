.. _quickstart-intro:

**********
Einleitung
**********

|UCSUAS| ist eine Erweiterung für Univention Corporate Server (UCS). Die
Installation besteht aus zwei Schritten:

* Installation von UCS

* Installation der Erweiterung |UCSUAS|

Dieser Quickstart Guide beschreibt die Installation und Einrichtung von
|UCSUAS| in einer Schritt-für-Schritt-Anleitung.

.. _quickstart-installation:

********************
Installation von UCS
********************

|UCSUAS| kann in zwei Varianten installiert werden:

* Als *Single-Server-Umgebung* für Installationen an einzelnen Schulen

* Als *Multi-Server-Umgebung* für Umgebungen mit mehreren Schulen

Dieser Quickstart Guide beschreibt die Installation als Single-Server-Umgebung.
Weiterführende Hinweise zu Multi-Server-Umgebungen finden sich in
:ref:`quickstart-ucsschool-multi-server` sowie im |UCSUAS|-Handbuch
:cite:t:`ucsschool-multi-server`.

UCS steht als 64 Bit-Variante (*amd64*) kostenlos im `Download-Bereich
<https://www.univention.de/download/download-ucs/>`_ zur Verfügung. Alternativ
kann UCS auch in der Amazon EC2 Cloud installiert (siehe :cite:t:`amazon-ec2`)
und für |UCSUAS| verwendet werden. Des Weiteren kann für die Installation von
|UCSUAS| auch das VMware-Image für UCS verwendet (siehe :cite:t:`ucs-vm-images`)
und darin die Erweiterung |UCSUASp| installiert werden. Auch hierfür gelten die
als nächstes beschriebenen abweichenden Einstellungen.

Wählen Sie für die Installation folgende abweichende Einstellungen vom UCS
Quickstart Guide :cite:t:`ucs-quickstart`, um |UCSUAS| zu installieren:

Systemrolle
   |UCSPRIMARYDN|

Software-Auswahl
   Hier können alle Auswahlkomponenten entfernt werden. Die spätere Installation
   der |UCSUAS|-Erweiterung installiert alle notwendigen Abhängigkeiten
   automatisch mit.

.. caution::

   Achten Sie darauf, dass der Hostname nur aus Kleinbuchstaben, Ziffern sowie
   dem Bindestrich bestehen (``a-z``, ``0-9`` und ``-``) und zur Trennung nur
   einzelne Punkte enthalten darf. Der Hostname darf außerdem nur mit einem
   Kleinbuchstaben beginnen, mit einem Kleinbuchstaben oder einer Ziffer enden
   und ist auf eine Länge von 13 Zeichen beschränkt.

.. _quickstart-ucsschool-installation:

*************************************
Installation der |UCSUAS|-Erweiterung
*************************************

Der folgende Abschnitt beschreibt die Installation der Erweiterung |UCSUAS| auf
einem UCS-System über Univention App Center. Dazu muss eine Anmeldung mit dem
Administrator-Konto (Benutzername: ``Administrator``) an der Univention
Management Console (:samp:`https://{server_ip}/umc` oder
:samp:`http://{server_ip}/umc`) erfolgen.

Bei der ersten Anmeldung muss im UMC-Modul *Willkommen!* eine UCS-Lizenz für das
Univention App Center freigeschaltet werden. Im Dialog, der über :guilabel:`Neue
Lizenz anfordern` geöffnet wird, muss dazu eine E-Mail-Adresse angegeben werden,
an die der freigeschaltete Lizenzschlüssel dann geschickt wird.

Der Lizenzschlüssel kann über das UMC-Modul *Willkommen!* importiert werden. Es
muss der Menüpunkt :guilabel:`Neue Lizenz importieren` ausgewählt werden. Nach
dem Import des Lizenzschlüssels kann das Univention App Center verwendet werden.

.. _install-via-app-center:

.. figure:: /images/appcenter-de.png

Im UMC-Modul App Center ist die Applikation |UCSUASp| auszuwählen und
anschließend auf :guilabel:`Installieren` zu klicken. Nach Abschluss der
Installation von |UCSUAS| kann in der Univention Management Console das neue
Modul *UCS\@school-Konfigurationsassistent* aufgerufen werden.

Standardmäßig wird bei der Erstinstallation von |UCSUAS| auf dem |UCSPRIMARYDN|
eine Demonstrationsschule inklusive Testnutzern konfiguriert. Die Schule trägt
den Namen *DEMOSCHOOL* und kann für eigene Tests verwendet werden. Das Passwort
für die automatisch angelegten Nutzer ``demo_student``, ``demo_teacher`` und
``demo_admin`` befindet sich in der Datei
:file:`/etc/ucsschool/demoschool.secret`. Um das Anlegen der
Demonstrationsschule zu verhindern, muss die UCR-Variable
:envvar:`ucsschool/join/create_demo` auf den Wert ``no`` gesetzt werden, bevor
der |UCSUAS|-Konfigurations-Assistent durchlaufen wird. Das Setzen der
UCR-Variable ist entweder über das UMC-Modul *Univention Configuration
Registry* oder auf der Kommandozeile mit dem Befehl :command:`ucr set
ucsschool/join/create_demo=no` möglich.

Der Assistent begleitet die notwendigen Konfigurationsschritte für |UCSUAS|:

* Im ersten Schritt wird die Option *Single-Server-Umgebung* ausgewählt.

* Dann wird der Name der Schule und ein Schulkürzel festgelegt (z.B.
  *Gesamtschule Nord* und *gsnord*).

Mit der Bestätigung der Einstellungen wird das System konfiguriert und benötigte
Pakete automatisch mitinstalliert. Der Frage nach dem Neustart der UMC sollte
zugestimmt werden, damit die |UCSUAS|-Module sofort verfügbar sind. Nach
Abschluss der Konfiguration ist die Installation von |UCSUAS| abgeschlossen.

.. _quickstart-user-management:

***************************************
Verwaltung der Schüler- und Lehrerdaten
***************************************

In einer Standard-UCS-Installation sind alle Benutzerkonten vom selben Typ und
unterscheiden sich nur anhand ihrer Gruppenmitgliedschaften. In einer
|UCSUAS|-Umgebung ist jeder Benutzer einer Rolle zugeordnet, aus der sich
Berechtigungen in der |UCSUAS|-Verwaltung ergeben:


Schüler
   *Schülern* wird in der Standardeinstellung kein Zugriff auf die
   Administrationsoberflächen gewährt. Sie können sich mit ihren Benutzerkonten
   nur an Windows-Clients anmelden und die für sie freigegebenen Dateifreigaben
   und Drucker verwenden.

Lehrer
   *Lehrer* erhalten gegenüber Schülern zusätzliche Rechte, um z.B. auf
   UMC-Module zugreifen zu können, die das Zurücksetzen von Schülerpasswörtern
   oder das Auswählen von Internetfiltern ermöglichen. Die für Lehrer
   freigegebenen Module können individuell definiert werden. Lehrer erhalten in
   der Regel aber nur Zugriff auf einen Teil der von der Univention Management
   Console bereitgestellten Funktionen.

Schuladministrator
   Vollen Zugriff auf die Schulverwaltungsfunktionen von |UCSUAS| erhalten die
   *Schuladministratoren*. Sie können z.B. Computer zu Rechnergruppen
   zusammenfassen, neue Internetfilter definieren oder auch Lehrerpasswörter
   zurücksetzen.

Bei der Konfiguration über den Assistenten wurde bereits ein Schulname
konfiguriert.

Als nächstes muss eine Schulklasse erstellt werden. In der Univention Management
Console kann mit *Klassen (Schulen)* aus dem Abschnitt Schuladministration eine
Schulklasse definiert werden, z.B. *1a*.

Nun werden über das Modul *Benutzer (Schulen)* zwei Schüler und ein Lehrerkonto
angelegt. Beiden Schülerkonten sollte die gerade angelegte Klasse zugewiesen
werden. Abschließend wird das angelegte Lehrerkonto mit *Lehrer Klassen
zuordnen* der Klasse zugeordnet.

.. _student-management:

.. figure:: /images/student-modify-de.png

Das oben beschriebene Anlegen der Benutzer erfolgt in den meisten
|UCSUAS|-Installationen z.B. durch automatisierte Import-Skripte. Die primäre
Verwaltung der Schülerdaten erfolgt üblicherweise weiterhin in der vom
jeweiligen Schulträger eingesetzten Schulverwaltungssoftware. Benutzerdaten der
Schüler und Lehrer werden dabei aus der Schulverwaltungssoftware exportiert und
über mitgelieferte Import-Skripte in |UCSUAS| importiert (typischerweise zum
Schuljahreswechsel). Über diese Import-Skripte lassen sich auch Rechnerkonten
und Drucker importieren.

.. _quickstart-module:

******
Module
******

|UCSUAS| stellt eine Reihe von Modulen für die Univention Management Console
bereit, die für den IT-gestützten Unterricht verwendet werden können. Im
Folgenden werden die Module kurz beschrieben. Eine ausführliche Beschreibung der
Verwendung der Module findet sich im Handbuch für Lehrer
:cite:t:`ucsschool-teacher`.

Einige Module stehen Lehrern und Schuladministratoren zur Verfügung und einige
Module nur Schuladministratoren. Je nachdem, ob die Anmeldung mit einem der oben
angelegten Lehrer oder dem Administrator erfolgt, erscheint nur eine Auswahl der
Module. Schüler erhalten keinen Zugriff auf die Module.

.. _ucsschool-module:

.. figure:: /images/module_overview_Administrator_admin.png

Passwörter (Schüler)
   *Passwörter (Schüler)* erlaubt Lehrern das Zurücksetzen von
   Schüler-Passwörtern. Die bestehenden Schüler-Passwörter können aus
   Sicherheitsgründen nicht ausgelesen werden; wenn Schüler ihr Passwort
   vergessen, muss ein neues Passwort vergeben werden. Schuladministratoren
   dürfen außerdem die Passwörter von Lehrern zurücksetzen.

Computerraum
   Das Modul *Computerraum* erlaubt die Kontrolle der Schüler-PCs und des
   Internetzugangs während einer Unterrichtsstunde. Der Internetzugang kann
   gesperrt und freigegeben werden und einzelne Internetseiten können gezielt
   freigegeben werden. Wenn eine entsprechende Software (Veyon) auf den
   Schüler-PCs installiert ist, besteht auch die Möglichkeit diese PCs zu
   steuern. So kann der Bildschirm gesperrt werden, so dass beispielweise in
   einer Chemie-Stunde die ungeteilte Aufmerksamkeit auf ein Experiment gelenkt
   werden kann. Außerdem kann der Bildschiminhalt eines PCs auf andere Systeme
   übertragen werden. Dies erlaubt es Lehrern, auch ohne einen Beamer
   Präsentationen durchzuführen.

Computerräume verwalten
   Mit dem Modul *Computerräume verwalten* werden Computer einer Schule einem
   Computerraum zugeordnet. Diese Computerräume können von den Lehrern dann
   zentral verwaltet werden, etwa in dem der Internetzugang freigegeben wird.

Helpdesk kontaktieren
   Jede Schule wird durch einen Helpdesk betreut, der in der Regel vom
   Schulträger bereitgestellt wird. Über das Modul *Helpdesk kontaktieren*
   können Lehrer und Schuladministratoren eine Anfrage stellen.

Arbeitsgruppen bearbeiten
   Jeder Schüler ist Mitglied seiner Klasse. Darüber hinaus gibt es die
   Möglichkeit mit dem Modul *Arbeitsgruppen bearbeiten* Schüler in
   klassenübergreifende Arbeitsgruppen einzuordnen. Das Anlegen einer
   Arbeitsgruppe legt automatisch einen Datenbereich auf dem Schulserver an, auf
   den alle Mitglieder der Arbeitsgruppe Zugriff haben. Lehrer können Schüler zu
   Arbeitsgruppen hinzufügen oder entfernen, aber keine neuen Arbeitsgruppen
   anlegen. Dies muss von einem Schuladministrator vorgenommen werden. Das Modul
   *Arbeitsgruppen bearbeiten* erlaubt Schuladministratoren neue
   Arbeitsgruppen anzulegen und diesen neben Schülern auch Lehrer zuzuweisen.

Drucker moderieren
   Mit dem Modul *Drucker moderieren* können Ausdrucke der Schüler geprüft
   werden. Die anstehenden Druckaufträge können vom Lehrer betrachtet und
   entweder verworfen oder an den Drucker weitergereicht werden. Dadurch werden
   unnötige oder fehlerhafte Ausdrucke vermieden.

Materialien verteilen
   Das Modul *Materialien verteilen* vereinfacht das Verteilen und Einsammeln
   von Unterrichtsmaterial an einzelne Schüler, Klassen oder Arbeitsgruppen.
   Optional kann eine Frist festgelegt werden. So ist es möglich, Aufgaben zu
   verteilen, die bis zum Ende der Unterrichtsstunde zu bearbeiten sind. Nach
   Ablauf der Frist werden die verteilten Materialien dann automatisch wieder
   eingesammelt und im Heimatverzeichnis des Lehrers abgelegt.

Unterrichtszeiten
   Das Modul *Unterrichtszeiten* erlaubt es Schuladministratoren, die Zeiträume
   der jeweiligen Unterrichtsstunde pro Schule zu definieren.

Lehrer Klassen zuordnen
   Für jede Klasse gibt es einen gemeinsamen Datenbereich. Damit Lehrer auf
   diesen Datenbereich zugreifen können, müssen sie mit dem Modul *Lehrer
   Klassen zuordnen* der Klasse zugewiesen werden.

Internetregeln definieren
   Für die Filterung des Internetzugriffs wird ein Proxy-Server eingesetzt, der
   bei dem Abruf einer Internetseite prüft, ob der Zugriff auf diese Seite
   erlaubt ist. Ist das nicht der Fall, wird eine Informationsseite angezeigt.
   Wenn Schüler beispielsweise in einer Unterrichtsstunde in der Wikipedia
   recherchieren sollen, kann eine Regelliste definiert werden, die Zugriffe auf
   alle anderen Internetseiten unterbindet. Diese Regelliste kann dann vom
   Lehrer zugewiesen werden. Mit der Funktion *Internetregeln definieren* können
   die Regeln verwaltet werden.

.. _quickstart-domain-join:

*************************************************
Domänenbeitritt eines Microsoft Windows 7-Clients
*************************************************

Microsoft Windows-Clients werden mithilfe von Samba integriert und verwaltet.
Die Windows-Clients authentifizieren sich dabei gegen den Samba-Server. Auch
Datei- und Druckdienste werden für die Windows-Clients über Samba
bereitgestellt. |UCSUAS| integriert Samba 4, die nächste Generation der
Samba-Suite. Es unterstützt Domänen-, Verzeichnis- und
Authentifizierungsdiensten, die kompatibel zu Microsoft Active Directory sind.
Dies ermöglicht die Verwendung der von Microsoft bereit gestellten Werkzeuge für
die Verwaltung von Benutzern oder Gruppenrichtlinien (GPOs).

Zuerst muss der PC in der Univention Management Console registriert werden. Dort
muss in der Modulgruppe *UCS\@school Administration* das Modul *Computer
hinzufügen* aufgerufen werden. Als *Computer-Typ* ist ``Windows-System``
auszuwählen. Die Angabe von *Name*, *IP-Adresse* und *MAC-Adresse* ist
verpflichtend. Die *Subnetzmaske* kann in den meisten Fällen auf der
Voreinstellung belassen werden.

Nun tritt der Microsoft Windows-Client der Domäne bei (in diesem Quickstart
Guide auf Basis von Windows 7). Der Beitritt kann nur mit einer Windows-Version
mit Domänenunterstützung durchgeführt werden, d.h. nicht mit Microsoft Windows 7
Home. Die Vorgehensweise gilt analog auch für Microsoft Windows 8.

Der Windows-Client muss DNS-Einträge aus der DNS-Zone der UCS-Domäne auflösen
können, d.h. der Schulserver sollte in den Netzwerkeinstellungen des
Windows-Clients als DNS-Server eingetragen werden.

Auf dem Windows-System muss die aktuelle Zeit konfiguriert werden. Wenn mit
Virtualisierung gearbeitet wird, muss beachtet werden, dass
Suspend/Resume-Zyklen zu inkorrekten Systemuhren führen können.

Über :menuselection:`Start --> Systemsteuerung --> System und Sicherheit -->
System` kann der Basiskonfigurationsdialog erreicht werden. Nun muss
*Einstellungen ändern* gewählt und auf :guilabel:`Ändern` geklickt werden.

.. _join-windows:

.. figure:: /images/join-win7-de.png

Für den Domänenbeitritt muss unter *Domäne* der Domänenname der Schule
verwendet werden, der bei der Installation gewählt wurde. Nach einem Klick auf
die Schaltfläche :guilabel:`OK` muss in das Eingabefeld *Ändern des
Computernamens, bzw. der Domäne* unter *Name* der ``Administrator``
und in das Eingabefeld *Kennwort* das bei der Einrichtung des |UCSPRIMARYDN|
verwendete Administrator-Kennwort eingetragen werden. Nun kann der
Domänenbeitritt mit einem Klick auf :guilabel:`OK` gestartet werden.

Abschließend sollte der Client neu gestartet werden.

Durch den Domänenbeitritt wird für den Microsoft Windows-Client automatisch ein
Eintrag in der Rechnerverwaltung und DNS-Einträge angelegt. Weitere Hinweise
finden sich im UCS-Handbuch im Kapitel :cite:t:`ucs-computer-management`.

.. _quickstart-manage-win-clients:

****************************************
Management von Microsoft Windows-Clients
****************************************

Die Netzkonfiguration der Microsoft Windows-Clients wird über in UCS integrierte
DNS- und DHCP-Dienste durchgeführt. Die MAC- und IP-Adressen werden beim Import
direkt zugewiesen. Weiterführende Hinweise finden sich im |UCSUAS|-Handbuch im
Abschnitt :cite:t:`ucsschool-computer-import`.

Die Windows-PCs der Schüler und Lehrer können über Gruppenrichtlinien
konfiguriert werden und ist im Kapitel :cite:t:`ucs-computer-windows` des
UCS-Handbuchs beschrieben.

Auf den Windows-Clients der Schüler kann die Software Veyon installiert werden.
Sie wird vom UMC-Modul Computerraumverwaltung verwendet und erlaubt Lehrern den
Desktop der Schüler einzuschränken und z.B. Bildschirme und Eingabegeräte zu
sperren. Außerdem kann ein Übertragungsmodus aktiviert werden, der die
Bildschirmausgabe des Desktops des Lehrers auf die Schülerbildschirme überträgt.
Veyon wird im Kapitel :cite:t:`ucsschool-veyon` |UCSUAS|-Handbuch dokumentiert.

.. _quickstart-ucsschool-multi-server:

********************************************************
Installation von |UCSUAS| in einer Multi-Server-Umgebung
********************************************************

Bei der Installation von |UCSUAS| in einer Multi-Server-Umgebung gibt es einen
zentralen Server in der Schulverwaltung und an jeder Schule einen lokalen
Schulserver. Auf diesem Schulserver laufen alle Dienste wie z.B. die Freigaben
für die Heimatverzeichnisse der Schüler, der Proxyserver oder die Druckdienste.
Es erfolgt dabei eine selektive Replikation der LDAP-Daten, d.h. auf den
einzelnen Schulservern sind nur die Daten der jeweiligen Schule gespeichert.

Die in diesem Quickstart Guide beschriebene Installation kann durch die
Installation weiterer Schulserver zu einer Multi-Server-Umgebung ausgebaut
werden. Die dazu nötigen Schritte sind im Kapitel
:cite:t:`ucsschool-multi-server` des |UCSUAS|-Handbuch beschrieben.

.. _quickstart-further-info:

****************************
Weiterführende Informationen
****************************

* Ausführliche Beschreibungen zum Konzept und zur Administration von |UCSUAS|
  können dem :cite:t:`ucsschool-admin` entnommen werden.

* Für Lehrer existiert darüber hinaus das gesonderte Dokument
  :cite:t:`ucsschool-teacher`, das die Verwendung der webbasierten
  Administrationsschnittstellen beschreibt.

* Im `Univention Wiki <https://wiki.univention.de/index.php/Main_Page>`_ finden sich u.a.
  verschiedene HOWTOs und Praxis-Tipps.

* Antworten auf häufig gestellte Fragen gibt es in der `Support und Knowledge
  Base zu finden <https://help.univention.com/>`_.

* Fragen zu UCS können auch im `Univention-Forum <https://help.univention.com/>`_
  gestellt werden.

* :cite:t:`ucs-quickstart`.

.. _biblio:

*************
Bibliographie
*************

.. bibliography::

.. spelling::

   Resume
   Veyon
