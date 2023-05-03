.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _materials:

Materialien verteilen
=====================

Diese Funktion vereinfacht das Verteilen und Einsammeln von Unterrichtsmaterial
an Klassen oder Arbeitsgruppen. Optional kann eine Frist festgelegt werden. So
ist es möglich, Aufgaben zu verteilen, die bis zum Ende der Unterrichtsstunde zu
bearbeiten sind. Nach Ablauf der Frist werden die verteilten Materialien dann
automatisch wieder eingesammelt und im Heimatverzeichnis des Lehrers abgelegt.

Die für eine solche Verteilung notwendigen Informationen werden als *Projekt*
bezeichnet.

Ein mögliches Beispielszenario:
   Die Schüler des Mathematikunterrichts sollen bis zur nächste
   Unterrichtsstunde (ein paar Tage später) ein Dokument bearbeiten. Dafür
   erstellt die Lehrkraft ein neues Projekt und lädt das zu verteilende Dokument
   in die Materialverteilung hoch.

   Als Frist wird der Startzeitpunkt der nächsten Unterrichtsstunde angegeben.

   Mit dem Erstellen des Projektes wird das Dokument automatisch in die
   Heimatverzeichnisse der Schüler verteilt.

   Die Schüler bearbeiten das Dokument bis zur nächsten Unterrichtsstunde (z.B.
   im Unterricht oder in Freistunden).

   Zum festgelegten Abgabezeitpunkt wird das Dokument automatisiert
   eingesammelt. Dazu wird das Dokument aus den Heimatverzeichnissen der Schüler
   in das Heimatverzeichnis der Lehrkraft kopiert und steht anschließend der
   Lehrkraft zur Durchsicht zur Verfügung.

.. _materials-project:

Verwaltung von Projekten
------------------------

Die Funktion kann über das Modul *Materialien verteilen* erreicht
werden. Hier findet sich eine Liste aller bestehenden Projekte. Das Anlegen
weiterer Projekte ist in :ref:`materials-add-project` beschrieben.

.. _distribution-projects:

.. figure:: /images/distribution_projects_1.png
   :alt: Liste von Materialverteilungsprojekten

   Liste von Materialverteilungsprojekten

Im Hauptmenü ist eine Liste aller Projekte zu sehen. Jedes Projekt ist einem
Lehrer zugeordnet, der unter *Eigentümer* angezeigt wird. Über die Option
*Übernehmen* kann ein anderer Lehrer das Projekt übernehmen. Bestehende Projekte
können außerdem bearbeitet oder gelöscht werden.

Das *Einsammeln* von Dateien ist in :ref:`materials-collect` beschrieben.

.. _materials-add-project:

Neues Projekt erstellen
-----------------------

In der unteren Bildzeile findet sich die Option *Projekt hinzufügen*, mit der
ein neues Projekt registriert werden kann.

.. _distribution-project-2:

.. figure:: /images/distribution_projects_2.png
   :alt: Erstellen eines Materialverteilungsprojekts

   Erstellen eines Materialverteilungsprojekts

* Als *Beschreibung* muss ein Projektname eingetragen werden, z.B.
  ``Klassenarbeit Mathematik``. Der Verzeichnisname legt fest, wo die Daten
  abgelegt werden.

* Das Feld *Verteilen der Projektdateien* erlaubt die Automatisierung
  des Verteilens von Projektdaten. In der Grundeinstellung *Manuelles
  Verteilen* wird die Verteilung der Projektdateien durch den Lehrer manuell
  ausgelöst.

  Durch Auswahl von *Automatisches Austeilen* kann auch ein fester Zeitpunkt
  definiert werden, zu dem die Dateien in die Heimatverzeichnisse der Schüler
  kopiert werden. Dieser Zeitpunkt kann über die Auswahlfelder
  *Verteilungsdatum* und *Verteilungszeit* vorgegeben werden.

* Analog zu der automatischen Verteilung können Projektdateien auch im
  Auswahlfeld *Einsammeln der Projektdateien* manuell oder automatisch
  eingesammelt werden.

* Unter *Mitglieder* können mit *Hinzufügen* einzelne Klassen oder
  Arbeitsgemeinschaften zugeordnet werden, bzw. mit *Entfernen* wieder entfernt
  werden.

* Im Untermenü *Dateien* werden die zu verteilenden Dokumente ausgewählt. Ein
  Klick auf *Hochladen* öffnet ein Fenster, mit dem eine Datei ausgewählt werden
  kann. Mit *Entfernen* können Dateien wieder abgewählt werden.

* Ein Klick auf :guilabel:`Projekt erstellen` schließt das Anlegen eines
  Projekts ab.

.. _materials-collect:

Einsammeln der verteilten Dokumente
-----------------------------------

Die nachfolgende Beschreibung gibt einen Überblick über das manuelle Einsammeln
der Dokumente eines bestehenden Verteilungsprojekts. Es wird durch einen Klick
auf *Einsammeln* in der Liste der Materialverteilungsliste gestartet. Durch
mehrfaches Einsammeln kann beispielsweise der Arbeitsfortschritt festgehalten
werden.

.. _distribution-project-collect:

.. figure:: /images/distribution_projects_4.png
   :alt: Einsammeln eines Materialverteilungsprojekts

   Einsammeln eines Materialverteilungsprojekts

Die eingesammelten Dateien werden im Heimatverzeichnis der Lehrkraft
abgelegt, die das Verteilungsprojekt erstellt hat. Dies erfolgt
unabhängig davon, welche Lehrkraft das Einsammeln der Dateien auslöst.

Die Dateien befinden sich im Verzeichnis
:file:`Unterrichtsmaterial/{Projektname-Ergebnisse}` unterhalb des persönlichen
Heimatverzeichnisses der Lehrkraft. Unterhalb dieses Verzeichnisses wird für
jeden Schüler und Lehrer ein Verzeichnis angelegt, das die eingesammelten
Dateien enthält, so dass eine nachträgliche Zuordnung leicht möglich ist.

Werden die Ergebnisse mehrfach eingesammelt, wird für jeden Einsammelvorgang und
Schüler und Lehrer jeweils ein eigenes Verzeichnis angelegt.
