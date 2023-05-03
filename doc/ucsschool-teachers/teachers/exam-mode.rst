.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _exam-mode:

Klassenarbeitsmodus
===================

Die Anforderungen, die in einer Klassenarbeitssituation an die IT-Infrastruktur
gestellt werden, sind vielfältig und variieren stark je nach Schulform,
Schulfach und Jahrgang. Um das Herstellen einer Klassenarbeitssituation in einem
Computerraum zu vereinfachen, stellt |UCSUAS| einen speziellen
Klassenarbeitsmodus zur Verfügung.

Der Klassenarbeitsmodus vereint die aus |UCSUAS| bekannten Funktionen, wie z.B.
der Materialverteilung, mit schulspezifischen Einstellungen, die durch den
Schuladministrator definiert werden können. Dabei ist zu beachten, dass vom
Klassenarbeitsmodus nur ein bestimmter Rahmen für eine Klassenarbeit
bereitgestellt wird - für die eigentliche Abnahme einer Klassenarbeit/Prüfung
ist gegebenenfalls weitere Software notwendig.

Der Klassenarbeitsmodus umfasst dabei folgende Eigenschaften:

* Für den Zeitraum der Klassenarbeit wird pro Schüler ein spezielles
  Benutzerkonto angelegt. Nur mit diesem speziellen Benutzerkonto kann ein
  Schüler an der Klassenarbeit teilnehmen. Der Anmeldename für das
  Klassenarbeitskonto setzt sich aus einem festgelegten Präfix (in der
  Standardeinstellung ``exam-``) und dem normalen Benutzernamen zusammen. Somit
  meldet sich der Benutzer ``anton123`` für die Klassenarbeit als
  ``exam-anton123`` an.

* Für den Zeitraum der Klassenarbeit wird sichergestellt, dass der Zugriff auf
  das ursprüngliche Heimatverzeichnis der Schüler nicht möglich ist.

* Zu Beginn der Klassenarbeit ist es möglich, die für die Klassenarbeit
  notwendigen Dateien (z.B. Aufgaben, Material) anzugeben und direkt an die
  Schüler zu verteilen.

* Mit dem Ende der Klassenarbeit werden alle Dateien des Klassenarbeitsordners
  wieder eingesammelt und nach Schülern sortiert im Heimatverzeichnis des
  Lehrers abgelegt.

* Des Weiteren kann - wie aus dem UMC-Modul *Computerraum* bekannt - der Zugang
  zum Internet sowie zu Datei- und Druck-Freigaben eingeschränkt werden.

Im Folgenden werden die einzelnen Schritte zum Erstellen einer Klassenarbeit
kurz beschrieben.

.. _exam-mode-overview:

Übersicht der Klassenarbeiten
-----------------------------

.. _fig-exam-mode-overview:

.. figure:: /images/exam_3_overview.png
   :alt: Übersicht über die Klassenarbeiten anzeigen

   Übersicht über die Klassenarbeiten anzeigen

Beim Öffnen des Moduls *Klassenarbeiten* in der |UCSUMC| zeigt sich zuerst eine
Übersichtsseite, die alle Informationen über gerade laufende Klassenarbeiten
anzeigt. Dabei kann man Auswählen, ob man nur die eigenen Klassenarbeiten
angezeigt bekommen möchte oder auch die aller Kolleginnen und Kollegen.

.. _exam-mode-start:

Einrichten einer Klassenarbeit
------------------------------

Eine neue Klassenarbeit kann über den Knopf :guilabel:`Eine neue Klassenarbeit
vorbereiten` eingerichtet werden. In mehreren Schritten werden alle
Einstellungen für die Klassenarbeit festgelegt.

#. Alle notwendigen Einstellungen werden in den ersten beiden Schritten
   angegeben. Dazu ist es notwendig einen Namen für die Klassenarbeit zu
   definieren.

   Als Endzeit wird das Ende der laufenden Schulstunde vorgeschlagen, sie kann
   jedoch nach Belieben angepasst werden. Für die Klassenarbeit ist die Endzeit
   nicht verbindlich, sondern wird lediglich genutzt, um über die verbleibende
   Zeit zu informieren. Mit Erreichen der vorgesehenen Endzeit wird ein
   Erinnerungsdialog im Modul *Computerraum* eingeblendet. Die Klassenarbeit
   kann ohne weiteres auch über das vorgesehene Ende hinaus weitergeführt
   werden.

   Über die auf der Seite enthaltenen Auswahlkästchen kann eingestellt werden,
   welche weiteren Einstellungsmöglichkeiten in den nächsten Schritten des
   Assistenten abgefragt werden. Dazu gehört das Verteilen von
   Unterrichtsmaterialien, das Festlegen von Einschränkungen für den Zugang zum
   Internet sowie die Zugriffssteuerung auf Freigaben.

#. Im zweiten Schritt muss der Computerraum in dem die Arbeit geschrieben werden
   soll, sowie mindestens eine teilnehmende Klasse bzw. Arbeitsgruppe, angegeben
   werden. Die einzelnen Mitglieder der ausgewählten Gruppen werden zusätzlich
   auf dieser Seite angezeigt. Falls weitere Einstellungsmöglichkeiten aktiviert
   wurden, werden diese auf den folgenden Seiten des Assistenten angezeigt.

#. Im nächsten optionalen Schritt kann ein passender Verzeichnisname für die
   Klassenarbeit ausgewählt und alle benötigten Klassenarbeitsdateien
   nacheinander hochgeladen werden. Diese Klassenarbeitsdateien werden an alle
   teilnehmenden Schüler ausgeteilt. Eine Kopie der Originaldateien wird im
   Heimatverzeichnis des Lehrers abgelegt, der die Klassenarbeit erstellt hat.
   Die Dateien werden im Heimatverzeichnis der Schüler unterhalb des Ordners
   :file:`Klassenarbeiten` und dem angegebenen Verzeichnisnamen abgelegt.

   Zu jedem Zeitpunkt der laufenden Klassenarbeit können die Dateien aus den
   Heimatverzeichnissen der Schüler eingesammelt werden. Dabei werden lediglich
   die Dateien unterhalb des Klassenarbeitsordners berücksichtigt. Die
   eingesammelten Dateien werden im Klassenarbeitsverzeichnis des
   Lehrer-Heimatverzeichnisses gespeichert. Durch mehrfaches Einsammeln kann
   beispielsweise der Arbeitsfortschritt festgehalten werden.

#. Zuletzt können optional Einschränkungen für den Zugang zum Internet und den
   Zugriff auf Freigaben festgelegt werden. Diese Einstellungen können jederzeit
   während einer laufenden Klassenarbeit über die Raumeinstellungen des Moduls
   *Computerraum* angepasst werden. Die einzelnen Einstellungsmöglichkeiten
   werden auch unter :ref:`computer-room` beschrieben.

Durch Drücken der Schaltfläche :guilabel:`Klassenarbeit starten` werden die
notwendigen Klassenarbeitskonten für die Schüler angelegt, die
Klassenarbeitsdateien verteilt und die Raumeinstellungen gesetzt. Dies kann je
nach Serverauslastung, Geschwindigkeit der Verbindung zum Server und Anzahl der
Schüler und Rechner im Raum einige Minuten dauern.

Alternativ kann man die Klassenarbeit jederzeit über die Schaltfläche
*Klassenarbeit speichern* zur späteren Bearbeitung abspeichern. Dazu muss
lediglich ein Name angegeben werden. Auf der Übersicht können solche
Klassenarbeiten über die Schaltfläche *Klassenarbeit bearbeiten* erneut geladen
und weiter angepasst, oder, falls alle notwendigen Informationen vorhanden sind,
gestartet werden.

Nur die ursprünglichen Autoren dürfen Klassenarbeiten im Nachhinein bearbeiten
oder starten. Zudem können Lehrer jederzeit ihre vorbereiteten Klassenarbeiten
löschen, solange diese noch nicht gestartet worden sind.

Administratoren können jede vorbereitete und noch nicht gestartete Klassenarbeit
löschen.

.. _exam-restart:

Neustart der Schülerrechner
---------------------------

.. _fig-exam-restart:

.. figure:: /images/exam_1_reboot.png
   :alt: Neustart der Schülerrechner

   Neustart der Schülerrechner

Je nach Konfiguration der Schülerrechner kann es notwendig sein, dass alle
Schülerrechner des Computerraums neu gestartet werden. Nur durch einen Neustart
der betroffenen Rechner können einige spezifische Berechtigungen und
Rechnerkonfigurationen, die für den Klassenarbeitsmodus vorgesehen sind, wirksam
werden.

Sollte dieser Dialog beim Starten einer Klassenarbeit nicht erscheinen, ist ein
Neustart der Schülerrechner in dieser Umgebung nicht notwendig und wurde bewusst
von einem Administrator so eingerichtet. In diesem Fall kann der Abschnitt
übersprungen werden und es ist nicht erforderlich, die Computer manuell neu zu
starten.

Das Klassenarbeitsmodul bietet eine Hilfsfunktion an, so dass dieser Vorgang
weitgehend automatisiert durchgeführt werden kann. Dabei wird eine Verbindung zu
allen eingeschalteten Rechnern aufgebaut und alle eingeschaltete Rechner werden
aufgelistet, wie in :numref:`fig-exam-restart` dargestellt. Die aufgelisteten
Rechner können durch Klick auf die Schaltfläche :guilabel:`Schülerrechner
neustarten` automatisch neu gestartet werden. Rechner, an denen Lehrer
angemeldet sind, werden bei dieser Aktion automatisch ausgelassen. Voraussetzung
hierfür ist, dass die Lehrerbenutzer korrekt erkannt wurden (siehe auch Spalte
*Benutzer* in der Tabelle). Zusätzlich können einzelne Rechner ausgewählt und
über die Schaltfläche *Ausgewählte Rechner neustarten* neu gestartet werden.
Hierbei werden die Rechner ungeachtet des angemeldeten Benutzers (auch bei
Lehrerbenutzern!) neu gestartet.

.. caution::

   Nach der Bestätigung wird der Neustart der Rechner sofort ausgeführt. Es
   erfolgt dabei keine Warnung bei angemeldeten Benutzern. Daher können auf
   diesen Rechnern ggf. noch nicht gesicherte Daten verloren gehen.

.. note::

   Bitte stellen Sie zusätzlich sicher, dass eingeschaltete Rechner manuell neu
   gestartet werden, sollten dies nicht automatisch durchgeführt worden sein.

.. _manage-exams:

Verwaltung und Abschluss der Klassenarbeit
------------------------------------------

.. _fig-exam-computer-room:

.. figure:: /images/exam_2_computerroom.png
   :alt: Verwaltung der Klassenarbeit über das Computerraum-Modul im Klassenarbeitsmodus

   Verwaltung der Klassenarbeit über das Computerraum-Modul im Klassenarbeitsmodus

Die Klassenarbeit wird durchgeführt und verwaltet über das |UCSUMC|-Modul
*Computerraum* (siehe :numref:`fig-exam-computer-room`). Während einer
Klassenarbeit werden in dem Modul zusätzlich die verbleibende Zeit der
Klassenarbeit sowie für diesen Modus spezifische Aktionen angezeigt.

Zwischenergebnisse der Klassenarbeit können über die Schaltfläche
*Ergebnisse einsammeln* zusammengetragen werden. Diese Aktion kann
beliebig oft durchgeführt werden. Zum Beenden der Klassenarbeit muss die
Schaltfläche *Klassenarbeit beenden* ausgewählt werden.

.. note::

   Zum Abschluss der Klassenarbeit müssen alle Rechner entweder ausgeschaltet
   oder neu gestartet werden, bevor sie für den regulären Schulbetrieb wieder
   verwendet werden können. Ein Neustart/Ausschalten setzt die für die
   Klassenarbeit spezifischen Einstellungen an den Rechnern wieder zurück.
