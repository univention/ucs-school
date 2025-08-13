
.. SPDX-FileCopyrightText: 2021-2025 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _legal-guardians:

****************
Sorgeberechtigte
****************

Dieses Szenario beschreibt den Import von Sorgeberechtigten von Schülern, zum Beispiel Elternteilen.

Sorgeberechtigte werden mit der Benutzerrolle ``legal_guardian`` importiert.
Sie können mit Schülern verknüpft werden.
Die Verknüpfung geschieht entweder am Schüler über das ``legal_guardians``-Attribut
oder am Sorgeberechtigten über das ``legal_wards``-Attribut.

Die Verknüpfung ist bidirektional und wird bei einer Änderung am jeweils assoziierten Objekt automatisch gepflegt:
Das Hinzufügen einer Verknüpfung am Schüler in ``legal_guardians`` fügt automatisch am Sorgeberechtigten
auch eine Verknüpfung in ``legal_wards`` auf den Schüler hinzu.
Dies erfolgt ebenfalls umgekehrt.
Es reicht daher aus, die Verknüpfung nur an einem Rollentyp zu pflegen.

Der |UCSUAS|-Import erwartet in den Attributen jeweils eine Liste der Benutzernamen mit den zu assoziierenden Benutzern.
Die einzelnen Benutzernamen müssen mit einem Komma voneinander getrennt werden.

Die Attribute müssen dabei den entsprechenden CSV-Spalten :ref:`zugeordnet <configuration-mapping>` werden,
um importiert zu werden.

Dabei gelten folgende Einschränkungen:

* Ein Schüler darf mit maximal 4 Sorgeberechtigten verknüpft sein.
* Ein Sorgeberechtigter darf mit maximal 10 Schülern verknüpft sein.
* Die zu verknüpfenden Benutzer müssen bereits existieren.

.. note::

   Die Einschränkung, dass die zu verknüpfenden Benutzer bereits im Verzeichnisdienst importiert sein müssen,
   erfordert ggf. Anpassungen an der Importreihenfolge oder zusätzliche Schritte.
   Wir empfehlen, die Verknüpfung zwischen den Objekten nur an einem von beiden Rollentypen zu setzen.

   Wenn Sie einen Import pro Benutzerrolle durchführen,
   empfehlen wir, Schüler vor den Sorgeberechtigten zu importieren.
   Weiterhin sollte die Verknüpfung zwischen den Benutzerobjekten nur bei den Sorgeberechtigten gesetzt werden (CSV-Spalte plus entsprechendes Mapping).
   Dadurch ist sichergestellt, dass die zu verknüpfenden Schüler-Benutzer bereits im Verzeichnisdienst existieren.

   Falls alle Benutzerrollen in einem einzelnen Importvorgang abgeglichen werden,
   müssen Sie den Import zweimal mit unterschiedlichen Import-Mappings durchführen.
   Im ersten Import darf die CSV-Spalte für die Verknüpfungen nicht im Import-Mapping aufgeführt werden.
   Der erste Importvorgang stellt sicher, dass zunächst alle Benutzerobjekte importiert werden.
   Der zweite Importvorgang erfolgt danach mit entsprechendem Mapping in der Importkonfiguration und passt die Verknüpfungen zwischen Schülern und Sorgeberechtigten entsprechend an.

.. note::

   Wir raten von der gleichzeitigen Verwendung beider Attribute in der Importkonfiguration ab.
   Dies erzeugt zusätzlichen Mehraufwand während des Imports und Sie müssen sicherstellen,
   dass die Attributwerte aufeinander abgestimmt und zueinander konsistent sind.
   Ist ein Elternteil als Sorgeberechtigter bei einem Schüler in ``legal_guardians`` eingetragen,
   so muss beim Elternteil der Schüler auch im ``legal_wards``-Attribut eingetragen sein.

Sollten Ihnen die Benutzernamen der zu assoziierenden Benutzer noch nicht bekannt sein,
weil diese zum Beispiel durch ein :ref:`Schema <configuration-scheme-formatting>` erzeugt werden,
ist ein zusätzlicher :ref:`Import-Hook <extending-hooks>` nötig.
Einen Hook, der es erlaubt, die ``record_uid`` anstelle des Benutzernamens in CSV-Importen zu nutzen,
können Sie wie folgt aktivieren:

.. code-block:: bash

    cp /usr/share/ucs-school-import/pyhooks{-available,}/legal_guardian_as_record_uid.py
