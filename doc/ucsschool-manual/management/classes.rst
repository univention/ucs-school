.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-setup-umc-classes:

Verwaltung von Schulklassen
===========================

Auf dem |UCSPRIMARYDN| kann das Anlegen und Entfernen von Schulklassen über das
UMC-Modul *Klassen (Schulen)* erfolgen. Das Anlegen einer Schulklasse ist
erforderlich, bevor das erste Schüler-Benutzerkonto erstellt werden kann.

Die eigentliche Zuordnung von Schülern zu einer Klasse erfolgt über das
UMC-Modul *Benutzer (Schulen)* am Schüler-Benutzerobjekt oder während des
CSV-Imports.

Die Zuordnung von Lehrern zu Klassen erfolgt über das UMC-Modul *Lehrer Klassen
zuordnen*.

.. _school-setup-umc-classes-create:

Anlegen von Schulklassen
------------------------

Im zentralen Suchdialog des UMC-Moduls ist oberhalb der Tabelle die Schaltfläche
:guilabel:`Hinzufügen` auszuwählen, um eine neue Klasse zu erstellen. Sind
mehrere Schulen in der |UCSUAS|-Umgebung eingerichtet, wird zunächst abgefragt,
in welcher Schule die Klasse angelegt werden soll. Wurde nur eine Schule
eingerichtet, wird dieser Schritt automatisch übersprungen.

Anschließend wird für die neue Klasse ein Name sowie eine Beschreibung erfragt.
Sprechende Namen, wie zum Beispiel ``Igel`` oder ``BiologieLK`` sind als Namen
ebenso möglich wie Buchstaben-Ziffern-Kombinationen (``10R``). Aufeinander
folgende Leerzeichen werden nicht unterstützt. Über die Schaltfläche
:guilabel:`Speichern` wird die neue Klasse im Verzeichnisdienst angelegt.

Die Klassennamen in |UCSUAS| müssen schulübergreifend eindeutig sein. Um
trotzdem z.B. die Klasse *7A* in mehreren Schule verwenden zu können, wird dem
Klassennamen im Verzeichnisdienst automatisch das jeweilige Schulkürzel als
Präfix vorangestellt. Für die Klasse *7A* an der Schule mit dem Schulkürzel
``gymmitte`` wird daher das Klassenobjekt ``gymmitte-7A`` erstellt. Dieser Name
mit Präfix zeigt sich z.B. später bei der Administration von Datei- und
Verzeichnisberechtigungen auf Windows-Rechnern.

Um innerhalb einer Klasse den Austausch von Dokumenten zu vereinfachen, wird mit
dem Anlegen einer neuen Klasse auch automatisch eine neue Freigabe erstellt, die
den gleichen Namen trägt, wie das Klassenobjekt (z.B. ``gymmitte-7A``). Die
Freigabe wird auf dem Dateiserver angelegt, welcher an dem Schulobjekt unter
*Erweiterte Einstellungen* als :guilabel:`Server für Klassenfreigaben`
hinterlegt ist. Der Zugriff auf diese Freigabe ist auf die Benutzer der Klasse
beschränkt.

.. _school-setup-umc-classes-modify:

Bearbeiten von Schulklassen
---------------------------

Zum Bearbeiten einer Klasse ist diese in der Tabelle auszuwählen und die
Schaltfläche :guilabel:`Bearbeiten` anzuklicken. Im folgenden
Dialog können Name und Beschreibung der Klasse bearbeitet werden.

.. note::

   Beim Ändern des Namens werden Klassengruppe, Klassenfreigabe und
   Freigabeverzeichnis automatisch umbenannt.

   Gegebenenfalls ist auf Windows-Rechner ein erneutes Anmelden notwendig, um
   wieder Zugriff auf die Freigabe zu erhalten.

Sofern der angemeldete UMC-Benutzer die Rechte für das UMC-Modul *Gruppen* aus
der Modulgruppe *Domäne* besitzt, wird zusätzlich die Schaltfläche *Erweiterte
Einstellungen* angezeigt. Über sie kann das UMC-Modul *Gruppen* geöffnet werden,
in dem viele erweiterte Einstellungen für die Gruppe möglich sind.

.. _school-setup-umc-classes-delete:

Löschen von Schulklassen
------------------------

Zum Löschen von Klassen sind diese in der Tabelle auszuwählen und
anschließend die Schaltfläche :guilabel:`Löschen` anzuklicken.
Nach dem Bestätigen werden die Klassen aus dem Verzeichnisdienst
entfernt.

.. note::

   Mit dem Löschen der Klassen wird auch automatisch die jeweilige
   Klassenfreigabe entfernt.

   In der Standardkonfiguration von |UCSUAS| wird das Freigabeverzeichnis auf
   dem Dateiserver automatisch in das Backup-Verzeichnis
   :file:`/home/backup/groups/` verschoben.
