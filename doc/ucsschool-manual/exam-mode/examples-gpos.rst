.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-exam-gpo:

Beispiele für Gruppenrichtlinien
================================

Gruppenrichtlinien werden von einem Windows System aus mit Hilfe der
Gruppenrichtlinienverwaltung (GPMC) angelegt und bearbeitet. Im Folgenden ist
die Konfiguration der Gruppenrichtlinien von einem Windows 7 System aus
beschrieben auf dem dazu die Gruppenrichtlinienverwaltung (GPMC) aus den *Remote
System Administration Tools (RSAT)* installiert sein muss.

Alle Gruppenrichtlinieneinstellungen können je nach Bedarf gesammelt über ein
Gruppenrichtlinienobjekt vorgenommen oder auf separate Objekte verteilt
werden. Um den Bezug zwischen einem ausgewählten Gruppenrichtlinienobjekt und
Objekten im Samba-Verzeichnisdienst herzustellen, kann es mit einer
Organisationseinheit (OU) verknüpft werden, z.B. der Schul-OU. Einige der hier
beispielhaft beschriebenen Gruppenrichtlinieneinstellungen wirken sich nur auf
Benutzer- und andere nur auf Computerkonten aus.

Da die Einstellungen eines Gruppenrichtlinienobjekts nur für Objekte ausgewertet
werden, die unterhalb des speziellen Verzeichniszweigs liegen, mit dem es
verknüpft wurde, ist es wichtig, dass das entsprechende Gruppenrichtlinienobjekt
hinreichend hoch in der hierarchischen Objektordnung verknüpft wird.

Einige der genannten Gruppenrichtlinien-Einstellungen beziehen sich auf den
Bereich der Computerkonfiguration und werden nur beim Systemstart korrekt von
den entsprechenden Windows-Komponenten ausgewertet. Für solche Einstellungen ist
daher ein Neustart der Windows-Arbeitsplatzsysteme nach Aktivierung des
Klassenarbeitsmodus notwendig.

.. note::

   Zu diesem Thema ist auch ein Hinweis von Microsoft zu Windows XP
   Systemen zu beachten:

      Jede Version von Windows XP Professional stellt eine Funktion zur
      Optimierung für schnelles Anmelden zur Verfügung.

      Computer mit diesen Betriebssystemen warten standardmäßig beim Starten
      nicht auf den Start des Netzwerks. Nach der Anmeldung werden die
      Richtlinien im Hintergrund verarbeitet, sobald das Netzwerk zur Verfügung
      steht.

      Dies bedeutet, dass der Computer bei der Anmeldung und beim Start
      weiterhin die älteren Richtlinieneinstellungen verwendet. Daher sind für
      Einstellungen, die nur beim Start oder bei der Anmeldung angewendet werden
      können (z. B. Softwareinstallation und Ordnerumleitung), möglicherweise
      nach dem Ausführen der ersten Änderung am Gruppenrichtlinienobjekt mehrere
      Anmeldungen durch den Benutzer erforderlich.

      Diese Richtlinie wird gesteuert durch die Einstellung in
      :file:`Computerkonfiguration\\Administrative
      Vorlagen\\System\\Anmeldung\\Beim Neustart des Computers und bei der
      Anmeldung immer auf das Netzwerk warten`.

      Diese Funktion ist in
      den Betriebssystemversionen von Windows 2000 oder Windows Server 2003
      nicht verfügbar.”

      — Quelle: :cite:t:`ms-technet-gpo-processing`

.. _school-exam-gpo-general:

Generelle Hinweise zu Gruppenrichtlinien und Administrativen Vorlagen
---------------------------------------------------------------------

Auf dem Schulserver sollte das Verzeichnis
:file:`/var/lib/samba/sysvol/{DomänenNameDerUCS@schoolUmgebung}/Policies/PolicyDefinitions/`
angelegt werden. Sobald dieses Verzeichnis angelegt ist, bevorzugt das
Windows-Programm zur Gruppenrichtlinienverwaltung die dort hinterlegten
Administrativen Vorlagen im ADMX-Format vor den lokal auf dem Windows 7 System
installierten Administrativen Vorlagen.

Da in den nachfolgenden Abschnitten zusätzliche Administrative Vorlagen
verwendet werden, die ebenfalls in dem oben genannten Verzeichnis abzulegen
sind, wird empfohlen, nach dem Erstellen des Verzeichnisses einmalig die lokal
installierten Administrativen Vorlagen aus dem Verzeichnis
:file:`C:\\Windows\\PolicyDefinitions` in das neue Verzeichnis zu kopieren. Da
das Verzeichnis serverseitig unterhalb der :file:`SYSVOL`-Freigabe liegt, wird
es per Voreinstellung auf alle Samba 4 Server der Domäne synchronisiert.

Die Administrativen Vorlagen sind an sich keine Gruppenrichtlinien, sie dienen
nur zur Erweiterung der Einstellungsmöglichkeiten die das Windows Programm zur
Gruppenrichtlinienverwaltung dem Administrator zur Auswahl anbietet. Für neuere
Windows-Versionen, wie z.B. Windows 8, stellt Microsoft aktualisierte
Administrative Vorlagen zum Download zur Verfügung.

Grundsätzlich können Gruppenrichtlinien im Samba Verzeichnisdienst mit
Organisationseinheiten (OU) und der LDAP-Basis verknüpft werden. Im
|UCSUAS|-Kontext werden jedoch nur Verknüpfungen unterhalb der Schul-OU
auch automatisch in das OpenLDAP-Verzeichnis synchronisiert.
Verknüpfungen mit der LDAP-Basis werden z.B. durch
OpenLDAP-Zugriffsbeschränkungen blockiert, damit sich eine Anpassung der
damit verknüpften Gruppenrichtlinien durch einen Schul-Administrator
nicht auch auf alle anderen Schulen auswirkt.

Eine solche Änderung wird im S4 Connector auf der Schule als *Reject* notiert.
Wenn tatsächlich gewünscht ist, eine Änderung der Gruppenrichtlinienverknüpfung
an der LDAP-Basis und unter ``OU=Domain Controllers`` auch in das
OpenLDAP-Verzeichnis und damit an alle Schulen zu synchronisieren, kann auf dem
Schulserver folgender Befehl mit dem zentralen Administrator-Passwort ausgeführt
werden:

.. code-block:: console

   $ eval "$(ucr shell)"
   $ /usr/share/univention-s4-connector/msgpo.py \
     --write2ucs \
     --binddn "uid=Administrator,cn=users,$ldap_base" \
     --bindpwd <password>

Der S4 Connector erkennt eine kurze Zeit später bei dem nächsten *Resync*, dass
der *Reject* aufgelöst wurde.

.. _school-exam-gpo-group:

Windows-Anmeldung im Prüfungsraum auf Mitglieder der Klassenarbeitsgruppe beschränken
-------------------------------------------------------------------------------------

.. versionadded:: 4.4v4

   Mit |UCSUAS| 4.4v4 werden die Windows-Anmeldungen während einer Klassenarbeit
   automatisch von |UCSUAS| verwaltet.

Dabei werden über das Nutzerattribut :envvar:`sambaUserWorkstations` alle
Schülerkonten der Klassenarbeitsgruppe auf die Rechner des Computerraumes
beschränkt. Zusätzlich wird verhindert, dass sich der originale Nutzer an einem
Windowsrechner anmelden kann. Dieser Mechanismus kommt ohne die hier
beschriebene Einrichtung von Windows Gruppenrichtlinien aus und erfordert daher
keinen Neustart der Rechner.

Sollten keine weiteren Gruppenrichtlinien eingerichtet worden sein, müssen die
Rechner vor oder nach einer Klassenarbeit überhaupt nicht mehr neugestartet
werden. In diesem Fall kann die Aufforderung der Lehrer zum Neustart der Rechner
während der Einrichtung von Klassenarbeiten über die |UCSUCRV|
:envvar:`ucsschool/exam/default/show/restart` abgeschaltet werden.

Da das im folgenden konfigurierte Gruppenrichtlinienobjekt je nach Verknüpfung
im Samba-Verzeichnisdienst die Anmeldung an betroffenen
Windows-Arbeitsplatzsystemen einschränkt, wird dringend empfohlen, als erstes
die Anwendung der neuen Gruppenrichtlinie auf solche Windows-Arbeitsplatzsysteme
einzuschränken, auf die sie sich später im Klassenarbeitsmodus auswirken soll.
Dies geschieht am einfachsten über die Anpassung der Sicherheitsfilterung, die
im Folgenden beschrieben ist.

Damit die Gruppenrichtlinieneinstellungen von Windows-Arbeitsplatzrechnern
ausgewertet werden, ist es notwendig, einen Bezug zwischen dem angelegten
Gruppenrichtlinienobjekt und den Rechnerobjekten im Samba-Verzeichnisdienst
herzustellen. Um dies zu erreichen, kann das Gruppenrichtlinienobjekt mit einer
Organisationseinheit (OU) verknüpft werden, die den Rechnerobjekten im
Verzeichnisbaum übergeordnet ist, in der Regel mit der Schul-OU.

.. _school-exam-gpo-computer:

Anwendungsbereich der GPO auf Klassenarbeitscomputer einschränken
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. In der Baumdarstellung der Gruppenrichtlinienverwaltung die Gruppenrichtlinie
   anklicken.

#. Auf dem geöffneten Reiter *Bereich* im Abschnitt *Sicherheitsfilterung* die
   Schaltfläche :guilabel:`Hinzufügen` betätigen.

#. In das Eingabefeld *Geben Sie die zu verwendenden Objektnamen ein* den Namen
   der Klassenarbeitsgruppe (:samp:`OU{NameDerOU}-Klassenarbeit`, z.B.
   ``OUgym17-Klassenarbeit``) eintragen und den Dialog mit :guilabel:`OK`
   schließen.

#. Auf dem geöffneten Reiter *Bereich* im Abschnitt *Sicherheitsfilterung* die
   Gruppe ``Authenticated Users`` auswählen und die Schaltfläche
   :guilabel:`Entfernen` betätigen.

.. _school-exam-gpo-user:

Einschränkung der Windows-Anmeldung auf Klassenarbeitsbenutzerkonten und Lehrer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. In der Gruppenrichtlinienverwaltung das Gruppenrichtlinienobjekt zur
   Bearbeitung öffnen (Kontextmenü des GPO in der Baumdarstellung).

#. Im neu geöffneten Gruppenrichtlinienverwaltungseditor den folgenden Zweig
   öffnen: :menuselection:`Computerkonfiguration --> Richtlinien -->
   Windows-Einstellungen --> Sicherheitseinstellungen --> Lokale Richtlinien -->
   Zuweisen von Benutzerrechten`

#. Im neu geöffneten Richtlinien-Dialog *Eigenschaften von Lokal anmelden
   zulassen* auf dem Reiter *Sicherheitsrichtlinie* die Option *Diese
   Richtlinieneinstellung definieren* aktivieren.

#. Dann die Schaltfläche :guilabel:`Benutzer oder Gruppe hinzufügen` betätigen.

#. In das Eingabefeld *Benutzer und Gruppennamen* den Namen ``Administratoren``
   eintragen und den Dialog mit :guilabel:`OK` schließen.

#. Erneut die Schaltfläche :guilabel:`Benutzer oder Gruppe hinzufügen` betätigen.

#. Im neu geöffneten Dialog die Schaltfläche :guilabel:`Durchsuchen` betätigen.

#. In das Eingabefeld *Geben Sie die zu verwendenden Objektnamen ein* den Namen
   der Klassenarbeitsgruppe (:samp:`OU{NameDerOU}-Klassenarbeit`, z.B.
   ``OUgym17-Klassenarbeit``) eintragen und den Dialog mit :guilabel:`OK`
   schließen.

#. Den Dialog *Benutzer oder Gruppe hinzufügen* ebenfalls mit :guilabel:`OK`
   schließen.

#. Erneut die Schaltfläche :guilabel:`Benutzer oder Gruppe hinzufügen`
   betätigen.

#. Im neu geöffneten Dialog die Schaltfläche :guilabel:`Durchsuchen` betätigen.

#. In das Eingabefeld *Geben Sie die zu verwendenden Objektnamen ein* den Namen
   der Lehrergruppe (:samp:`lehrer-{NameDerOU}`, z.B. ``lehrer-gym17``)
   eintragen und den Dialog mit :guilabel:`OK` schließen.

#. Den Dialog *Benutzer oder Gruppe hinzufügen* ebenfalls mit :guilabel:`OK`
   schließen.

#. Den Richtlinien-Dialog *Eigenschaften von Lokal anmelden zulassen* mit
   :guilabel:`OK` schließen.

.. _school-exam-gpo-usb:

Zugriff auf USB-Speicher und Wechselmedien einschränken
-------------------------------------------------------

Zur Einschränkung des Zugriffs auf USB-Speicher und Wechselmedien sind je nach
Windowsversion zwei Fälle zu beachten:

* Die Einschränkung der Benutzung bereits installierter Gerätetreiber

* Die Einschränkung der Installation neuer Gerätetreiber

Während für Windows XP beide Einschränkungen notwendig sind, bietet Windows 7
durch erweiterte Richtlinien vereinfachte und erweiterte Kontrollmöglichkeiten.
In Mischumgebungen ist eine Kombination der skizzierten Einstellungen zu
empfehlen.

.. note::

   Die Liste der hier erwähnten Einstellungen erhebt nicht den Anspruch auf
   Vollständigkeit. Es ist notwendig die Einstellungen entsprechend der lokalen
   Gegebenheiten zu testen. Insbesondere sollte folgende Microsoft-Dokumentation
   beachtet werden: :cite:t:`ms-technet-ext-storage`.

.. _school-exam-gpo-usb-xp:

Zugriff auf USB-Speicher an Windows XP einschränken
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Diese Richtlinie wird über eine Administrative Vorlage (ADMX) definiert, die in
:cite:t:`ms-kb-555324` beschrieben ist. Erst nach Einbinden der Administrative
Vorlage (ADMX) können folgende Einstellungen getroffen werden. Beispiele für
ADMX-Dateien liegen unter
:file:`/usr/share/doc/ucs-school-umc-exam/examples/GPO`. Zum Einbinden der
ADMX-Dateien müssen diese auf die :file:`SYSVOL`-Freigabe kopiert werden (siehe
:ref:`school-exam-gpo-general`).

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Computerkonfiguration --> Richtlinien --> Administrative
   Vorlagen --> Spezielle Einstellungen --> Treiber einschränken`

#. Richtlinie *USB Sperren* öffnen, *Aktiviert* auswählen und mit :guilabel:`OK`
   bestätigen.

.. note::

   Hier stehen auch weitere Gerätetypen zur Auswahl, z.B. CD-ROM-Laufwerke.

.. _school-exam-gpo-usb-xp-drivers:

Installation neuer Gerätetreiber für USB-Speicher an Windows XP verbieten
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Diese Richtlinie definiert eingeschränkte Dateisystemberechtigungen gemäß
:cite:t:`ms-kb-823732`.

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Computerkonfiguration --> Richtlinien --> Windows-Einstellungen -->
   Sicherheitseinstellungen --> Dateisystem`

#. Rechtsklick auf :guilabel:`Datei hinzufügen...`

#. Das Verzeichnis :file:`C:\\Windows\\Inf`
   ansteuern und dort die Datei :file:`usbstor.inf` auswählen und mit
   :guilabel:`OK`
   bestätigen.

   .. note::

      Gegebenenfalls wird die Dateiendung :file:`.inf` nicht mit angezeigt.

#. In dem neu geöffneten Dialog *Datenbanksicherheit für ...* in der oberen
   Liste *Gruppen- oder Benutzernamen* die Schaltfläche :guilabel:`Hinzufügen`
   betätigen und den Namen der Klassenarbeitsgruppe hinzufügen,

#. In der darunter angezeigten Liste *Berechtigungen für ...* in der
   Zeile *Vollzugriff*, Spalte *Verweigern* ein Häkchen setzen und
   mit :guilabel:`OK` bestätigen.

#. Den Dialog *Datenbanksicherheit für ...* mit :guilabel:`OK` schließen.

#. Das neue Dialogfenster *Windows-Sicherheit* mit :guilabel:`Ja` bestätigen.

#. Das neue Dialogfenster *Objekt hinzufügen* mit :guilabel:`OK` schließen.

Analog sollten Einstellungen für :file:`%SystemRoot%\inf\usbstor.pnf` und
:file:`%SystemRoot%\system32\drivers\usbstor.sys` definiert werden.

.. _school-exam-gpo-usb-w7:

Zugriff auf USB-Speicher an Windows 7 einschränken
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Benutzerkonfiguration --> Richtlinien --> Administrative
   Vorlagen --> System --> Wechselmedienzugriff`

#. Z.B. Richtlinie *Wechseldatenträger: Lesezugriff verweigern*
   öffnen, *Aktiviert* auswählen und mit :guilabel:`OK` bestätigen.

.. note::

   Weitere Informationen zu diesem Thema liefert z.B.
   :cite:t:`ms-technet-removable-devices`.

.. _school-exam-gpo-usb-w7-drivers:

Installation neuer Gerätetreiber für USB-Speicher an Windows 7 Clients verbieten
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Zusätzliche Einschränkungen zur Installation von Gerätetreibern sind auch unter
Windows 7 möglich. Die Einstellungsmöglichkeiten bieten eine größere Kontrolle,
setzen aber auch konkrete Erfahrungen mit den im Einzelfall eingesetzten Geräten
voraus. Daher ist dieser Abschnitt nur als Einstiegshilfe zu verstehen. Die
folgende Einstellung würde die zusätzliche Installation jeglicher Treiber für
Wechselgeräte deaktivieren. Es kann hier z.B. dann zusätzlich sinnvoll sein,
Administratoren von dieser Einschränkung auszunehmen.

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Computerkonfiguration --> Richtlinien --> Administrative
   Vorlagen --> System --> Geräteinstallation --> Einschränkungen bei der
   Geräteinstallation`

#. Hier kann die Installation von Treibern für bestimmte Geräteklassen,
   Geräte-IDs oder alle Wechselgeräte eingeschränkt werden.

#. Richtlinie *Installation von Wechselgeräten verhindern* öffnen,
   *Aktiviert* auswählen und mit :guilabel:`OK` bestätigen.

Die Richtlinie *Administratoren das Außerkraftsetzen der Richtlinien unter ...
erlauben* erlaubt Mitgliedern der Administratorengruppe die getroffenen
Einschränkungen zu umgehen.

Noch stärkere Restriktionen sind möglich, indem man die Ausschlusslogik auf
Whitelisting umstellt. Dies kann über die Richtlinie *Installation von Geräten
verhindern, die nicht in anderen Richtlinien beschrieben sind* erreicht werden.

.. note::

   Weitere Informationen zu diesem Thema liefert z.B.
   :cite:t:`ms-technet-driver-install-control-gpo`.

.. _school-exam-gpo-proxy:

Vorgabe von Proxy-Einstellungen für den Internetzugriff
-------------------------------------------------------

Im Folgenden sind Vorgaben für Internet Explorer, Google Chrome und Mozilla
Firefox beschrieben. Während Microsoft selbst Administrative Vorlagen
mitliefert, sind für Google Chrome und Mozilla Firefox jeweils eigene
Administrative Vorlagen notwendig.

Zusätzlich zur Vorgabe einer Proxyeinstellung ist für den Klassenarbeitsmodus
eine Sperrung des Benutzerzugriffs auf eben diese Einstellungen sinnvoll. Dazu
gibt es zwei unterschiedliche Ansätze:

#. Im Fall des Internet Explorers bietet die Administrative Vorlage die
   Möglichkeit, das entsprechende Einstellungsfenster zu sperren.

#. Im Fall von Google Chrome und Mozilla Firefox werden hingegen die
   Proxy-Einstellungen per Gruppenrichtlinie für den Arbeitsplatzrechner
   vorgegeben, statt für den Benutzer, und sind dadurch z.B. für Schüler nicht
   mehr veränderbar. Für diese Browser ist es daher wichtig darauf zu achten,
   die Einstellungen, wo nötig, im Zweig *Computerkonfiguration* des
   Gruppenrichtlinieneditors statt im Zweig *Benutzerkonfiguration* vorzunehmen.

.. _school-exam-gpo-proxy-ie:

Proxy-Vorgabe für den Internet Explorer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Benutzerkonfiguration --> Richtlinien -->
   Windows-Einstellungen --> Internet Explorer-Wartung --> Verbindung`

#. Richtlinie *Proxyeinstellungen* öffnen, *Aktiviert* auswählen und bestätigen.

#. Proxyadresse für *HTTP* sowie *Secure* und das entsprechende *Port*-Feld
   ausfüllen (Wert der |UCSUCRV| :envvar:`squid/httpport`, Standardwert:
   ``3128``).

#. Ggf. *Für alle Adressen denselben Proxyserver verwenden* aktivieren.

.. _school-exam-gpo-proxy-ie-lock:

Sperrung der Proxyeinstellung für den Internet Explorer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Computerkonfiguration --> Richtlinien --> Administrative
   Vorlagen: Vom zentralen Computer abgerufene Richtliniendefinitionen
   (ADMX-Dateien) --> Windows-Komponenten --> Internet Explorer -->
   Internetsystemsteuerung`

#. Richtlinie *Verbindungsseite deaktivieren* öffnen und *Aktiviert* auswählen
   und bestätigen.

.. _school-exam-gpo-proxy-chrome:

Proxy-Vorgabe für Google Chrome
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Die Administrativen Vorlagen für Google Chrome werden durch das Zip-Archiv
:file:`policy_templates.zip` des Chromium-Projekts bereitgestellt. Die
entsprechenden Dateien liegen unter
:file:`/usr/share/doc/ucs-school-umc-exam/examples/GPO/`. Der Inhalt des
:file:`admx` Verzeichnisses sollte in das Verzeichnis :file:`PolicyDefinitions`
auf den Schulserver kopiert werden, so dass dort die Datei :file:`chrome.admx`
liegt. Die :file:`*.adml` Dateien aus den Unterverzeichnissen müssen in
gleichnamige Unterverzeichnisse unter :file:`PolicyDefinitions` kopiert werden.

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Computerkonfiguration --> Richtlinien --> Administrative
   Vorlagen: Vom zentralen Computer abgerufene Richtliniendefinitionen
   (ADMX-Dateien) --> Google --> Google Chrome --> Proxy-Server`

#. Richtlinie *Auswählen, wie Proxy-Server-Einstellungen angegeben werden*
   öffnen und *Aktiviert* auswählen.

#. Im Dropdown *System-Proxy-Einstellungen verwenden* auswählen und bestätigen.

.. _school-exam-gpo-proxy-firefox:

Proxy-Vorgabe für Mozilla Firefox
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Auf dem Schulserver sollte das Verzeichnis
:file:`/var/lib/samba/sysvol/DomänenNameDerUCS@schoolUmgebung/Policies/PolicyDefinitions/`
angelegt werden. Nähere Informationen sind im Abschnitt zu Google Chrome zu
finden.

Die Administrativen Vorlagen für Mozilla Firefox werden durch das
FirefoxADM-Projekt bereitgestellt. Es ist sinnvoll, die dort definierten
ADM-Vorlagen in das ADMX-Format umzuwandeln.

Beispiele für ADMX Dateien liegen unter
:file:`/usr/share/doc/ucs-school-umc-exam/examples/GPO`. Der Inhalt des
:file:`admx` Verzeichnisses sollte in das Verzeichnis :file:`PolicyDefinitions`
auf den Schulserver kopiert werden, so dass dort die Datei
:file:`firefoxlock.admx` liegt. Die :file:`*.adml` Dateien aus den
Unterverzeichnissen müssen in gleichnamige Unterverzeichnisse unter
:file:`PolicyDefinitions` kopiert werden.

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Computerkonfiguration --> Richtlinien --> Administrative Vorlagen: Vom
   zentralen Computer abgerufene Richtliniendefinitionen (ADMX-Dateien)
   --> Mozilla Firefox Locked Settings --> General`

#. Richtlinie *Proxy Settings* öffnen und *Aktiviert* auswählen.

#. Im Dropdown *Preference State* die Einstellung *Locked* auswählen.

#. Im Dropdown *Proxy Setting* die Einstellung *Manual Proxy Configuration*
   auswählen.

#. Im Feld *Proxy Setting* die Einstellung *Manual Setting - HTTP Proxy*
   eintragen.

#. Im Feld *HTTP Proxy Port* den Proxy Port eintragen (Wert der |UCSUCRV|
   :envvar:`squid/httpport`, Standardwert: ``3128``).

#. Den Dialog mit :guilabel:`OK` bestätigen.

Da Mozilla Firefox bisher nicht selbständig die über die Administrativen
Vorlagen definierten Einstellungen in der Windows-Registry berücksichtigt, ist
es notwendig diese Einstellungen über ein Startup- bzw. Shutdown-Skript in
Mozilla-Konfigurationsdateien übersetzen zu lassen. Das FirefoxADM-Projekt
stellt diese Skripte in Form von zwei :file:`*.vbs` Dateien zur Verfügung. Deren
Einbindung ist über die folgenden Schritt möglich.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Computerkonfiguration --> Windows-Einstellungen --> Skripts
   (Start/Herunterfahren)`

#. Richtlinie *Starten* öffnen.

#. Im Dialog *Eigenschaften von Starten* auf dem Reiter *Skripts* die
   Schaltfläche *Dateien anzeigen* betätigen.

#. In das vom automatisch geöffneten Windows Explorer angezeigte (leere)
   Verzeichnis (:file:`Machine\Scripts\Startup` im betreffenden GPO-Verzeichnis)
   die Datei :file:`firefox_startup.vbs` kopieren und das Explorer-Fenster
   schließen.

#. Im Dialog *Eigenschaften von Starten* die Schaltfläche :guilabel:`Hinzufügen`
   betätigen.

#. Im neu geöffneten Dialog *Hinzufügen eines Skripts* neben dem Feld
   *Skriptname* den Namen :file:`firefox_startup.vbs` eintragen und Dialog mit
   :guilabel:`OK` bestätigen.

#. Im Dialog *Eigenschaften von Starten* den Dialog mit :guilabel:`OK`
   bestätigen.

#. Richtlinie *Herunterfahren* öffnen, und dort analog zu dem Vorgehen bei
   *Starten* das Skript :file:`firefox_shutdown.vbs` eintragen. Im Detail also:

   #. Im Dialog *Eigenschaften von Herunterfahren* die Schaltfläche
      :guilabel:`Hinzufügen` betätigen,

   #. In das vom automatisch geöffneten Windows Explorer angezeigte (leere)
      Verzeichnis (:file:`Machine\Scripts\Shutdown` im betreffenden
      GPO-Verzeichis) die Datei :file:`firefox_shutdown.vbs` kopieren und das
      Explorer-Fenster schließen.

   #. Im neu geöffneten Dialog *Hinzufügen eines Skripts* neben dem
      Feld *Skriptname* den Namen :file:`firefox_shutdown.vbs`
      eintragen und Dialog mit :guilabel:`OK` bestätigen.

#. Im Dialog *Eigenschaften von Herunterfahren* den Dialog mit :guilabel:`OK`
   bestätigen.

.. _school-exam-gpo-cmd:

Zugriff auf bestimmte Programme einschränken
--------------------------------------------

.. note::

   Die Liste der hier erwähnten Einstellungen erhebt nicht den Anspruch der
   Vollständigkeit. Es ist notwendig die Einstellungen entsprechend der lokalen
   Gegebenheiten zu testen. Insbesondere sollten folgende
   Microsoft-Dokumentationen beachtet werden:

   * :cite:t:`ms-technet-srp-protect-unauthorized`

   * :cite:t:`ms-technet-software-restriction-policies`.

.. _school-exam-gpo-cmd-cli:

Kommandoeingabeaufforderung deaktivieren
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Benutzerkonfiguration --> Richtlinien --> Administrative
   Vorlagen --> System`

#. Richtlinie *Zugriff auf Eingabeaufforderung verhindern* öffnen und
   *Aktiviert* auswählen und bestätigen.

.. _school-exam-gpo-cmd-regedit:

Zugriff auf Windows-Registry-Editor deaktivieren
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Benutzerkonfiguration --> Richtlinien --> Administrative
   Vorlagen --> System`

#. Richtlinie *Zugriff auf Programme zum Bearbeiten der Registrierung
   verhindern* öffnen

#. *Aktiviert* auswählen und den Dialog mit :guilabel:`OK` bestätigen.

.. _school-exam-gpo-cmd-srp:

Konfiguration von *Software Restriction Policies* (SRP)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aufgrund der Tiefe des Eingriffs der *Software Restriction Policies* ist zu
empfehlen, diese zunächst in einer Testumgebung zu auszuprobieren. Bei der
Analyse von Zugriffsfehlern kann die Ereignisanzeige des Windows-Clients helfen.

Die *Software Restriction Policies* greifen auch in die Bearbeitung von Login-
und Logoff-Skripten ein. Alle dort verwendeten Programme bzw. Programmpfade
sollten auf Ausführbarkeit getestet werden.

.. note::

   Die Liste der hier erwähnten Einstellungen erhebt nicht den Anspruch der
   Vollständigkeit. Es ist notwendig die Einstellungen entsprechend der lokalen
   Gegebenheiten zu testen. Insbesondere sollte folgende Microsoft-Dokumentation
   beachtet werden:

   * :cite:t:`ms-technet-srp-protect-unauthorized`.

   * :cite:t:`ms-technet-software-restriction-policies`.

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Benutzerkonfiguration --> Windows-Einstellungen -->
   Sicherheitseinstellungen --> Richtlinien für Softwareeinschränkung`

#. Rechtsklick auf *Neue Richtlinien für Softwareeinschränkung erstellen*.

#. Im rechten Fensterteil *Erzwingen* öffnen.

#. Einstellung *Alle Benutzer außer den lokalen Administratoren* auswählen und
   mit :guilabel:`OK` bestätigen.

#. Im rechten Fensterteil *Sicherheitsstufen* öffnen.

#. *Nicht erlaubt* per Doppelklick öffnen.

#. *Als Standard* auswählen und mit :guilabel:`OK` bestätigen.

#. Im rechten Fensterteil *Zusätzliche Regeln* öffnen.

#. Rechtsklick auf *Neue Pfadregel...*.

#. In das Eingabefeld *Pfad* den UNC-Pfad ``\\%USERDNSDOMAIN%\SysVol`` eingeben,
   damit Logon- und GPO-Skripte ausgeführt werden können.

#. In der Dropdown-Liste *Nicht eingeschränkt* auswählen und mit :guilabel:`OK`
   bestätigen.

   .. list-table:: Beispiele für weitere Pfadregeln
      :header-rows: 1
      :widths: 8 4

      * - Pfad
        - Sicherheitsstufe

      * - ``\\%USERDNSDOMAIN%\SysVol``
        - Nicht eingeschränkt

      * - ``\\%LogonServer%\SysVol``
        - Nicht eingeschränkt

      * - ``\\%LogonServer%\netlogon``
        - Nicht eingeschränkt

      * - ``\\%COMPUTERNAME%\Templates$\*``
        - Nicht eingeschränkt

      * - ``%UserProfile%\LocalSettings\Temp\*.tmp``
        - Nicht eingeschränkt

      * - ``%WinDir%\system32\cscript.exe``
        - Nicht eingeschränkt

      * - ``%WinDir%\system32\wscript.exe``
        - Nicht eingeschränkt

      * - ``%ProgramFiles%``
        - Nicht eingeschränkt

      * - ``%ProgramFiles(x86)%``
        - Nicht eingeschränkt

      * - ``*.lnk``
        - Nicht eingeschränkt

#. Es kann sinnvoll sein zusätzlich Programm-Pfade als *Nicht erlaubt*
   einzustufen, z.B.:

   .. list-table:: Beispiele für weitere Pfadregeln
      :header-rows: 1
      :widths: 8 4

      * - Pfad
        - Sicherheitsstufe

      * - ``%UserProfile%\LocalSettings\Temp``
        - Nicht erlaubt

      * - ``%SystemRoot%\temp\*``
        - Nicht erlaubt

      * - ``%SystemRoot%\System32\mstsc.exe``
        - Nicht erlaubt

      * - ``%SystemRoot%\System32\dllcache\*``
        - Nicht erlaubt

      * - ``%SystemRoot%\System32\command.com``
        - Nicht erlaubt

      * - ``%SystemRoot%\System32\cmd.exe``
        - Nicht erlaubt

      * - ``%SystemRoot%\repair\*``
        - Nicht erlaubt

      * - ``%SystemDrive%\temp\*``
        - Nicht erlaubt

#. Es sollte beachtet werden, dass schreibbare Verzeichnisse, auf die der
   Zugriff nicht per Software Restriction Policy eingeschränkt ist, Benutzern
   die Möglichkeit geben, Programmdateien dort abzulegen und so die definierten
   Regeln zu umgehen.


.. _school-exam-gpo-profiles:

Verwendung temporärer Benutzerprofil-Kopien
-------------------------------------------

Bei der Verwendung von |UCSUAS| werden serverseitige Profile verwendet, die bei
der Anmeldung eines Benutzers auf den jeweiligen Windows-Rechner kopiert werden.

In der Standardeinstellung von Windows wird bei der Abmeldung des Benutzers das
Profil nicht gelöscht und eine lokale Kopie vorgehalten. Gerade in Verbindung
mit dem Klassenarbeitsmodus führt dies zu einer unnötigen Auslastung der lokalen
Festplatte.

Über eine Richtlinie kann Windows angewiesen werden, die lokale Profil-Kopie
nach der Abmeldung des Benutzers wieder zu verwerfen.

#. In der Gruppenrichtlinienverwaltung ein neues Gruppenrichtlinienobjekt
   anlegen und/oder ein existierendes Gruppenrichtlinienobjekt zur Bearbeitung
   öffnen.

#. Im Gruppenrichtlinienverwaltungseditor den folgenden Zweig öffnen:
   :menuselection:`Computerkonfiguration --> Richtlinien --> Administrative
   Vorlagen --> System --> Benutzerprofile`

#. Richtlinie *Zwischengespeicherte Kopien von servergespeicherten Profilen
   löschen* öffnen und *Aktiviert* auswählen und bestätigen.
