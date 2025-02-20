.. SPDX-FileCopyrightText: 2024-2025 Univention GmbH
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

.. envvar:: ucsschool/import/lusd/skip_students

   Wenn diese Variable auf ``yes`` gesetzt ist, werden keine Schülerdaten heruntergeladen und importiert.

.. envvar:: ucsschool/import/lusd/skip_teachers

   Wenn diese Variable auf ``yes`` gesetzt ist, werden keine Lehrerdaten heruntergeladen und importiert.

.. envvar:: ucsschool/import/lusd/school_authority

   Name des Schulträgers, der für die Schulen verantwortlich ist.
   Der Schulträger wird benötigt, um Fehler bei der Eingabe Dienststellennummer zu erkennen.
   Es werden nur Dienststellennummern vom Import akzeptiert, die dem Schulträger zugeordnet sind.

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
Optionen auf der Kommandozeile überschreiben Einstellungen in UCR.

.. option:: dry-run

   Diese Einstellung wird direkt an die |UCSUAS| Importsoftware weitergegeben und bestimmt, ob ein ``dry-run`` ausgeführt
   werden soll oder nicht.
   Mehr Informationen zum ``dry-run`` entnehmen Sie dem Abschnitt :ref:`configuration` entnehmen.
   Erlaubte Werte sind: ``true`` und ``false`` mit dem Standardwert ``false``.

.. option:: skip-fetch

   Diese Einstellung dient Software-Entwicklern zum Testen der LUSD Import Software.
   Erlaubte Werte sind ``true`` und ``false``.
   Der Standardwert ist ``false``.
   Bei dem Wert ``true`` ruft der LUSD Import **keine Daten** ab,
   sondern arbeitet mit den bereits vorhandenen Daten.
   Belassen oder setzen Sie den Wert im allgemeinen Betrieb auf ``false``.

.. option:: log-level

   Bestimmt das Log Level für die Log Einträge, die dieser Import generiert. Erlaubte Werte sind:
   ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR`` und ``CRITICAL`` mit dem Standardwert ``INFO``.

.. option:: skip-students

   Ist diese Option gesetzt, werden keine Schülerdaten importiert.

.. option:: skip-teachers

   Ist diese Option gesetzt, werden keine Lehrerdaten importiert.

.. _lusd-import-config:

Importkonfiguration
-------------------

Der LUSD Import verwendet spezielle Konfigurationsdateien.
Diese befinden sich im Ordner :file:`/usr/share/ucs-school-import-lusd/import-config/`.

Dabei werden die folgenden Werte aus der LUSD Datenbank standardmässig nach |UCSUAS| übernommen:

``personalUID``
   wird für Lehrkräfte als ``record_uid`` verwendet.
   Bitte beachten Sie, dass die ``personalUID`` für eine Lehrkraft
   für jede Schule unterschiedlich ist.
   Das bedeutet, dass eine Lehrkraft für jede Schule in der sie sich befindet
   ein eigenes Benutzerkonto bekommt.

``schuelerUID``
   wird für Schüler als ``record_uid`` verwendet.

``vorname``
   wird für Lehrkräfte als ``firstname`` verwendet.

``nachname``
   wird für Lehrkräfte als ``lastname`` verwendet.

``schuelerVorname``
   wird für Schüler als ``firstname`` verwendet.

``schuelerNachname``
   wird für Schüler als ``lastname`` verwendet.

``klassenname``
   wird für Schüler als ``school_classes`` verwendet.

``klassenlehrerKlassen`` und ``klassenlehrerVertreterKlassen``
   wird für Lehrkräfte als ``school_classes`` verwendet.

.. _lusd-class-level:

Semesterstufen
==============

Die LUSD Datenbank exportiert Informationen zu den Semesterstufen von Schülern.
Diese Informationen können vor allem für externe Dienste nützlich sein,
die auf ein |UCSUAS| LDAP zugreifen.

In vielen Fällen ist es ausreichend, ein Mapping des LUSD Attributes ``stufeSemester``
auf ein erweitertes Attribut in |UCSUAS| einzurichten,
wie im Abschnitt :ref:`configuration-mapping` beschrieben.

.. note::

   Die Erstellung eines erweiterten Attributes für das Speichern der Semesterstufe
   können Sie im Abschnitt zu :external+uv-manual:ref:`central-extended-attrs`
   im UCS Handbuch nachlesen.

Sollten Sie die Semesterstufen in einem anderen Format benötigen,
als es die LUSD Datenbank anbietet,
können Sie einen Hook verwenden,
den das Paket :program:`ucs-school-import-lusd` mitbringt.
Dieser Hook wird als :file:`/usr/share/ucs-school-import-lusd/hooks/lusd_class_level_hook.py` abgelegt.
Die Verwendung von Hooks können Sie im Abschnitt :ref:`extending-hooks` nachlesen.

Um diesen Hook zu aktivieren,
verwenden Sie den Befehl in :numref:`lusd-class-level-activate-hook-listing`
und führen ihn auf dem |UCSUAS| System aus:

.. code-block:: console
   :caption: Hook aktivieren
   :name: lusd-class-level-activate-hook-listing

    $ ln -s /usr/share/ucs-school-import-lusd/hooks/lusd_class_level_hook.py \
         /usr/share/ucs-school-import/pyhooks/

Dabei wird die transformierte Semesterstufe in ein erweitertes Attribut mit dem Namen ``class_level`` geschrieben.

.. note::

   Der Hook ist eine generelle Implementierung
   und kann gegebenenfalls von Ihren Anforderungen abweichen.
   Wenn dies der Fall ist,
   kopieren Sie den Hook und passen ihn Ihren Anforderungen entsprechend an.
   Dazu ist die Anpassung der Felder ``UDM_CLASS_LEVEL_ATTRIBUTE``
   und ``REGEX_PATTERNS`` erforderlich.
   Ihre Funktionsweise und Hinweise zur Anpassung
   entnehmen Sie der Dokumentation im Quellcode.

.. _lusd-troubleshooting:

Fehlerbehandlung
================

Falls es bei dem LUSD Import zu Problemen kommt,
finden Sie in diesem Abschnitt einige Möglichkeiten,
mit denen Sie eventuell ein Problem selbst lösen können.

.. important::

   Konsultieren Sie immer zuerst die Log Datei, um potentielle Probleme zu identifizieren.
   Die Datei mit den Log-Einträgen lautet :file:`/var/log/univention/ucs-school-import-lusd.log`.

Migration existierender Nutzerdaten zum LUSD Import
---------------------------------------------------

Dieser Abschnitt beschreibt,
wie Sie eine Schule mit bereits existierenden Nutzerdaten
für die Umstellung auf den LUSD Import vorbereiten müssen.

Wollen Sie den LUSD Import für eine Schule einsetzen,
für die schon Daten im LDAP existieren,
müssen Sie vor dem ersten Import dafür sorgen,
dass der Import die Daten aus der LUSD Datenbank korrekt
den schon existierenden Benutzerkonten für Schüler und Lehrkräfte zuweist.
Ansonsten werden die existierenden Benutzerkonten gelöscht und dann neu angelegt.

Da es sich bei dem LUSD Import um einen |UCSUAS| Import handelt,
werden Nutzer über die Kombination der Werte von ``source_uid`` und ``record_uid`` identifiziert.
Diese beiden Werte müssen in den existierenden Daten so angepasst werden,
dass sie für die jeweiligen Nutzer mit den Daten aus dem LUSD Import übereinstimmen.

Die ``source_uid`` wird über die Konfigurationsdatei definiert
und für den LUSD Import standardmässig auf ``LUSD_JSON_API`` gesetzt.
Sie können entweder die ``source_uid`` bei allen existierenden Nutzern der Schule auf den Wert ``LUSD_JSON_API`` setzen
oder Sie passen die Konfiguration des LUSD Imports so an,
dass Ihre existierende ``source_uid`` verwendet wird.

Die ``record_uid`` wird beim LUSD Import direkt aus der Datenbank bezogen.
Jeder Schüler und jede Lehrkraft besitzen eine ``dienststellennummer``,
die als ``record_uid`` verwendet wird.
Um die Nutzer der Schule korrekt zu migrieren,
müssen Sie für jedes Benutzerkonto eines Schülers und jeder Lehrkraft im LDAP die dazugehörige Dienststellennummer einmalig in Erfahrung bringen
und als die neue ``record_uid`` im LDAP eintragen.
Ein entsprechender Mechanismus zur Zuordnung der existierenden Daten zu Dienststellennummern kann nicht automatisch vom LUSD Import durchgeführt werden.
Sie müssen eine geeignete Strategie entwickeln, die auf Ihre Datenstruktur Anwendung findet.

Wenn Sie beide Werte bei den existierenden Nutzern angepasst haben,
kann der LUSD Import gestartet werden und existierende Nutzer werden korrekt aktualisiert.

.. note::

   Aufgrund der unterschiedlichen und teils sehr spezifischen Handhabung der ``record_uid`` an den verschiedenen Schulen,
   kann die Dokumentation an dieser Stelle kein allgemein hilfreiches Beispiel anbieten.
