.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _computer-room:

Computerraum
============

Diese Funktion erlaubt die Kontrolle der Schüler-PCs und des Internetzugangs
während einer Schulstunde. Der Internetzugang kann gesperrt oder freigegeben
werden und es können gezielt einzelne Internetseiten freigegeben werden.

Wenn eine entsprechende Software (Veyon) auf den Schüler-PCs installiert ist,
besteht auch die Möglichkeit diese PCs zu steuern. So kann beispielsweise der
Bildschirm gesperrt werden, so dass in einer Chemie-Stunde die ungeteilte
Aufmerksamkeit auf ein Experiment gelenkt werden kann.

Außerdem kann der Bildschiminhalt eines PCs auf andere Systeme übertragen
werden. Dies erlaubt es Lehrern, auch ohne einen Beamer Präsentationen
durchzuführen.

.. _choose-computer-room:

.. figure:: /images/computerroom_1_select.png
   :alt: Auswahl eines Computerraums

   Auswahl eines Computerraums

Nach einem Klick auf *Computerraum* erscheint eine Auswahlmaske, in der ein
Computerraum ausgewählt werden muss.

Wird ein Computerraum aktuell von einem anderen Lehrer betreut, erscheint ein
Hinweis. Ein Klick auf :guilabel:`Übernehmen` überträgt den Rechnerraum dann an
den gerade angemeldeten Lehrer, wenn z.B. ein anderer Lehrer die zweite Hälfte
einer Doppelstunde betreut.

Es wird nun eine Liste aller PCs in diesem Computerraum angezeigt. Unter *Name*
ist der Name des PCs aufgeführt. Bewegt man die Maus auf einen PC wird
zusätzlich ein Feld angezeigt, das zwei Adressen anzeigt, mit denen der PC im
Schulnetz identifiziert werden kann. Diese Informationen werden ggf. vom
Helpdesk abgefragt, haben aber für die Computerverwaltung keine weitergehende
Bedeutung. Neben jedem PC wird ein Kreis angezeigt. Ist dieser dunkelgrau, ist
auf den PCs die Software *Veyon* installiert (siehe
:ref:`computer-room-veyon`), ist der Kreis hellgrau, fehlt *Veyon* oder der
Rechner ist abgeschaltet. Wird ein orangefarbenes Warndreieck angezeigt, ist das
Computer-Objekt unvollständig.

Ist *Veyon* installiert, wird unter *Benutzer* der Name des gerade angemeldeten
Schülers/Lehrers angezeigt.

Unter *mehr* können die Schüler-PCs über die Option *Computer einschalten* über
das Netzwerk eingeschaltet werden. Die Computer müssen dafür entsprechend
konfiguriert worden sein.

Lehrer können benutzerdefinierte Einstellungen für den Computerraum vornehmen,
die unter *ändern* angepasst werden können. Hier lassen sich u.a. Regeln für den
Internetzugriff auswählen (siehe :ref:`internet-rules` oder eine lokale Liste
erlaubter Webseiten definieren. Mit den Optionen *Freigabezugriff* und
*Druckmodus* kann der Zugriff auf Freigaben und Drucker unterbunden bzw. erlaubt
werden. Die benutzerdefinierten Einschränkungen werden über das Feld *Gültig
bis* zeitlich eingeschränkt.

.. note::

   Falls ein Benutzer am Rechner des Computerraums mit einem lokalen Konto angemeldet ist,
   wird dieser mit ``LOCAL\<Benutzername>`` angezeigt. Benutzer, die auf diese Weise angemeldet
   sind, können z.B. nicht auf Freigaben bzw. Netzwerklaufwerke zugreifen.

.. _computer-room-veyon:

Kontrolle der Schüler-PCs bei Einsatz von Veyon
-----------------------------------------------

Die folgenden Möglichkeiten stehen nur zur Verfügung, wenn auf den Schüler-PCs
die Software *Veyon* installiert ist. Für die Installation der Software kann der
Helpdesk angesprochen werden (siehe :ref:`helpdesk`).

.. _computer-room-image:

.. figure:: /images/computerroom_2_overview.png
   :alt: Beaufsichtigung eines Computerraums

   Beaufsichtigung eines Computerraums

In der Übersichtsliste der Schüler-PCs steht eine Reihe von Aktionen zur
Verfügung. Bewegt man die Maus über die Schaltfläche *Beobachten* eines
Eintrags, erscheint eine verkleinerte Ansicht des aktuellen Schüler-Desktops.
Klickt man auf die Schaltfläche, besteht auch die Möglichkeit diese Ansicht in
größerer Form darzustellen. Die Ansicht des Schüler-Desktops wird fortlaufend
aktualisiert.

Durch Klick auf *Bildschirm sperren* kann die Bildschirmanzeige der
zuvor markierten Schüler-PCs deaktiviert werden. Auf den Schüler-PCs wird dann
nur ein grauer Hintergrund mit einem Schloss-Symbol angezeigt (siehe
:ref:`screenlock`). Ein Klick auf *Bildschirm entsperren* gibt die
ausgewählten Schüler-PCs wieder frei.

.. _screenlock:

.. figure:: /images/school-veyon-lock.png
   :alt: Ein gesperrter Bildschirm

   Ein gesperrter Bildschirm

Unter *mehr* stehen weitere Aktionen zur Verfügung:

*Benutzer abmelden*
   Meldet einen Schüler vom Windows-Desktop ab.

*Computer herunterfahren* und *Computer neu starten*
   Erlauben das Abschalten, bzw. den Neustart eines Schüler-PCs.

*Computer einschalten*
   Ermöglicht das Einschalten von Schüler-PCs über die Weboberfläche. Dieser
   Menüpunkt funktioniert nur, wenn die Hardware der betreffenden Schüler-PCs
   dies unterstützt und zuvor vom Administrator entsprechend eingerichtet wurde.

*Eingabegeräte sperren*
   Deaktiviert Maus und Tastatur auf den Schüler-PCs.

*Präsentation starten*
   Die Option *Präsentation starten* wird in :ref:`computer-room-presentation`
   beschrieben.

.. _computer-room-presentation:

Durchführung von Bildschirmpräsentationen
-----------------------------------------

Diese Funktion steht ebenfalls nur zur Verfügung, wenn auf den Schüler-PCs die
Software *Veyon* installiert ist. Sie erlaubt es, den Bildschirminhalt eines PCs
an alle anderen PCs zu übertragen und dort darzustellen. So können Schüler und
Lehrer Präsentationen ohne die Verwendung eines Beamers durchzuführen.

Wird eine Präsentation durchgeführt, wird auf den PCs des Computerraums, an
denen Schüler angemeldet sind, die Präsentation in Vollbild dargestellt und
Tastatur- und Mauseingaben blockiert. Auf PCs, an denen Lehrer angemeldet sind,
erfolgt die Präsentation in einem separaten Fenster und alle Eingaben sind wie
gewohnt möglich.

.. _praesentation:

.. figure:: /images/computerroom_3_start_presentation.png
   :alt: Start einer Bildschirmpräsentation

   Start einer Bildschirmpräsentation

Eine Präsentation wird wie folgt gestartet: Unter *mehr* muss in der Liste der
Rechner die Option *Präsentation starten* ausgewählt werden. Es erscheint ein
Hinweis, das die Präsentation gestartet wird und nach kurzer Zeit wird die
Ausgabe auf die übrigen PCs übertragen. Der Kreis des sendenden Rechners wird in
rot und für die empfangenden Rechner in grün dargestellt. Ein Klick auf die
Schaltfläche :guilabel:`Präsentation beenden` stoppt die Präsentation.
