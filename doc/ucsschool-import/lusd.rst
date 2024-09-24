.. SPDX-FileCopyrightText: 2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _lusd-import:

***********
LUSD Import
***********

Dieses Kapitel richtet sich an Administratoren, die Benutzerdaten aus der zentralen Datenbank für Lehrer und Schüler
des hessischen Kultusministeriums importieren wollen.

|UCSUAS| beinhaltet optionale Komponenten für die Importsoftware,
mit der sich ein automatischer und periodischer Import von Benutzerdaten aus
LUSD nach |UCSUAS| einrichten lässt.

.. seealso::

   `LUSD - Lehrer- und Schülerdatenbank | Digitale Schule Hessen <https://digitale-schule.hessen.de/digitale-infrastruktur-und-verwaltung/lehrer-und-schuelerdatenbank-lusd>`_
      für Informationen zur Lehrer- und Schülerdatenbank in Hessen.

.. _lusd-installation:

Installation
============

Die Komponenten für den LUSD Import werden über das Paket :program:`ucs-school-import-lusd`
auf einem UCS Primary oder Backup Directory Node installiert.

Auf der Kommandozeile installieren Sie das Paket mit dem folgenden Befehl:

.. code-block:: console

   $ univention-install ucs-school-import-lusd
   $ mkdir -p /var/lib/ucs-school-import-lusd/

Um Daten aus LUSD abrufen zu können, muss sich das System beim hessischen Kultusministerium authentifizieren.
Dazu ist ein privater Schlüssel erforderlich, den Sie als Datei :file:`/var/lib/ucs-school-import-lusd/auth_key` im UCS-System
ablegen müssen.

.. important::

   Um den privaten Schlüssel zu erhalten, wenden Sie sich bitte an Ihre Kontaktperson bei Univention.

Sie müssen den Schlüssel manuell auf das |UCSUAS| System kopieren.
Stellen Sie außerdem mit folgendem Befehl sicher, dass die Datei nur von dem Benutzer ``root`` ausgelesen werden kann.

.. code-block:: console

   $ chown root:root /var/lib/ucs-school-import-lusd/auth_key
   $ chmod 600 /var/lib/ucs-school-import-lusd/auth_key

.. _lusd-usage:

Verwendung
==========

Das Paket :program:`ucs-school-import-lusd` erstellt während der Installation einen Cron Job, der den LUSD Import täglich ausführt.
Der Name des Jobs lautet ``LUSD_import``.
Der Cron Job wird dabei durch UCR Variablen konfiguriert, wie im
:external+uv-manual:ref:`UCS Handbuch <computers-defining-cron-jobs-in-univention-configuration-registry>`
beschrieben.

Für den Cron Job wählt das Paket :program:`ucs-school-import-lusd` einen zufälligen Zeitpunkt innerhalb des Betriebszeitraumes der LUSD Schnittstelle.
Die LUSD Schnittstelle stellt ihre Daten nur während des Betriebszeitraum von 06:00 bis 22:00 Mitteleuropäische Zeit zur Verfügung.

.. warning::

   Der Cron Job lässt sich beliebig anpassen und auf eine andere Zeit verlegen.
   Beachten Sie dabei,
   dass die LUSD Schnittstelle nur während des Betriebszeitraums zur Verfügung steht.

Der Cron Job führ das Skript :file:`/usr/share/ucs-school-import-lusd/scripts/lusd_import` aus.
Als Administrator können Sie das Skript auch manuell starten, um einen LUSD Import durchzuführen:

.. code-block:: console

    $ /usr/share/ucs-school-import-lusd/scripts/lusd_import

Dabei lädt das Skript die Daten für alle konfigurierten Schulen herunter und importiert diese über die |UCSUAS|
Importsoftware.
Die Parameter, die das Skript akzeptiert, erläutert der Abschnitt :ref:`lusd-configuration-parameters`.

Der Abschnitt :ref:`lusd-configuration` erläutert die Konfiguration von Schulen für den LUSD Import.

Der LUSD Import verwendet zwar ein eigenes Skript, um die benötigten Daten vor dem Import herunterzuladen,
ist aber ansonsten ein ganz normaler SiSoPi |UCSUAS| Import.
LUSD Import verwendet daher alle Hooks, die für den Import konfiguriert worden sind.

.. note::

   Die LUSD Datenbank verlangt nicht, dass sich Schüler in einer Schulklasse befinden müssen.
   Da dies allerdings im Datenmodell von |UCSUAS| vorgesehen ist, werden alle Schüler ohne Schulklasse
   automatisch in eine Klasse mit dem Namen ``lusd_noclass`` eingetragen.

Es gilt allerdings zu beachten, dass der LUSD Import spezielle Konfigurationsdateien verwendet.
Diese befinden sich im Ordner :file:`/usr/share/ucs-school-import-lusd/import-config/`.
Sollten die dort hinterlegten Einstellungen nicht den Anforderungen Ihrer Umgebung entsprechen, können neue Konfigurationen
von diesen abgeleitet werden.
Im Abschnitt :ref:`lusd-configuration` ist beschrieben, wie sich andere Konfigurationsdateien für den LUSD Import
nutzen lassen.

.. _lusd-usage-logging:

Logging
-------

Die Logs für den LUSD Import befinden sich in der Datei :file:`/var/log/univention/ucs-school-import-lusd.log`.
Diese Datei enthält die Log Einträge des Kommandozeilenprogramms :program:`lusd_import`.

Da es sich letztlich um einen normalen |UCSUAS| Import handelt, findet man zusätzliche Informationen in den |UCSUAS|
Import Logs.

Wenn Sie als Administrator das Log Level auf ``DEBUG`` setzen,
fügt das LUSD Kommandozeilenprogramm zusätzlich das gesamte Log des |UCSUAS| Import Prozesses der Log Datei
des LUSD Kommandozeilenprogramms hinzu.

.. _lusd-configuration:

Konfiguration
=============

Der LUSD Import wird über UCR konfiguriert. Folgende Variablen sind verfügbar:

.. envvar:: ucsschool/import/lusd/log_level

   Bestimmt das Log Level für die Log Einträge, die dieser Import generiert. Erlaubte Werte sind:
   ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR`` und ``CRITICAL`` mit dem Standardwert ``INFO``.

.. envvar:: ucsschool/import/lusd/student_import_config_path

   Bestimmt den Dateipfad zu der Konfigurationsdatei für den Import von Schülern.
   Dabei handelt es sich um eine normale Konfigurationsdatei des Imports, wie sie im
   Abschnitt :ref:`configuration` beschrieben ist. Der Standardwert ist
   :file:`/usr/share/ucs-school-import-lusd/import-config/user_import_lusd_student.json`.
   Überschreiben Sie diese Einstellung nur,
   wenn der Import von Schülerkonten eine von der Standardkonfiguration abweichende Konfiguration verwenden soll.

.. envvar:: ucsschool/import/lusd/teacher_import_config_path

   Bestimmt den Dateipfad zu der Konfigurationsdatei für den Import von Lehrkräften.
   Dabei handelt es sich um eine normale Konfigurationsdatei des Imports, wie sie im
   Abschnitt :ref:`configuration` beschrieben ist. Der Standardwert ist
   :file:`/usr/share/ucs-school-import-lusd/import-config/user_import_lusd_teacher.json`.
   Überschreiben Sie diese Einstellung nur,
   wenn der Import von Lehrerkonten eine von der Standardkonfiguration abweichende Konfiguration verwenden soll.

.. envvar:: ucsschool/import/lusd/schools/.*

   Damit die Daten einer Schule importiert werden können,
   müssen Sie als Administrator diese erst für den LUSD Import konfigurieren.
   Da die Möglichkeit besteht, dass Schulen in der zentralen Datenbank für Lehrer und Schüler
   des hessischen Kultusministeriums eine andere Bezeichnung haben als in |UCSUAS|,
   müssen Sie die Beziehung zwischen Schulen in |UCSUAS| und dem LUSD explizit herstellen.

   Dafür müssen Sie für jede Schule, für die der LUSD Import Daten importieren soll,
   eine UCR Variable in der Form
   ``ucsschool/import/lusd/schools/SCHULKUERZEL=DIENSTSTELLENNUMMER_IN_LUSD`` erstellen.

.. _lusd-configuration-parameters:

Kommandozeilenparameter
-----------------------

Neben den UCR Variablen bietet das Skript :file:`/usr/share/ucs-school-import-lusd/scripts/lusd_import`
noch einige Optionen, die Sie beim direkten Aufruf einstellen können.

.. option:: dry_run

   Diese Einstellung wird direkt an die |UCSUAS| Importsoftware weitergegeben und bestimmt, ob ein ``dry-run`` ausgeführt
   werden soll oder nicht.
   Mehr Informationen zum ``dry-run`` entnehmen Sie dem Abschnitt :ref:`configuration` entnehmen.
   Erlaubte Werte sind: ``true`` und ``false`` mit dem Standardwert ``false``.

.. option:: skip_fetch

   Diese Einstellung dient Software-Entwicklern zum Testen der LUSD Import Software.
   Erlaubte Werte sind ``true`` und ``false``.
   Der Standardwert ist ``false``.
   Bei dem Wert ``true`` ruft der LUSD Import **keine Daten** ab,
   sondern arbeitet mit den bereits vorhandenen Daten.
   Belassen oder setzen Sie den Wert im allgemeinen Betrieb auf ``false``.

.. option:: log_level

   Bestimmt das Log Level für die Log Einträge, die dieser Import generiert. Erlaubte Werte sind:
   ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR`` und ``CRITICAL`` mit dem Standardwert ``INFO``.

.. _lusd-troubleshooting:

Fehlerbehandlung
================

Falls es bei dem LUSD Import zu Problemen kommt,
finden Sie in diesem Abschnitt einige Möglichkeiten,
mit denen Sie eventuell ein Problem selbst lösen können.

.. important::

   Konsultieren Sie immer zuerst die Log Datei, um potentielle Probleme zu identifizieren.
   Die Datei mit den Log-Einträgen lautet :file:`/var/log/univention/ucs-school-import-lusd.log`.

..
   TODO: Add troubleshooting scenarios


