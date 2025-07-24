.. SPDX-FileCopyrightText: 2021-2025 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _legal-guardians:

*********************
Gesetzliche Vertreter
*********************

Dieses Szenario beschreibt den Import von gesetzlichen Vertretern, zum Beispiel Eltern,
von Schülern.

Gesetzliche Vertreter werden mit Rolle ``legal_guardian`` importiert.
Sie können mit Schülern verknüpft werden.
Dies geschieht entweder am Schüler über das ``legal_guardians`` Attribut
oder am gesetzlichen Vertreter über das ``legal_wards`` Attribut.

.. note::

   Bei der Verwendung beider Attribute müssen Sie sicherstellen das diese aufeinander abgestimmt sind.
   Ist ein Elternteil als gesetzlicher Vertreter bei einem Schüler in ``legal_guardians`` eingetragen,
   so muss beim Elternteil der Schüler auch im ``legal_wards`` Attribut eingetragen sein.

Die Attribute müssen dabei den entsprechenden CSV-Spalten :ref:`zugeordnet <configuration-mapping>` werden,
um importiert zu werden.

Der |UCSUAS| Import erwartet als Attribut die Benutzernamen der zu assoziierenden Benutzern, mit Komma getrennt.

Dabei gelten folgende Einschränkungen:

* Ein Schüler darf mit maximal 4 gesetzlichen Vertretern verknüpft sein.
* Ein gesetzlicher Vertreter darf mit maximal 10 Schülern verknüpft sein.
* Die zu verknüpfenden Benutzer müssen bereits existieren.

Um sicherzustellen das die Benutzer bereits existieren, kann es nötig sein mehrere Imports durchzuführen.

Sollten Ihnen die Benutzernamen der zu assoziierenden Benutzern noch nicht bekannt sein,
weil diese zum Beispiel durch ein :ref:`Schema <configuration-scheme-formatting>` erzeugt werden,
ist ein :ref:`Hook <extending-hooks>` nötig.
Einen Hook der es erlaubt die ``record_uid`` anstelle des Benutzernamens in CSV Importen zu nutzen,
können Sie wie folgt aktivieren:

.. code-block:: bash

    cp /usr/share/ucs-school-import/pyhooks{-available,}/legal_guardian_as_record_uid.py
