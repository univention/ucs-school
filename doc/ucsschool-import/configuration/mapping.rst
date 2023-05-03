.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration-mapping:

Zuordnung von Eingabedaten zu Benutzerattributen
================================================

Während des Imports aus einer CSV-Datei müssen die Daten einer Zeile den
Attributen des anzulegenden bzw. zu ändernden Benutzerobjekts zugeordnet werden.
Diese Zuordnung geschieht im Konfigurationsobjekt :option:`csv:mapping`.

In ihm stehen Schlüssel-Wert-Paare: CSV-Spalte → Benutzerattribut.

Folgendes Beispiel zeigt, wie der Import von drei Schülern an zwei Schulen
konfiguriert werden kann. Die Schulverwaltungssoftware hat folgendes CSV
produziert (anderes Beispiel :download:`hier zum Download
</user_new_example.csv>`, UTF-16, Tabulator getrennt):

.. code-block::

   "Schulen","Vorname","Nachname","Klassen","Mailadresse","Telefonnumer"
   "schule1,schule2","Anton","Meyer","schule1-1A,schule2-2B","anton@schule.local",""
   "schule1,schule2","Bea","Schmidt","schule1-2B,schule2-1A","bea@schule.local","0421-1234567890"
   "schule2","Daniel","Krause","schule2-1A","daniel@schule.local",""


.. versionadded:: 4.1R2v1

   Schulübergreifende Benutzerkonten wurden mit |UCSUAS|
   4.1R2 eingeführt (siehe `UCS@school 4.1 R2 v1 Release Notes
   <https://docs.software-univention.de/release-notes-ucsschool-4.1R2v1-de.html>`_)
   und werden von der Importsoftware unterstützt.

Als erstes fällt auf, dass ein Schüler an zwei Schulen gleichzeitig
eingeschrieben ist. Entsprechend sind die Namen der Klassen so kodiert, dass sie
eindeutig einer Schule zugeordnet werden können. Anton geht also in die Klasse
``1A`` der Schule ``Schule1`` und in die Klasse ``2B`` der Schule ``Schule2``.

Für die Aufbereitung der Daten ist es besonders wichtig darauf zu achten, dass
Benutzern in der Rolle *Schüler* immer eine Schulklasse zugewiesen ist.
Benutzerkontodaten werden an anderen Stellen weiter verarbeitet. Wenn die Angabe
für die Schulklasse eines Schülers fehlt, kann die Weiterverarbeitung gestört
werden. Detaillierte Informationen wie sich Benutzerkonten |UCSUAS| von UCS
unterschieden, finden sich in :uv:kb:`Knowledge Base Artikel "How a UCS@school user
should look like" <15630>`.

Die Namen der Schulen bzw. Klassen sind ohne Leerzeichen und durch Komma
getrennt aufgelistet. Als Trennzeichen innerhalb einer CSV-Zelle wird das Komma
verwendet, da dies implizit aus der Standardeinstellung
:option:`csv:incell-delimiter:default`\ ``=","`` aus
:file:`/usr/share/ucs-school-import/configs/user_import_defaults.json`
übernommen wurde.

Folgende Konfiguration nutzt implizit die Standardeinstellung
:option:`csv:header_lines`\ ``=1``
:file:`/usr/share/ucs-school-import/configs/user_import_defaults.json` und
verwendet damit die Spaltennamen aus der CSV-Kopfzeile als Schlüssel.

.. code-block:: json

   {
       "csv": {
           "mapping": {
               "Schulen": "schools",
               "Vorname": "firstname",
               "Nachname": "lastname",
               "Klassen": "school_classes",
               "Mailadresse": "email",
               "Telefonnumer": "phone"
           }
       }
   }


Um die Konfiguration zu überprüfen, kann ein Testlauf mit :option:`--dry-run`
gestartet werden. Anschließend steht in
:file:`/var/log/univention/ucs-school-import.log` ein :option:`Protokoll
<logfile>` bereit, das Debug-Ausgaben enthält. Hier findet sich:

.. code-block::

   2016-06-28 17:47:25 INFO  user_import.read_input:81  ------ Starting to read users from input data... ------
   [..]
   2016-06-28 17:47:25 DEBUG base_reader.next:73  Input 3: ['schule1', 'Bea', 'Schmidt', 'schule1-2B,schule2-1A',
   'bea@schule.local', 'Sch\xc3\xbclerin mit Telefon', '0421-1234567890'] -> {u'Schulen': u'schule1',
   u'Vorname': u'Bea', u'Telefonnumer': u'0421-1234567890', u'Nachname': u'Schmidt', u'Klassen': u'schule1-2B,schule2-1A',
   u'Mailadresse': u'bea@schule.local'}


Ab der zweiten Zeile ist dies folgendermaßen zu lesen:

* ``Input 3``: dritte Zeile der Eingabedatei, die Kopfzeile mitgerechnet.

* ``['schule1', 'Bea', 'Schmidt', 'schule1-2B,schule2-1A', 'bea@schule.local',
  '0421-1234567890']``: Die Eingabezeile mit bereits getrennten Spalten.

* ``{u'Schulen': u'schule1', u'Vorname': u'Bea', u'Telefonnumer':
  u'0421-1234567890', u'Nachname': u'Schmidt', u'Klassen':
  u'schule1-2B,schule2-1A', u'Mailadresse': u'bea@schule.local'}``: Die
  Zuordnung von Daten zu den Schlüsseln aus der CSV-Kopfzeile.

Das Einlesen aus der CSV-Datei ist gelungen. Die Daten wurden den Schlüsseln aus
der CSV-Kopfzeile zugeordnet. Da diese in :option:`csv:mapping` verwendet
werden, kann nun weiter unten, beim Anlegen der Benutzer, die Zuordnung der
Daten zu Benutzerattributen beobachtet werden:

.. code-block::

   2016-06-28 17:47:25 INFO  user_import.create_and_modify_users:107  ------ Creating / modifying users... ------
   [..]
   2016-06-28 17:47:25 INFO  user_import.create_and_modify_users:128  Adding ImportStudent(name='B.Schmidt',
   school='schule1', dn='uid=B.Schmidt,cn=schueler,cn=users,ou=schule1,dc=uni,dc=dtr', old_dn=None) (source_uid:NewDB
   record_uid:bea@schule.local) attributes={'$dn$': 'uid=B.Schmidt,cn=schueler,cn=users,ou=schule1,dc=uni,dc=dtr',
   'display_name': 'Bea Schmidt', ``'record_uid'``: u'bea@schule.local', 'firstname': 'Bea',
   'lastname': 'Schmidt', 'type_name': 'Student', 'school': 'schule1', ``'name'``: 'B.Schmidt',
   'disabled': '0', 'email': u'bea@schule.local', 'birthday': None, 'type': 'importStudent', 'schools': ['schule1'],
   'password': 'xxxxxxxxxx', 'source_uid': u'NewDB', ``'school_classes'``: {'schule1': ['schule1-2B'],
   'schule2': ['schule2-1A']}, 'objectType': 'users/user'} ``udm_properties</property>={u@@property@@>'phone'``: [u'0421-1234567890'],
   'overridePWHistory': '1', 'overridePWLength': '1'}...


Hier ist nun zu sehen, dass Daten umgewandelt und Attributen zugeordnet wurden,
sowie dass einige Attribute aus anderen Daten generiert wurden:

* ``school_classes`` ist von einer kommaseparierten Liste zu einer Datenstruktur
  geworden.

* ``name`` und ``record_uid`` sind aus den konfigurierten Schemata
  :option:`scheme:username` und :option:`scheme:record_uid` erzeugt worden.

* ``phone`` wurde in einem ``udm_properties`` genannten Objekt gespeichert.

.. note::

   In ``udm_properties`` werden Daten am Benutzerobjekt gespeichert, die nicht
   zu den Attributen der :ref:`extending-import-user-class`). Die Schlüssel
   entsprechen der Ausgabe des Kommandos:

   .. code-block:: console

      $ udm users/user


Bei der obigen, langen Ausgabe handelt es sich um die Beschreibung eines
:py:class:`ImportUser` Objektes. Dieses zu kennen wird wichtig für die
Programmierung von Hooks (siehe :ref:`extending-hooks`), mit denen vor und nach
dem Anlegen, Ändern oder Löschen von Benutzern noch Aktionen ausgeführt werden
können.

.. _configuration-mapping-specials:

Sonderwerte
-----------

Es existieren *Sonderwerte*, die in der Konfiguration der Zuordnung
(:option:`csv:mapping`) verwendet werden können:

``__action``
   Steht in einer CSV-Spalte immer die auf einen eingelesenen Benutzer
   anzuwendende Aktion als Buchstabe kodiert, so wird die Import-Software keine
   eigene Entscheidung darüber fällen, sondern dieser Anweisung folgen.

   * Anlegen - *add*: ``A``

   * Ändern - *modify*: ``M``

   * Löschen - *delete*: ``D``

``__ignore``
   Der Inhalt dieser Spalte wird ignoriert. Sie kann z.B. verwendet werden, wenn
   die CSV-Datei leere Spalten, oder solche mit nicht zu importierenden Daten,
   enthält.

``__role``
   Der Inhalt dieser Spalte wird verwendet, um die Rolle des Benutzers zu
   bestimmen. Gültige Werte sind:

   * ``student``

   * ``staff``

   * ``teacher``

   * ``teacher_and_staff``

   Wenn die Rolle der zu importierenden Benutzer in einer Spalte angegeben wird,
   darf die Option :option:`user_role` nicht (oder nur auf ``null``) gesetzt
   werden.

.. _configuration-mapping-extending:

Eigene Erweiterungen hinzufügen
-------------------------------

Weitere, eigene Interpretationen von Eingabewerten können in einer von
:py:class:`ucsschool.importer.reader.csv_reader.CsvReader` abgeleiteten Klasse
(siehe :ref:`extending-subclassing`) in der Methode
:py:meth:`~ucsschool.importer.reader.csv_reader.CsvReader.handle_input` erzeugt
werden.

Das folgende Beispiel zeigt eine
:py:meth:`~ucsschool.importer.reader.csv_reader.CsvReader.handle_input` Methode,
die sich in einer von
:py:class:`~ucsschool.importer.reader.csv_reader.CsvReader` abgeleiteten Klasse
befindet. In ihr wird für Schüler der Wert von ``__activate`` in ``disabled``
übersetzt.

.. code-block:: python

   def handle_input(self, mapping_key, mapping_value, csv_value, import_user):
       if mapping_value in ["__is_staff", "__is_teacher"]:
           return True
       if mapping_value == "__activate":
           if csv_value == "0":
               import_user.disabled = "1"
           else:
               import_user.disabled = "0"
           return True
       return super(CustomCsvReader, self).handle_input(
           mapping_key, mapping_value, csv_value, import_user
       )


Um Unterstützung für den Import von anderen Dateiformaten als CSV (JSON, XML
etc) hinzuzufügen, kann von
:py:class:`ucsschool.importer.reader.base_reader.BaseReader` abgeleitet werden
(siehe :ref:`extending-subclassing`).

