.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-admins:

**********************************************
Verwaltungsfunktionen für Schuladministratoren
**********************************************

.. _passwords-teachers:

Passwörter (Lehrer)
===================

Dieses Modul erlaubt Schuladministratoren das Zurücksetzen von
Lehrer-Passwörtern. Die bestehenden Passwörter können aus Sicherheitsgründen
nicht ausgelesen werden. Wird ein Passwort vergessen, muss ein neues Passwort
vergeben werden.

Die Bedienung erfolgt analog zum in :ref:`student-passwords` beschriebene
Zurücksetzen von Passwörtern für Schüler.

.. _admindoku-pwmitarbeiter:

Passwörter (Mitarbeiter)
========================

Dieses Modul erlaubt Schuladministratoren das Zurücksetzen von
Mitarbeiter-Passwörtern. Die bestehenden Passwörter können aus
Sicherheitsgründen nicht ausgelesen werden. Wird ein Passwort vergessen, muss
ein neues Passwort vergeben werden.

Die Bedienung erfolgt analog zum in :ref:`student-passwords` beschriebene
Zurücksetzen von Passwörtern für Schüler.

.. _computer-room-create:

Computerräume verwalten
=======================

Mit der Funktion *Computerräume verwalten* werden Computer einer Schule einem
Computerraum zugeordnet. Diese Computerräume können von den Lehrern dann zentral
verwaltet werden, etwa indem der Internetzugang freigegeben wird.

.. _computerroom-list:

.. figure:: /images/computerrooms_1_overview.png
   :alt: Verwaltung von Computerräumen

   Verwaltung von Computerräumen

Mit *Raum hinzufügen* kann ein neuer Computerraum definiert werden. Neben einem
*Namen* kann auch eine weiterführende *Beschreibung* angegeben werden.

Mit der Option *Computer in dem Raum* können dem Raum Computer zugewiesen
werden. In der Auswahlliste werden nur Rechner angezeigt, die von den
technischen Betreuern registriert sind. Fehlen in der Liste Computer, sollte
dies an den Helpdesk gemeldet werden.

.. _add-to-computerroom:

.. figure:: /images/computerrooms_2_add_computers.png
   :alt: Zuweisen von Computern zu einem Computerraum

   Zuweisen von Computern zu einem Computerraum

Über die Liste *Lehrercomputer* können einzelne Computer des Raumes als
Lehrercomputer markiert werden.

Während einer Klassenarbeit unterliegt ein Lehrercomputer nicht den selben
Restriktionen, wie andere Rechner des Raumes. Somit hat der Lehrer an diesem
Rechner weiterhin Zugriff auf alle Dateifreigaben und kann das Internet
uneingeschränkt nutzen. Sollte sich ein Lehrercomputer in mehreren Räumen
befinden, so gilt er in allen Räumen als Lehrercomputer. Ebenso wird er in allen
Räumen wieder zu einem normalen Rechner sobald er in einem seiner Räume als
Lehrercomputer abgewählt wird.

Bereits angelegte Computerräume können auch nachträglich über das jeweilige Icon
bearbeitet oder gelöscht werden.

.. _lesson-times:

Unterrichtszeiten
=================

Die Funktion *Unterrichtszeiten* erlaubt es, die Zeiträume der jeweiligen
Schulstunden pro Schule zu definieren. So kann beispielsweise der Internetzugang
pro Schulstunde freigegeben werden.

.. _fig-lesson-times:

.. figure:: /images/lesson_times.png
   :alt: Festlegung der Unterrichtszeiten

   Festlegung der Unterrichtszeiten

Es wird empfohlen das Ende der Schulstunden inklusive der Pausen bis kurz vor Beginn
der nächsten Schulstunde anzugeben, da die Unterrichtszeiten als Vorgabe für die
raumbezogenen Einstellungen verwendet werden und damit z.B. der Internetzugang
nicht direkt mit der Pausenglocke deaktiviert wird.

.. _assign-teachers-to-pupils:

Lehrer Klassen zuordnen
=======================

Für jede Klasse gibt es einen gemeinsamen Datenbereich. Damit Lehrer auf diesen
Datenbereich zugreifen können, müssen sie der Klasse zugewiesen werden und somit
Mitglied der Klasse werden.

.. _classes-list:

.. figure:: /images/classes.png
   :alt: Liste der Klassen einer Schule

   Liste der Klassen einer Schule

Die Zuweisung kann über zwei Module erfolgen: *Lehrer zuordnen* und *Klassen
zuordnen*.

Lehrer zuordnen
   Das Modul *Lehrer zuordnen* erlaubt es, einer ausgewählten Klasse mehrere
   Lehrer zuzuordnen.

   Nach dem Öffnen des Moduls wird eine Liste von Klassen angezeigt. Nach der
   Auswahl einer Klasse und einem Klick auf *Bearbeiten* wird eine Auswahlliste
   angezeigt, in der Lehrer hinzugefügt oder entfernt werden können.

   Dieses Modul wird üblicherweise nach der Einrichtung neuer Klassen verwendet,
   um ihnen erstmals die entsprechenden Lehrer zuzuordnen.

Klassen zuordnen
   Daneben erlaubt das Modul *Klassen zuordnen*, einen bestimmten Lehrer zu
   mehreren Klassen hinzuzufügen.

   Nach dem Öffnen des Moduls wird eine Liste von Lehrern angezeigt. Nach der
   Auswahl eines Lehrers und einem Klick auf *Bearbeiten* wird eine Auswahlliste
   angezeigt, in der Klassen hinzugefügt oder entfernt werden können.

   Dieses Modul wird üblicherweise nach einem Neuzugang im Kollegium verwendet,
   um den neuen Lehrer seinen Klassen zuzuweisen.

.. _assign-teacher:

.. figure:: /images/assign_teachers_to_class.png
   :alt: Zuweisen von Lehrern zu einer Klasse

   Zuweisen von Lehrern zu einer Klasse

.. _internet-rules:

Internetregeln definieren
=========================

Für die Filterung des Internetzugriffs wird ein sogenannter Proxy eingesetzt. Es
handelt sich dabei um einen Server, der vor jedem Abruf einer Internetseite
prüft, ob der Zugriff auf diese Seite erlaubt ist. Ist das nicht der Fall, wird
eine Informationsseite angezeigt.

Wenn Schüler beispielsweise in einer Schulstunde in der Wikipedia recherchieren
sollen, kann eine Regelliste definiert werden, die Zugriffe auf alle anderen
Internetseiten unterbindet. Diese Regelliste kann dann vom Lehrer zugewiesen
werden.

Wird die Regel für eine Klasse oder Arbeitsgruppe definiert, betrifft dies auch
die in der Klasse enthaltenen Lehrer. Für Lehrer kann ggf. eine Regel mit
höherer Priorität zugewiesen werden.

Mit der Funktion *Internetregeln definieren* können die Regeln verwaltet werden.

In der Grundeinstellung sind schon zwei Regeln vordefiniert: *Kein Internet*
deaktiviert den Internetzugang generell und *Unbeschränkt* erlaubt vollständigen
Zugriff.

.. _fig-internet-rules:

.. figure:: /images/internet_rules_1.png
   :alt: Verwaltung von Internetregeln

   Verwaltung von Internetregeln

Mit *Regel hinzufügen* kann eine neue Filterregel definiert werden. Zuerst ist
ein *Name* einzugeben. Als *Regeltyp* werden zwei Arten von Filterregeln
unterschieden:

Freigabeliste
   Bei einer *Freigabeliste* sind nur vordefinierte Seiten aufrufbar und alle
   anderen Seiten gesperrt.

Sperrliste
   Bei einer *Sperrliste* sind bis auf die gesperrten Seiten alle anderen Seiten
   aufrufbar.

.. _wikipedia-whitelist:

.. figure:: /images/internet_rules_2.png
   :alt: Anlegen einer Whitelist für Wikipedia

   Anlegen einer Whitelist für Wikipedia

Unter *Internet-Domänen* kann eine Liste von Adressen angegeben werden, z.B.
``wikipedia.org`` oder ``facebook.com``. Es wird empfohlen nur den Domänenanteil
einer Adresse anzugeben, also statt ``www.wikipedia.org`` nur ``wikipedia.org``.

Ist die Option *WLAN-Authentifizierung* aktiviert, wird der Klasse oder
Arbeitsgruppe, der die die Regel zugewiesen wird, der Zugriff auf ein ggf.
vorhandenes *Wireless LAN* erlaubt, um beispielsweise mobilen Geräten wie
Laptops den Zugriff auf das Internet zu erlauben.

Regeln können auch mit *Prioritäten* versehen werden. Eine Regel mit höherer
Priorität überschreibt dann die unterliegenden Regeln. Dies ist besonders dann
zu beachten, wenn Benutzer in mehreren Gruppen enthalten sind.
