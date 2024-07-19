.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-setup-generic:

************************
Erweiterte Konfiguration
************************

.. _school-setup-generic-print-moderation:

Einrichtung der Druckmoderation
===============================

Um unnötige oder fehlerhafte Druckaufträge zu minimieren, bietet |UCSUAS| den
Lehrern die Möglichkeit, Druckaufträge zu moderieren. Dafür werden die
Druckaufträge zunächst über einen speziellen PDF-Drucker (Druckerfreigabe
``PDFDrucker``) auf dem Schüler-/Lehrerrechner gedruckt und anschließend durch
den Lehrer im UMC-Modul *Drucker moderieren* betrachtet, verworfen oder für den
Druck freigegeben.

In |UCSUAS| gibt es vielfältige Möglichkeiten, die Druckmoderation zu
konfigurieren und einzusetzen. Nachfolgend wird die Einrichtung eines einzelnen
Szenarios beschrieben, welches leicht an die Bedürfnisse der eigenen
Schulumgebung angepasst werden kann. In dem beschriebenen Szenario wird der
Zugriff auf die physikalischen Drucker für alle Schüler gesperrt.

Für die Druckmoderation ist es erforderlich, dass zunächst wie in
:ref:`school-setup-cli-printers` beschrieben, Druckerfreigaben für die zu
verwendenden, physikalisch existierenden Drucker angelegt werden.

An den Druckerfreigabeobjekten im UMC-Modul *Drucker* können spezielle
Zugriffsrechte gesetzt werden. Dabei kann der Zugriff für einzelne Benutzer oder
ganze Gruppen erlaubt bzw. gesperrt werden. Um den Schülern den Zugriff auf die
physikalischen Drucker zu verbieten, muss an den Druckerfreigaben für diese
Drucker der Zugriff durch Benutzer der OU-spezifischen Gruppe
:samp:`schueler-{OU}` (z.B. ``schueler-gsmitte``) verboten werden. Für den
PDF-Drucker ``PDFDrucker`` sollten keine Einschränkungen gemacht werden.

Schüler haben damit nur noch die Möglichkeit Druckaufträge an den ``PDFDrucker``
zu senden. Im UMC-Modul *Drucker moderieren* können die Druckaufträge
anschließend durch den Lehrer aufgelistet und in Form einer PDF-Datei betrachtet
werden. Dafür ist ein geeignetes Programm zur Anzeige von PDF-Dateien auf den
Lehrerrechnern erforderlich. Die Druckaufträge können dann durch den Lehrer an
einen beliebigen physikalischen Drucker der Schule weitergeleitet oder auch
verworfen werden.

Lehrer können in dem UMC-Modul grundsätzlich nur die Druckaufträge der Schüler
oder ihre eigenen Druckaufträge betrachten. Druckaufträge von anderen Lehrern
werden von dem UMC-Modul nicht angezeigt.

Um Ausnahmen von dieser strikte Regelung zu ermöglichen, kann der Lehrer im
UMC-Modul *Computerraum* über den Punkt *Einstellungen ändern* den Druckmodus
für einen einzelnen Computerraum beeinflussen. Die oben beschriebenen
Einschränkungen für Schüler werden dabei als *Standard (globale Einstellungen)*
beschrieben. Darüber hinaus kann auch der Druckmodus *Drucken deaktiviert*
ausgewählt werden, der das Drucken von den Rechnern des Computerraums
vollständig untersagt.

.. _school-setup-generic-moderated-printer:

Anlegen eines PDF-Druckers für die Druckermoderation
----------------------------------------------------

Druckerfreigaben werden, wie in einer Standard-UCS-Installation, über das
UMC-Modul *Drucker* auf dem |UCSPRIMARYDN| angelegt. Weiterführende
Dokumentation findet sich in :ref:`print-general` in :cite:t:`ucs-manual`.

Die Drucker müssen unterhalb der OU der Schule angelegt werden. Die Auswahl
findet mit der Option *Container* beim Anlegen eines Drucker statt.
Bei der OU ``gym17`` muss beispielsweise ``gym17/printers`` ausgewählt werden.

Für die Verwendung der Druckermoderation muss ein PDF-Drucker unterhalb der OU
der Schule angelegt werden. Dies geschieht in der Regel automatisch bei der
Installation von |UCSUAS| bzw. dem Ausführen der Join-Skripte.

Sollte der PDF-Drucker für eine OU fehlen, gibt es zwei Möglichkeiten dieses für
eine OU zu erstellen:

* Auf dem Schulserver kann über das UMC-Modul *Domänenbeitritt* das Join-Skript
  *99ucs-school-umc-printermoderation* (erneut) ausgeführt werden.

* Alternativ kann das LDAP-Objekt im zuständigen Container für Druckerfreigaben
  der betreffenden OU (siehe oben) angelegt werden. Dabei müssen folgende Werte
  am Druckerfreigabe-Objekt gesetzt werden:

  Server
      Name des Schulservers

  Protokoll
      ``cups-pdf:/``

  Ziel
      leer

  Drucker-Hersteller
      ``PDF``

  Drucker-Modell
      ``Generic CUPS-PDF Printer``

.. _school-setup-generic-windows-attributes:

Windows-spezifische Benutzereinstellungen
=========================================

Neben den in :ref:`school-setup-umc-user` und
:ref:`school-setup-cli-importusers` genannten Attributen für Benutzer werden
beim Anlegen eines Benutzers auch automatisch einige Windows-spezifische
Einstellungen vorgenommen:

* Für die Verwendung von Samba ist es notwendig, dass für jeden Benutzer ein
  UNC-Pfad für das Windows-Benutzerprofil vorgegeben wird. In der
  Standardeinstellung von |UCSUAS| wird der jeweilige Logonserver als Ablageort
  für das Benutzerprofil definiert
  (``%LOGONSERVER%\%USERNAME%\windows-profiles\default``).

  Falls die Benutzerprofile statt auf dem Logonserver auf einem anderen
  Dateiserver gespeichert werden sollen, kann in der |UCSUMC| am Rechnerobjekt
  des gewünschten Dateiservers der Dienst *Windows Profile Server* gesetzt
  werden. Es wird dann ein UNC-Pfad nach dem Schema
  ``\\DATEISERVERNAME\%USERNAME%\windows-profiles\default`` am
  Benutzerobjekt gespeichert.

  .. note::

     Falls ein alternativer Dateiserver für den Benutzerprofilpfad verwendet
     werden soll, muss das entsprechende Rechnerobjekt unterhalb der Schul-OU im
     LDAP-Verzeichnisdienst liegen.

     Für den reibungslosen Betrieb darf der Dienst *Windows Profile Server* nur
     an einem Dateiserver pro OU gesetzt werden.

     Weiterhin ist der Dienst *Windows Profile Server* veraltet und wird in
     einer zukünftigen |UCSUAS|-Version entfernt bzw. durch einen äquivalenten
     Mechanismus ersetzt.

* Darüber hinaus wird auch automatisch der Pfad zum Heimatverzeichnis des
  Benutzers gesetzt. In einer Single-Server-Umgebung wird automatisch der
  |UCSPRIMARYDN| als Dateiserver eingetragen. In Multi-Server-Umgebungen ist der
  für die OU zuständige Dateiserver am Schul-OU-Objekt hinterlegt.

  Um diesen zu ändern, muss in der |UCSUMC| das OU-Objekt geöffnet werden und
  auf dem Reiter |UCSUAS_e| im Auswahlfeld *Server für
  Windows-Heimatverzeichnisse* ein geeigneter Dateiserver ausgewählt werden
  (siehe auch :ref:`school-setup-umc-schools-modify`). Der dort definierte
  Dateiserver wird beim Anlegen eines Benutzers ausgelesen und der UNC-Pfad am
  Benutzerobjekt entsprechend gesetzt (Beispiel:
  ``\\server3.example.com\benutzer123``).

.. note::

   Die Windows-spezifischen Einstellungen werden nur beim Anlegen eines
   Benutzers gesetzt und am Benutzerobjekt gespeichert.

   Ein nachträgliches Modifizieren des Benutzers über die Importskripte hat
   keinen Einfluss auf diese Einstellungen. Änderungen müssen manuell z.B. über
   das UMC-Modul *Benutzer* erfolgen.

.. _school-setup-generic-shares:

Anlegen von Freigaben
=====================

Die meisten Freigaben in einer |UCSUAS|-Umgebung werden automatisch erstellt.
Jede Klasse oder Arbeitsgemeinschaft verfügt über eine gemeinsame Freigabe.
Weiterhin existiert mit der *Marktplatz*-Freigabe je Schule eine schulweite
Freigabe. Das Erstellen der Marktplatzfreigabe beim Anlegen einer OU kann durch
das Setzen der |UCSUCRV| :envvar:`ucsschool/import/generate/marktplatz` auf den
Wert ``no`` verhindert werden.

Diese Freigaben müssen zwingend auf dem Schulserver bereitgestellt werden, um
die von |UCSUAS| bereitgestellten Funktionen nutzen zu können.

Weitere Freigaben werden, wie in einer Standard-UCS-Installation, über das
UMC-Modul *Freigaben* auf dem |UCSPRIMARYDN| angelegt. Weiterführende
Dokumentation findet sich in :ref:`shares-general` in :cite:t:`ucs-manual`.

Die Freigaben müssen unterhalb der OU der Schule angelegt werden. Die Auswahl
findet mit der Option *Container* beim Anlegen einer Freigabe statt. Für die OU
``gym17`` muss beispielsweise der Container ``gym17/shares`` ausgewählt werden.

.. versionadded:: 4.1 R2 v5

   Seit |UCSUAS| 4.1 R2 v5 werden neue Freigaben (sowohl automatisch, als auch
   manuell erstellte) standardmäßig nur noch per Samba/CIFS freigegeben. Um neue
   Freigaben standardmäßig auch per NFS zu exportieren, muss die |UCSUCRV|
   :envvar:`ucsschool/default/share/nfs` auf allen |UCSUAS|-Systemen auf den
   Wert ``yes`` gesetzt werden.

   Um den NFS-Export einer Freigabe manuell ein- oder auszuschalten, kann im
   UMC-Modul *Freigaben* für jede Freigabe die Option *Für NFS-Clients
   exportieren (NFSv3 und NFSv4)* (de)aktiviert werden.

.. _school-setup-generic-role-shares:

Lehrerzugriff auf Benutzerfreigaben
===================================

Lehrern kann der Zugriff auf alle Heimatverzeichnisse von Schülern an
einer Schule freigeschaltet werden. Dies geschieht durch Installation
des Pakets :program:`ucs-school-roleshares` auf dem
jeweiligen Schulserver. Der Zugriff kann dann über eine spezielle
Dateifreigabe erfolgen.

Das Paket installiert das Skript
:command:`/usr/share/ucs-school-import/scripts/create_roleshares`, welches über
das Join-Skript automatisch aufgerufen wird und später auch manuell aufgerufen
werden kann. Mit der Standardoption ``--create student`` aufgerufen, legt es für
alle Dateiserver des Schulstandorts jeweils eine Freigabe mit dem Namensschema
:samp:`schueler-{OU}` an. Die Freigabe erlaubt der Gruppe :samp:`lehrer-{OU}`
den administrativen Zugriff auf das Basisverzeichnis
:file:`/home/{OU}/schueler`.

Per Voreinstellung wird der Lehrergruppe Lesezugriff gewährt. Die Freigabe wird
vom jeweiligen Dateiserver nicht explizit angezeigt. Eine an einem
Windows-Arbeitsplatz angemeldete Lehrkraft sollte automatisch eine Verknüpfung
zu dieser Freigabe angezeigt bekommen.

Die Freigabe-Einstellungen dieser Freigabe können wie üblich über die |UCSUMC|
auf dem |UCSPRIMARYDN| angepasst werden, z.B. um Lehrern auch Schreibzugriff zu
gewähren.

Voraussetzung für diese Funktion ist, dass die Heimatverzeichnisse der
Benutzerkonten in entsprechend strukturierten Unterverzeichnissen angelegt
wurden. Dies geschieht in Domänen die mit |UCSUAS| 3.2 R2 oder später
installiert wurden automatisch. In älteren Umgebungen wird dies dadurch
verhindert, dass dort |UCSUCRV| :envvar:`ucsschool/import/roleshare` automatisch
auf ``no`` gesetzt wurde. Dies gewährleistet eine einheitliche Anlage der
Heimatverzeichnisse und sollte erst nach einer manuellen Migration der
Heimatverzeichnisse geändert werden.

.. _school-setup-generic-school-admins:

Anlegen von Benutzerkonten für Schuladministratoren
===================================================

Ab |UCSUAS| 4.4 v8 können Benutzerkonten für Schuladministratoren direkt über
das |UCSUAS| UMC-Modul angelegt werden. Diese Option ist standardmäßig
abgeschaltet. Um das Verhalten zu aktivieren, muss der Wert ``schoolAdmin`` aus
der |UCSUCRV| :envvar:`ucsschool/wizards/schoolwizards/users/roles/disabled`
entfernt werden. Schuladministratoren, die mit dem |UCSUAS| UMC-Modul erstellt
werden, besitzen nicht die Option *UCS@school-Lehrer* und befinden sich nicht
in der Gruppe :samp:`{lehrer-OU}`.

Benutzerkonten von Lehrern können durch eine zusätzliche Gruppenmitgliedschaft
und das Einschalten einer Option zu Schuladministratoren umgewandelt werden.

* Die zusätzliche Gruppenmitgliedschaft muss manuell über das |UCSUMC|-Modul
  *Benutzer* auf dem |UCSPRIMARYDN| hinzugefügt werden. Auf dem Reiter *Gruppen*
  muss das Benutzerkonto in die Gruppe :samp:`admins-{OU}` (für die OU *gym17*
  ist dies die Gruppe ``admins-gym17``) aufgenommen werden.

* Im |UCSUMC|-Modul *Benutzer* muss außerdem im Reiter *Optionen* die Option
  *UCS@school-Administrator* eingeschaltet werden.

.. warning::

   Es ist nicht möglich, ein Benutzerkonto einzurichten, das mit der Rolle
   *Schuladministrator* an einer Schule und mit der Rolle *Lehrer* an einer
   anderen Schule agiert.

   Ein Benutzerkonto mit der Option *UCS@school-Administrator* verfügt
   standardmäßig über einige Schuladministrator-Berechtigungen für alle Schulen,
   an denen es Mitglied ist. Das gilt auch, wenn das Benutzerkonto kein Mitglied
   der Gruppe :samp:`admins-{OU}` für die jeweilige Schule ist. Die
   Gruppenmitgliedschaft des Benutzerkontos in :samp:`admins-{OU}` fügt für die
   jeweilige Schule weitere Schuladministrator-Berechtigungen hinzu.

   Ein Benutzerkonto mit aktivierter *UCS@school-Administrator*-Option muss für
   alle Schulen, in denen das Benutzerkonto Mitglied ist, auch zu den Gruppen
   :samp:`admins-{OU}` hinzugefügt werden. Auf diese Weise finden
   Schuladministratoren an allen Schulen das gleiche, konsistente Verhalten für
   administrative Tätigkeiten im Rahmen ihrer Schuladministrator-Berechtigungen
   vor. Systemadministratoren erkennen besser, welche Benutzerkonten die
   Schuladministrator-Berechtigung haben.

Fungiert das Benutzerkonto nicht mehr als Lehrer, sondern nur noch als
Schuladministrator, so kann im Reiter *Optionen* die Option *UCS@school-Lehrer*
deaktiviert und dem Benutzer die Gruppe :samp:`lehrer-{OU}` entzogen werden.

Soll ein Schuladministrator auch als Lehrer tätig sein, muss zusätzlich die
Gruppe :samp:`lehrer-{OU}`, also z.B. ``lehrer-gym17``, hinzugefügt werden.
Abschließend müssen die Angaben für Profilpfad und Heimatverzeichnispfad am
Benutzerobjekt gesetzt werden, um das gleiche Verhalten wie bei Schüler- und
Lehrerkonten zu erhalten (siehe dazu auch
:ref:`school-setup-generic-windows-attributes`).

.. _school-setup-generic-configure-helpdesk:

Konfiguration der Helpdesk-Kontaktadresse
=========================================

Über das Helpdesk-Modul können Lehrer per E-Mail Kontakt zum Helpdesk-Team einer
Schule aufnehmen. Damit dieses Modul genutzt werden kann, muss auf dem
jeweiligen Server die |UCSUCRV| :envvar:`ucsschool/helpdesk/recipient` auf die
E-Mailadresse des zuständigen Helpdesk-Teams gesetzt werden.

.. _school-setup-generic-computerroom:

Konfiguration des Computerraum-Moduls
=====================================

Im UMC-Modul *Computerraum* kann z.B. über die Funktion *Beobachten* eine
verkleinerte Desktop-Ansicht der aufgelisteten Windows-Rechner angezeigt werden.
Dabei ist es möglich, die Desktops bestimmter Benutzergruppen von dieser Anzeige
auszuschließen. In der Standardkonfiguration ist dies die Gruppe ``Domain
Admins``.

Über die |UCSUCR|-Variable
:envvar:`ucsschool/umc/computerroom/hide_screenshots/groups` kann eine
abweichende kommaseparierte Liste mit Gruppennamen konfiguriert werden, z.B.
``Domain Admins,Helpdesk``. Da |UCSUAS| für jede Schule für die dort agierenden
Lehrer eine eigene Benutzergruppe anlegt, wurde zur Vereinfachung eine weitere
|UCSUCR|-Variable :envvar:`ucsschool/umc/computerroom/hide_screenshots/teachers`
eingeführt. Wird in dieser Variable der Wert ``yes`` hinterlegt, ist das
Betrachten der Desktop-Ansicht von Rechnern, an denen Lehrer angemeldet sind,
nicht mehr möglich.

Über die |UCSUCR|-Variable
:envvar:`ucsschool/umc/computerroom/screenshot_dimension` kann eine
gewünschte Auflösung für Screenshots zur Überwachung der einzelnen Computer im
Computerraum angegeben werden. Bei Benutzung der Standardeinstellung (nicht gesetzt)
wird die Auflösung des Zielrechners verwendet. Soll eine andere Auflösung verwendet
werden, muss die Variable gesetzt werden. Hierbei wird ein String des Formats
:code:`<Breite>x<Höhe>` erwartet.

.. caution::

   Die Anpassung der |UCSUCR|-Variable :envvar:`ucsschool/umc/computerroom/screenshot_dimension` erlaubt die Optimierung
   der Bandbreiten und CPU-Auslastung. Die Auflösung wird an die Veyon WebAPI weitergereicht, es werden aber nicht alle
   Auflösungen unterstützt. Im Falle einer nicht unterstützten Auflösung wird kein Screenshot als Antwort ausgegeben.
   Daher ist die Verwendung von Standardauflösungen empfohlen. Die geringste, funktionstüchtige Auflösung ist *240p* (320x240 Pixel).


Über die Aktion *Computer einschalten* können *WakeOnLAN*-Pakete an die
betreffenden Rechner verschickt werden, um diese einzuschalten. Ab UCS@school
4.4v4 werden diese *WakeOnLAN*-Pakete über alle Netzwerkschnittstellen des
|UCSUAS|-Systems verschickt.

Falls die Pakete auf bestimmten Netzwerkschnittstellen nicht verschickt werden
sollen, können diese Schnittstellen über die UCR-Variablen
:envvar:`ucsschool/umc/computerroom/wakeonlan/blacklisted/interfaces` und
:envvar:`ucsschool/umc/computerroom/wakeonlan/blacklisted/interface_prefixes`
festgelegt werden. Dabei sind die einzelnen Werte durch Leerzeichen zu trennen,
z.B. ``tun docker``. Wenn sich die Zielrechner in einem anderen Netzwerk
befinden, können über die UCR-Variable
:envvar:`ucsschool/umc/computerroom/wakeonlan/target_nets` die Subnetze
angepasst werden, an die Pakete gesendet werden. Dabei sind die einzelnen Werte
durch Leerzeichen zu trennen, z.B. ``255.255.255.255 10.200.18.255``.

.. versionadded:: 4.4 v4

   Ab Version 4.4 v4 prüft das Computerraum-Modul von |UCSUAS| in der
   Standardeinstellung regelmäßig, ob alle gesperrten Rechner weiterhin noch
   gesperrt sind, um z.B. Rechner nach deren Neustart wieder in den gesperrten
   Zustand zu versetzen. Das Intervall, in dem die Überprüfung läuft, kann durch
   die |UCSUCR|-Variable
   :envvar:`ucsschool/umc/computerroom/screenlock/interval` konfiguriert werden.
   In der Standardkonfiguration wird die Prüfung alle 5 Sekunden durchgeführt.
   Wird der Wert der Variable auf 0 gesetzt, wird die Prüfung abgeschaltet.

.. versionadded:: 4.4 v8

   Ab |UCSUAS| 4.4v8 werden Rechner mit mehreren IP-Adressen unterstützt. Die
   IP-Adressen des jeweiligen Rechners werden durchlaufen und die erste
   verwendet, die erreicht werden kann. Dies kann zu längeren Wartezeiten
   führen, wenn Rechner innerhalb des Computerraums ausgeschaltet sind oder eine
   Firewall den Befehl blockiert. Das Verhalten ist standardmäßig deaktiviert
   und kann durch Setzen der |UCSUCR|-Variable
   :envvar:`ucsschool/umc/computerroom/ping-client-ip-addresses` aktiviert
   werden.

.. caution::

   Ab |UCSUAS| 5.0 wird *Veyon* als Computerraum Backend eingesetzt. In den
   UMC-Modulen *Computerraum* und *Klassenarbeiten* werden fortan nur noch
   Computerräume angezeigt, deren Backend auf *Veyon* gesetzt ist.

   Für die Zeit der Migration in Multi-Server-Umgebungen können Computerräume,
   die iTALC als Backend verwenden und auf |UCSREPLICADN| betrieben werden, die
   noch |UCSUAS| 4.4v9 verwenden, weiter verwendet werden. Die Migration von
   iTALC auf *Veyon* in diesen Mischumgebungen erfolgt im UMC-Modul *Computerräume
   verwalten* auf dem entsprechenden |UCSREPLICADN| (und nicht auf dem
   |UCSPRIMARYDN|). Die Schritte der Migration von iTALC zu *Veyon* sind in
   :uv:help:`Migration of the computer room backend iTALC to Veyon <16937>`
   beschrieben.

.. _school-setup-generic-configure-class-lists:

Konfiguration des Klassenlisten-Moduls
======================================

Über das UMC-Modul *Klassenlisten* können Listen mit Schülerdaten
einer ausgewählten Klasse exportiert werden. In der Standardkonfiguration werden
die UDM Attribute ``firstname``, ``lastname`` und ``username`` sowie die
ausgewählte Klasse angezeigt.

Mit der |UCSUCRV| :envvar:`ucsschool/umc/lists/class/attributes` können die
angezeigten Attribute angepasst werden. Die Variable beschreibt eine Zuordnung
der anzuzeigenden UDM Attribute zu den angezeigten Spaltennamen. Dabei sind die
Zuordnung durch Kommata zu trennen, z.B. ``firstname Vorname,lastname
Nachname,Class Klasse,username Username``. Für ``Class`` wird dabei die
ausgewählte Klasse eingesetzt.

.. _school-setup-generic-configure-workgroup-emails:

Konfiguration von Email-Adressen für Arbeitsgruppen
===================================================

.. versionadded:: 4.4v7

   Ab |UCSUAS| 4.4v7 ist es möglich die Aktivierung von E-Mailadressen für
   Arbeitsgruppen über das Modul *Arbeitsgruppen verwalten* zu
   erlauben.

Um dieses Feature zu aktivieren, muss die |UCSUCRV|
:envvar:`ucsschool/workgroups/mailaddress` gesetzt werden. Der eingetragene
Wert bestimmt das Muster, nach dem die E-Mailadresse einer Arbeitsgruppe
berechnet wird.

Es stehen folgende Platzhalter-Werte zur Verfügung:

* ``{ou}``

* ``{name}``

Ist der Wert der |UCSUCRV| beispielsweise
``{ou}-{name}@schule-univention.de``, so wird für eine Arbeitsgruppe mit dem
Namen ``AG1`` an der Schule ``DEMOSCHOOL`` die E-Mailadresse
``DEMOSCHOOL-AG1@schule-univention.de`` berechnet.

.. _school-setup-generic-apple-school-manager:

Provisionierung von Benutzern zu Apple School Manager
=====================================================

Die Apple School Manager Connector App für |UCSUAS| synchronisiert automatisch
Benutzer zu Apple School Manager (ASM). Das |UCSUAS| Identity Management
übernimmt die Rolle des Studierendeninformationssystems und verwendet die
SFTP-Schnittstelle, wie sie von Apple bereit gestellt wird.
