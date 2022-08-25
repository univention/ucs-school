.. _structure:

******************************
Aufbau einer |UCSUAS|-Umgebung
******************************

|UCSUCS| (UCS) bietet ein plattformübergreifendes Domänenkonzept mit einem
gemeinsamen Vertrauenskontext zwischen Linux- und Windows-Systemen. Innerhalb
einer UCS-Domäne ist ein Benutzer mit seinem Benutzernamen und Passwort auf
allen Systemen bekannt, und kann für ihn freigeschaltete Dienste nutzen.

|UCSUAS| baut auf das flexible Domänenkonzept von UCS auf und integriert einige
schulspezifische Erweiterungen.

.. _structure-userroles:

|UCSUAS|-Benutzerrollen
=======================

In einer Standard-UCS-Installation sind alle Benutzerkonten vom selben Typ und
unterscheiden sich nur anhand ihrer Gruppenmitgliedschaften. In einer
|UCSUAS|-Umgebung ist jeder Benutzer einer *Rolle* zugeordnet, aus der sich
Berechtigungen in der |UCSUAS|-Verwaltung ergeben:

Schüler
   *Schülern* wird in der Standardeinstellung kein
   Zugriff auf die Administrationsoberflächen gewährt. Sie können sich
   mit ihren Benutzerkonten nur an Windows-Clients anmelden und die für
   sie freigegebenen Dateifreigaben und Drucker verwenden.

Lehrer
   *Lehrer* erhalten gegenüber Schülern
   zusätzliche Rechte, um z.B. auf UMC-Module zuzugreifen, die das
   Zurücksetzen von Schülerpasswörtern oder das Auswählen von
   Internetfiltern ermöglichen. Die einem Lehrer angezeigten Module
   können individuell definiert werden, Lehrer erhalten in der Regel
   aber nur Zugriff auf einen Teil der von der |UCSUMC| bereitgestellten
   Funktionen.

Schuladministrator
   *Schuladministratoren* erhalten, auf den Servern ihrer jeweiligen Schule,
   administrativen Zugriff auf die |UCSUAS|-UMC-Module. Sie können z.B. Computer
   zu Rechnergruppen zusammenfassen, neue Internetfilter definieren oder auch
   Lehrerpasswörter zurücksetzen. Schuladministratoren, die mit dem
   |UCSUAS|-UMC-Modul erstellt werden, besitzen nicht die Option
   *UCS\@school-Lehrer* und befinden sich nicht in der Gruppe :samp:`{lehrer-OU}`
   (siehe auch :ref:`school-setup-generic-schooladmins`).

Mitarbeiter
   Der Benutzertyp *Mitarbeiter* kommt häufig im Umfeld der Schulverwaltung zum
   Einsatz. Er besitzt in der Standardeinstellung ähnliche Zugriffsrechte wie
   ein Schülerkonto, kann jedoch mit zusätzlichen Rechten ausgestattet werden
   (siehe auch :ref:`structure-edunet-vs-adminnet`).

System-Administrator
   Die *System-Administratoren* sind Mitarbeiter mit vollem administrativen
   Zugriff auf die |UCSUAS|-Systeme, also beispielweise ein IT-Dienstleister,
   der die Schule beim Betrieb der Server unterstützt.

Überschneidungen der Benutzertypen Lehrer, Mitarbeiter und Schuladministrator
sind möglich. So können z.B. Benutzerkonten erstellt werden, die eine Nutzung
des Kontos als Lehrer und Mitarbeiter ermöglichen.

Für die Pflege der Benutzerkonten stehen mehrere Möglichkeiten zur Verfügung.
Die Bearbeitung von Benutzerkonten kann über die |UCSUMC| erfolgen. Darüber
hinaus bringt |UCSUAS| flexible Importskripte mit. Sie lesen Tabulator-getrennte
Importdateien oder CSV-Dateien ein, die üblicherweise aus vorhandenen
Schulverwaltungssystemen extrahiert werden können und so einen automatisierten
Abgleich ermöglichen.

.. _structure-distribution:

Aufteilung von |UCSUAS|
=======================

Für den Betrieb von |UCSUAS| an einer einzelnen Schule reicht ein Serversystem
aus (dieses wird dann in der UCS-Systemrolle |UCSPRIMARYDN_e| installiert). Ein
solches Szenario wird nachfolgend auch als *Single-Server-Umgebung* bezeichnet.

Für Schulträger oder große Schulen mit mehreren Standorten oder mit einer großen
Anzahl an Clients, kann die |UCSUAS|-Installation auf mehrere Server verteilt
werden (*Multi-Server-Umgebung*). Dabei wird ein |UCSPRIMARYDN| als der primäre
Server zur Datenverwaltung genutzt. Für jeden Schul-Standort wird dann ein
|UCSREPLICADN| installiert, nachfolgend als *Schulserver* bezeichnet.

.. caution::

   |UCSUAS| unterstützt derzeit für Edukativ- und Verwaltungsnetz jeweils nur
   einen Schulserver pro Standort.

   Darüber hinaus können UCS-Systeme mit der Rolle *Managed-Node-Server*
   installiert und an den Schul-Standorten betrieben werden. Diese zusätzlichen
   UCS-Systeme können jedoch nicht in Verbindung mit |UCSUAS|-Funktionalitäten
   eingesetzt werden; z.B. wird das Sperren von Dateifreigaben über die
   |UCSUAS|-UMC-Module auf den zusätzlichen UCS-Systemen nicht unterstützt.

   Zusätzlich müssen die Rechnerobjekte der zusätzlichen UCS-Systeme vor dem
   Domänenbeitritt unterhalb der Organisationseinheit (OU) der Schule angelegt
   werden (siehe auch :ref:`structure-ou-replication`). Die Einrichtung
   zusätzlicher UCS-Systeme wird in :ref:`school-performance-scaling`
   beschrieben.

.. _structure-ou-replication:

Replikation der LDAP-Daten auf die Schul-Standorte
--------------------------------------------------

Ein Schulserver bietet alle an einem Standort verwendeten Dienste an. Die
Anfragen an den LDAP-Verzeichnisdienst erfolgen dabei gegen einen lokalen
LDAP-Server, der automatisch gegen den |UCSPRIMARYDN| fortlaufend repliziert und
aktualisiert wird. Dies gewährleistet einen reibungslosen Betrieb, auch wenn die
Verbindung zwischen Schulserver und dem zentralen |UCSPRIMARYDN| einmal
ausfallen sollte.

Aus Sicherheitsgründen speichern die Schulserver nur eine Teilreplikation des
LDAP-Verzeichnisses. Nur die für den Schulserver relevanten Teile (z.B. Benutzer
und Gruppen der jeweiligen Schule) sowie die globalen Strukturen des
LDAP-Verzeichnisses, inklusive deren Benutzer und Gruppen, werden auf den
Schul-Server übertragen.

.. caution::

   Benutzer, deren Benutzerkonto nicht unterhalb einer
   Organisationseinheit der Schule (Schul-OU) liegt, können ihr Passwort
   nur über die UMC des |UCSPRIMARYDN| oder eines |UCSBACKUPDN| ändern
   (nicht über den Schulserver am Standort bzw. einem dort angebundenen
   Windows-Client).

   Ebenso dürfen Benutzer, deren Benutzerkonto unterhalb einer
   Schul-Organisationseinheit liegt, aus Sicherheitsgründen nicht Mitglied der
   Gruppe ``Domain Admins`` sein.

In |UCSUAS| werden schulübergreifende Benutzerkonten unterstützt. Ein
Benutzerobjekt existiert im LDAP-Verzeichnis nur einmal an seiner
primären Schule. An die weiteren Schulen wird nur ein Ausschnitt des
LDAP-Verzeichnisses dieser Schule repliziert: sein Benutzerobjekt und
die Standardgruppen. Verlässt der Benutzer die Schule, wird sein
Benutzerobjekt dort gelöscht bzw. nicht mehr dorthin repliziert.
Schulübergreifende Benutzerkonten können nur mit Importskripten
verwaltet werden.

Zur Unterteilung der im LDAP-Verzeichnisdienst hinterlegten Objekte und
Einstellungen wird für jede Schule im LDAP-Verzeichnis eine eigene
*Organisationseinheit* (OU) angelegt. Unterhalb
dieser OU werden Container für z.B. Benutzerobjekte, Gruppen,
DHCP-Einstellungen, usw. angelegt. Diese OUs werden direkt unterhalb der
LDAP-Basis angelegt.

|UCSUAS| unterscheidet in seinem Verzeichnisdienst zwischen dem Namen einer
Schule und dem Schulkürzel (OU-Namen). Der Name einer Schule kann frei gewählt
werden und wird primär in den UMC-Modulen angezeigt (in anderem Kontexten wird
dieser Wert häufig auch als Anzeigename bezeichnet). Der eigentliche Name der
Organisationseinheit (OU) wird nachfolgend auch als Schulkürzel bezeichnet. Das
Schulkürzel sollte ausschließlich aus Buchstaben, Ziffern oder dem Bindestrich
bestehen, da es unter anderem die Grundlage für Gruppen-, Freigabe- und
Rechnernamen bildet. Häufig kommen hier Schulnummern wie *340* oder
zusammengesetzte Kürzel wie ``g123m`` oder ``gymmitte`` zum Einsatz.

.. _structure-ou-schoolserver-multiple-ous:

Replikation mehrerer Schulen auf einen Schulserver
--------------------------------------------------

Im Normalfall repliziert ein Schulserver die LDAP-Daten für genau eine Schule.
Es gibt jedoch Szenarien, in denen es wünschenswert ist, wenn die LDAP-Daten
(Benutzerkonten, Gruppen, Rechnerkonten, Räume, ...) von mehreren Schulen auf
einem Schulserver vorgehalten werden. Beginnend mit |UCSUAS| 4.4v5 bietet
|UCSUAS| die Möglichkeit an, dass sich mehrere Schulen einen Schulserver teilen.

Dabei sind einige Randbedingungen zu beachten:

* Jede Schule darf nur auf *einen* Schulserver repliziert werden. Die
  Replikation einer Schule auf mehrere Schulserver ist nicht erlaubt und wird
  nicht unterstützt.

* Direkt nach dem Hinzufügen eines existierenden Schulservers zu einer neuen
  Schule muss der Schulserver erneut der Domäne beitreten (auf der Kommandozeile
  über den Befehl :command:`univention-join`). Anderenfalls kann es zu
  Inkonsistenzen im LDAP-Verzeichnis aufgrund geänderter Zugriffsberechtigungen
  kommen.

* Der DHCP-Dienst wird auf Schulservern, die mehrere Schulen vorhalten, *nicht*
  unterstützt. Hier kann es in den Logdateien auf dem Schulserver ggf. zu
  Fehlermeldungen des DHCP-Dienstes kommen, die in diesem Szenario ignoriert
  werden können.

* Lehrkräfte können in der Univention Management Console nur die Benutzer,
  Klassen, Arbeitsgruppen, Druckaufträge, Computerräume und Rechner der Schulen
  sehen, in denen sie auch Mitglied sind. Eine Ausnahme bilden die UMC-Module
  *Klassenarbeiten* und *Materialien verteilen*, welche die Klassenarbeiten und
  Verteilungsprojekte aller Schulen anzeigen, die auf diesem Schulserver
  verwaltet werden, unabhängig davon, ob die Lehrkräfte Mitglied der jeweiligen
  anderen Schulen sind.

* Ein Computerraum kann nur einer einzelnen Schule zugeordnet werden. D.h er
  kann nicht von mehreren Schulen aus genutzt bzw. geteilt werden. Werden zwei
  Räume mit dem gleichen Namen an unterschiedlichen Schulen erstellt, handelt es
  sich für |UCSUAS| um zwei vollkommen unabhängige Räume.

* Die Freigaben aller dem Schulserver zugeordneten Schulen werden von dem
  Dateiserver Samba angezeigt. Die Namen der Freigaben entsprechen i.d.R. dem
  Schema ``$OU-$CLASS`` bzw. ``$OU-$WORKGROUP``. Der Zugriff auf die automatisch
  erstellten Freigaben wird über die Gruppenmitgliedschaften
  (Arbeitsgruppen/Klassen) gesteuert.

* Da der Schulserver die Authentifizierung für die Windows-Rechner durchführt,
  ist es allen Benutzern der Schulen eines Schulservers möglich, sich auf allen
  Windows-Rechnern anzumelden, die gegen den Schulserver gejoined wurden.

* Das Teilen eines Schulservers durch mehrere Schulen beschränkt sich auf die
  Schulserver des Edukativnetzes. Der Betrieb von mehreren Schulen auf einem
  Server des Verwaltungsnetzes wird nicht unterstützt!

  Nähere Informationen zu Verwaltungs- und Edukativnetzen finden sich in
  :ref:`structure-edunet-vs-adminnet`.

Die Einrichtung mehrerer Schulen auf einem Schulserver wird in
:ref:`school-setup-umc-schools-schoolserver-multiple-ous` beschrieben.

.. _structure-edunet-vs-adminnet:

Verwaltungsnetz und Edukativnetz
================================

Die Netze für den edukativen Bereich und für die Schulverwaltung müssen aus
organisatorischen oder rechtlichen Gründen in der Regel logisch und/oder
physikalisch getrennt werden. In |UCSUAS| kann daher zusätzlich zur Unterteilung
in Organisationseinheiten (OU) noch eine Unterteilung der OU in Verwaltungsnetz
und Edukativnetz erfolgen.

Diese optionale Unterteilung findet auf Ebene der Serversysteme bzw. der
Netzwerksegmente statt und sieht vor, dass in einer Schule ein Schulserver für
das edukative Netz und ein Schulserver für das Verwaltungsnetz betrieben wird.
Diese Server verwenden für ihre Client-Systeme (Schülerrechner bzw. Rechner der
Verwaltung) jeweils ein eigenes IP-Subnetz.

Auch bei der Unterteilung in Verwaltungsnetz und Edukativnetz findet eine
selektive Replikation statt, wie sie in :ref:`structure-ou-replication`
beschrieben wird. Zusätzlich wird jedoch bei der Replikation der Benutzerkonten
anhand ihrer Benutzerrolle(n) unterschieden.

Auf den Schulserver des edukativen Netzes werden die Benutzerkonten mit den
Benutzerrollen *Schüler*, *Lehrer*, *Schuladministrator* und
*System-Administrator* repliziert. Auf den Schulserver der Verwaltung werden die
Benutzerkonten mit den Benutzerrollen *Mitarbeiter*, *Schuladministrator* und
*System-Administrator* repliziert. Die gemeinsame Verwendung der Benutzerrollen
*Lehrer* und *Mitarbeiter* für ein Benutzerkonto ist möglich, z.B. für
Benutzerkonten der Schulleitung, die neben ihrer Verwaltungstätigkeit auch
lehrend tätig sind.

.. note::

   Die Einrichtung eines Verwaltungsnetzes ist in einer Single-Server-Umgebung
   nicht möglich. Hier werden alle Benutzerkonten auf dem Primary Directory Node
   vorgehalten.

.. caution::

   |UCSUAS| setzt für die Unterteilung in Edukativ- und Verwaltungsnetz eine
   physikalische Trennung der beiden Netzwerksegmente voraus. D.h. das edukative
   Netz und das Verwaltungsnetz können nicht gleichzeitig im gleichen
   Netzwerksegment verwendet werden. Ergänzend dazu müssen auch die Hinweise zu
   DHCP-DNS-Richtlinien in :ref:`school-installation-replica-directory-node`
   beachtet werden.

.. _structure-staff-in-edunet:

Mitarbeiter im Edukativnetz
---------------------------

Benutzerkonten mit der Benutzerrolle *Mitarbeiter* aus dem Verwaltungsnetz
können explizit auf Schulserver im Edukativnetz repliziert werden. Benutzer in
dieser Rolle können sich anschließend gegen den Schulserver im Edukativnetz
authentifizieren und so zum Beispiel Zugriff auf Dateifreigaben erhalten oder
sich an einem Client anmelden, der Teil der lokalen Domäne ist. Sie können zu
Arbeitsgruppen hinzugefügt werden. Mitarbeiter können keine edukativen UMC
Module verwenden, wie zum Beispiel die Computerraumverwaltung oder den
Klassenarbeitsmodus.

Folgende Schritte sind nötig, um die Replikation von Benutzern in der Rolle
*Mitarbeiter* auf Schulserver im Edukativnetz zu aktivieren:

1. Auf dem |UCSPRIMARYDN| und *allen* |UCSBACKUPDN|\ s müssen die LDAP ACLs
   angepasst und der LDAP-Server neu gestartet werden:

   .. code-block:: console

      $ ucr set ucsschool/ldap/replicate_staff_to_edu="true"
      $ ucr commit /etc/ldap/slapd.conf
      $ systemctl restart slapd


2. Nach der Änderung der LDAP ACLs werden nur modifizierte und neu erstellte
   Benutzerkonten *automatisch* repliziert, solange kein erneuter
   Domänenbeitritt durchgeführt wird. Um *bestehende* Benutzerkonten zu
   replizieren, müssen die Schulserver im Edukativnetz der Domäne erneut
   beitreten. Nach der Aktivierung zusätzlicher LDAP ACLs können alle
   Schulserver im Edukativnetz die Benutzerkonten der Rolle *Mitarbeiter* vom
   |UCSPRIMARYDN| und den |UCSBACKUPDN|\ s lesen.

   .. caution::

      Wenn alle bestehenden Benutzerkonten der Rolle *Mitarbeiter* in einem Lauf
      repliziert werden sollen, müssen edukative Schulserver mit
      :command:`univention-join` der Domäne erneut beitreten. Hierbei ist zu
      beachten, dass der erneute Domänenbeitritt eines edukativen Schulservers
      einige Zeit in Anspruch nimmt und in der Zwischenzeit nicht verwendet
      werden kann. Planen Sie dafür ein Wartungsfenster ein.

.. _structure-schoolservers-in-staffnet:

Schulserver im Verwaltungsnetz
------------------------------

Auf den Schulservern des Verwaltungsnetzes werden keine speziellen Dienste oder
UMC-Module angeboten. Sie dienen den Verwaltungsrechnern hauptsächlich als
Anmelde-, Druck- und Dateiserver. Die Benutzerkonten mit der Benutzerrolle
*Mitarbeiter* haben entsprechend keinen Zugriff auf die |UCSUAS|-spezifischen
UMC-Module des edukativen Netzes. Im Gegensatz zu den Benutzern des edukativen
Netzes werden für die Benutzer des Verwaltungsnetzes keine automatischen
Einstellungen für Windows-Profilverzeichnis oder Windows-Heimatverzeichnis
gesetzt.

Die Installationsschritte für Schulserver des Edukativnetzes und des
Verwaltungsnetzes sind sehr ähnlich. In
:ref:`school-installation-replica-directory-node` werden diese ausführlich
beschrieben.

.. _structure-ldap:

|UCSUAS|-Objekte im LDAP-Verzeichnisdienst
==========================================

|UCSUAS| erstellt zur Verwaltung der schulspezifischen Erweiterungen zusätzliche
Strukturen im LDAP-Verzeichnisdienst. Im Folgenden werden einige Funktionen
dieser Container und Objekte genauer vorgestellt.

Wie bereits im :ref:`structure-ou-replication` beschrieben wurde, wird für jede
Schule direkt unterhalb der LDAP-Basis eine eigene Organisationseinheit (OU)
angelegt. Unterhalb dieser OU werden Container für Benutzerobjekte, Gruppen und
weitere |UCSUAS|-relevante Objekte erstellt. Darüber hinaus werden einige neue
Objekte in den bereits bestehenden UCS-Strukturen des LDAP-Verzeichnisses
angelegt.

.. _structure-ldap-ou:

Struktur einer |UCSUAS|-OU
--------------------------

Der Aufbau einer Schul-OU wird nachfolgend am Beispiel der Schul-OU ``gymmitte``
in einem LDAP-Verzeichnis mit der LDAP-Basis ``dc=example,dc=com`` erläutert.

* ``cn=computers,ou=gymmitte,dc=example,dc=com``

  In diesem Container werden Rechnerobjekte abgelegt, die von der OU verwaltet
  werden. Dies können z.B. Objekte vom Typ *Windows-Client* oder
  *IP-Managed-Client* sein. Die Rechnerobjekte für Schulserver (Verwaltungs- und
  Edukativnetz) werden in dem Untercontainer
  ``cn=dc,cn=server,cn=computers,ou=gymmitte,dc=example,dc=com`` abgelegt.

* ``cn=examusers,ou=gymmitte,dc=example,dc=com``

  Dieser Container enthält temporäre Prüfungsbenutzer, die für den
  Klassenarbeitsmodus benötigt werden. Sie werden zu Beginn bzw. nach Beendigung
  des Klassenarbeitsmodus automatisch erstellt bzw. wieder gelöscht.

* ``cn=groups,ou=gymmitte,dc=example,dc=com``

  ``cn=raeume,cn=groups,ou=gymmitte,dc=example,dc=com``

  ``cn=schueler,cn=groups,ou=gymmitte,dc=example,dc=com``

  ``cn=klassen,cn=schueler,cn=groups,ou=gymmitte,dc=example,dc=com``

  In den aufgeführten Containern werden Gruppenobjekte für |UCSUAS| vorgehalten.
  Im Container ``cn=groups`` werden automatisch einige Standard-Gruppen
  angelegt, die alle Schüler, Lehrer bzw. Mitarbeiter der Schul-OU als
  Gruppenmitglied enthalten. Diese Gruppen werden bei der Verwendung der
  |UCSUAS|-Import-Mechanismen automatisch gepflegt. Beim Import von Benutzern
  über die Importskripte oder über die UMC-Module wird den Benutzern je nach
  ihrer Benutzerrolle eine der drei Gruppen automatisch als primäre Gruppe
  zugeordnet. Die Namen der drei Gruppen lauten ``schueler-gymmitte``,
  ``lehrer-gymmitte`` und ``mitarbeiter-gymmitte``.

  Gruppenobjekte für Schulklassen müssen im Untercontainer ``cn=klassen``
  abgelegt werden, damit diese von |UCSUAS| korrekt als Klassengruppe erkannt
  werden. Im übergeordneten Container ``cn=schueler`` werden von den
  |UCSUAS|-Modulen Gruppenobjekte für klassenübergreifende Arbeitsgruppen (z.B.
  Musik-AG) gepflegt, die z.B. über das UMC-Modul *Arbeitsgruppen verwalten*
  erstellt werden.

  Beim Anlegen von Räumen über das UMC-Modul *Computerräume verwalten* werden
  ebenfalls Gruppenobjekte erstellt, die im Container ``cn=raeume`` abgelegt
  werden. Diese Gruppenobjekte enthalten üblicherweise ausschließlich
  Rechnerobjekte als Gruppenmitglieder.

* ``cn=shares,ou=gymmitte,dc=example,dc=com``

  ``cn=klassen,cn=shares,ou=gymmitte,dc=example,dc=com``

  Die beiden Container enthalten allgemeine bzw. klassenspezifische
  Freigabeobjekte für die Schul-OU.

* ``cn=users,ou=gymmitte,dc=example,dc=com``

  Die Benutzerobjekte für |UCSUAS| müssen entsprechend ihrer Benutzerrolle in
  einem der vier Untercontainer ``cn=schueler``, ``cn=lehrer``, ``cn=lehrer und
  mitarbeiter``, ``cn=mitarbeiter`` oder ``cn=admins`` erstellt werden.

* ``cn=dhcp,ou=gymmitte,dc=example,dc=com``

  ``cn=networks,ou=gymmitte,dc=example,dc=com``

  ``cn=policies,ou=gymmitte,dc=example,dc=com``

  ``cn=printers,ou=gymmitte,dc=example,dc=com``

  Die genannten Container enthalten (analog zu ihrem globalem Pendant direkt
  unterhalb der LDAP-Basis) die DHCP-, Netzwerk-, Richtlinien- und
  Drucker-Objekte für die jeweilige Schul-OU.

.. note::

   |UCSUAS| unterstützt aktuell keine weitere Strukturierung der LDAP-Objekte
   durch Untercontainer oder Unter-OUs in den oben angegebenen Containern.

.. _structure-ldap-global:

Weitere |UCSUAS|-Objekte
------------------------

Für die Steuerung von Zugriffsrechten auf |UCSUAS|-Funktionen und das
LDAP-Verzeichnis werden mit dem Erstellen einer neuen Schul-OU automatisch
einige Gruppen erstellt. Auch diese Gruppen werden am Beispiel der OU
``gymmitte`` in einem LDAP-Verzeichnis mit der LDAP-Basis ``dc=example,dc=com``
erläutert.

* ``cn=DC-Edukativnetz,cn=ucsschool,cn=groups,dc=example,dc=com``

  ``cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,dc=example,dc=com``

  ``cn=Member-Edukativnetz,cn=ucsschool,cn=groups,dc=example,dc=com``

  ``cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,dc=example,dc=com``

  Diese Gruppen werden beim Erstellen der ersten Schul-OU einmalig angelegt und
  sind nicht spezifisch für eine bestimmte OU. Sie enthalten (entsprechend ihrem
  Namen) als Gruppenmitglieder die Schul-DCs oder die |UCSMANAGEDNODE| Server der
  Schulstandorte, wobei diese jeweils nach Verwaltungsnetz und Edukativnetz
  getrennt werden. Über diese Gruppen werden Zugriffsrechte von
  |UCSUAS|-Systemen auf die |UCSUAS|-Objekte im LDAP gesteuert. Primary
  Directory Node und Backup Directory Node dürfen **kein** Mitglied in einer
  dieser Gruppen sein.

* ``cn=OUgymmitte-DC-Edukativnetz,cn=ucsschool,cn=groups,dc=example,dc=com``

  ``cn=OUgymmitte-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,dc=example,dc=com``

  ``cn=OUgymmitte-Member-Edukativnetz,cn=ucsschool,cn=groups,dc=example,dc=com``

  ``cn=OUgymmitte-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,dc=example,dc=com``

  Diese OU-spezifischen Gruppen werden während des Anlegens der Schul-OU
  erstellt. Sie enthalten (entsprechend ihrem Namen) als Gruppenmitglieder die
  Schul-DCs oder die |UCSMANAGEDNODE| Server der jeweiligen OU (hier
  ``gymmitte``), wobei diese jeweils nach Verwaltungsnetz und Edukativnetz
  getrennt werden. |UCSPRIMARYDN| und |UCSBACKUPDN| dürfen **kein** Mitglied in
  einer dieser Gruppen sein.

* ``cn=OUgymmitte-Klassenarbeit,cn=ucsschool,cn=groups,dc=example,dc=com``

  Während eines laufenden Klassenarbeitsmodus werden die beteiligten Benutzer
  und Rechner als Gruppenmitglieder zu dieser Gruppe hinzugefügt. Sie wird z.B.
  für die Steuerung von speziellen Einstellungen für den Klassenarbeitsmodus
  verwendet.

* ``cn=admins-gymmitte,cn=ouadmins,cn=groups,dc=example,dc=com``

  Benutzer, die Mitglied dieser Gruppe sind, werden von |UCSUAS| in der
  betreffenden OU automatisch als Schuladministrator behandelt. Siehe dazu auch
  :ref:`school-setup-generic-schooladmins`.
