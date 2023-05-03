.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _sisopi:

****************************************
Szenario: Eine Quelle, partielle Importe
****************************************

Das Szenario wird auch *single source, parial import - SiSoPi* genannt.


.. versionadded:: 4.3v5

   Seit |UCSUAS| 4.3 v5 wird ein Szenario unterstützt, in dem es eine
   Quelldatenbank mit den Mitgliedern aller Schulen gibt, bei dem aber nicht
   zentral, sondern an allen Schulen einzeln importiert wird.

Der Import ist sowohl über die Kommandozeile als auch mit dem UMC-Modul, welches
im Hintergrund die Import-HTTP-API verwendet, möglich.

.. _features:

Features
========

* OU übergreifende Benutzerkonten (ein Benutzer kann in mehreren Schulen sein)

* Jede Schule kann ihre Benutzer einzeln und zu einem beliebigen Zeitpunkt
  importieren.

.. _requirements:

Voraussetzungen
===============

* Eine Datenbasis, die alle Benutzer mit je einem domänenweit eindeutigen
  Schlüssel (``record_uid``), enthält.

* Die Quelldatenbank exportiert separate CSV Dateien pro Schule und
  Benutzerrolle.

* Die Importe können in zufälliger Reihenfolge stattfinden. Es ist möglich, dass
  beim Verschieben eines Benutzers dieser zuerst in einer Schule gelöscht und in
  einer anderen Schule später angelegt wird. Das Benutzerkonto darf in der
  Zwischenzeit nicht gelöscht werden.

.. _implementation:

Implementierung
===============

Um das Verschieben eines Benutzers von Schule *A* nach Schule *B* in zwei Schritten
zu ermöglichen - einschließlich der Möglichkeit, dass der Benutzer zuerst in
Schule *A* gelöscht und später in Schule *B* angelegt wird - wird eine temporäre
Schule verwendet: die sogenannte ``limbo_ou``. Es handelt sich dabei um eine
gewöhnliche Schule (``OU``), deren Name konfigurierbar ist (Standard ist
``limbo``).

Benutzerkonten, die von ihrer letzten oder einzigen Schule (*A*) entfernt
wurden, werden

#. sofort deaktiviert und

#. in die temporäre Schule (``limbo_ou``) verschoben.

Soll ein Benutzer während eines Imports (an Schule *B*) erstellt werden,
existiert jedoch bereits ein Konto mit dessen ``record_uid`` in der *limbo OU*,
so wird dieses Konto stattdessen von dort zur Schule "B" verschoben und das
Konto reaktiviert.

.. _install-and-config:

Installation und Konfiguration
==============================

Der Inhalt von
:file:`/usr/share/ucs-school-import/configs/user_import_sisopi.json` muss der
Importkonfiguration (in
:file:`/var/lib/ucs-school-import/configs/user_import.json`) hinzugefügt werden.

Folgende Einstellungen sollten angepasst werden:

* ``deletion_grace_period:deactivation`` **muss** ``0`` sein.

* ``deletion_grace_period:deletion`` sollte (deutlich) größer als ``0`` sein. Es
  sollte die maximale Anzahl an Tagen sein, die ein Import von zwei Schulen
  auseinander liegen kann. Das ist die Zeit, die ein Konto in der *limbo OU*
  verbringt, bevor es endgültig gelöscht wird.

Der Name der *limbo OU* kann mit der Einstellung ``limbo_ou`` gesetzt werden.

Darüber hinaus muss die |UCSUCR|-Variable
:envvar:`ucsschool/import/http_api/set_source_uid` auf ``no`` gesetzt und der
Import-HTTP-API-Server neu gestartet werden:

.. code-block:: console

   $ ucr set ucsschool/import/http_api/set_source_uid=no
   $ service ucs-school-import-http-api restart


.. _example:

Beispielaufbau
==============

Für den Testaufbau werden zunächst zwei reguläre und die temporäre
Schule erstellt:

.. code-block:: console

   $ /usr/share/ucs-school-import/scripts/create_ou schuleA
   $ /usr/share/ucs-school-import/scripts/create_ou schuleB
   $ /usr/share/ucs-school-import/scripts/create_ou limbo


Nach dem Sichern der ursprünglichen Konfiguration wird die
*SiSoPi*-Konfiguration aktiviert. Üblicherweise wird die neue Konfiguration
anschließend an die individuellen Erfordernisse angepasst. Für den Testaufbau
wurden ``csv``, ``scheme`` und ``source_uid`` hinzugefügt.

.. code-block:: console

   $ cp -v /var/lib/ucs-school-import/configs/user_import.json{,.bak}
   $ cp -v /usr/share/ucs-school-import/configs/user_import_sisopi.json /var/lib/ucs-school-import/configs/user_import.json
   $ $EDITOR /var/lib/ucs-school-import/configs/user_import.json


.. tip::

   Mit folgendem Befehl kann die syntaktische Korrektheit der JSON-Datei geprüft
   werden. Wenn die Datei syntaktisch korrekt ist, wird ihr Inhalt ausgegeben,
   bei einem Fehler wird stattdessen dieser angezeigt.

.. code-block:: console

   $ cat /var/lib/ucs-school-import/configs/user_import.json | python3 -m json.tool
   {
       "classes": {
           "user_importer": "ucsschool.importer.mass_import.sisopi_user_import.SingleSourcePartialUserImport"
       },
       "configuration_checks": [
           "defaults",
           "sisopi"
       ],
       "csv": {
           "mapping": {
               "Beschreibung": "description",
               "EMail": "email",
               "Klassen": "school_classes",
               "Nachname": "lastname",
               "Schule": "school",
               "Telefon": "phone",
               "Vorname": "firstname"
           }
       },
       "deletion_grace_period": {
           "deactivation": 0,
           "deletion": 90
       },
       "limbo_ou": "limbo",
       "scheme": {
           "record_uid": "<firstname>.<lastname>",
           "username": {
               "default": "<:umlauts><firstname>.<lastname><:lower>[COUNTER2]"
           }
       },
       "source_uid": "Test"
   }


.. code-block:: console

   $ ucr set ucsschool/import/http_api/set_source_uid=no
   $ service ucs-school-import-http-api restart


Nun wird für jede Schule eine zu importierende CSV Datei erzeugt:

.. code-block:: console

   $ /usr/share/ucs-school-import/scripts/ucs-school-testuser-import \
     --csvfile test_users_A-1.csv \
     --nostart \
     --httpapi \
     --teachers 4 \
     --classes 1 \
     --inclasses 1 \
     --schools 1 \
     --verbose \
     schuleA
   $ /usr/share/ucs-school-import/scripts/ucs-school-testuser-import \
     --csvfile test_users_B-1.csv \
     --nostart \
     --httpapi \
     --teachers 4 \
     --classes 1 \
     --inclasses 1 \
     --schools 1 \
     --verbose \
     schuleB


.. code-block:: console

   $ cat test_users_A-1.csv

   "Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"
   "schuleA","Yola","Lenz","1a","A teacher.","+74-686-445678",""
   "schuleA","Iphigenie","Lemgo","1a","A teacher.","+63-727-768248",""
   "schuleA","Felix","Adams","1a","A teacher.","+15-263-530094",""
   "schuleA","Radomila","Meygger","1a","A teacher.","+11-364-599925",""


.. code-block:: console

   $ cat test_users_B-1.csv

   "Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"
   "schuleB","Stan","Kinker","1a","A teacher.","+91-299-143803",""
   "schuleB","Jonathan","Heuelmann","1a","A teacher.","+74-656-351455",""
   "schuleB","Ingward","Bohnenkämper","1a","A teacher.","+24-351-217608",""
   "schuleB","Vincent","Störtländer","1a","A teacher.","+67-303-103581",""


Der Import würde regulär über das UMC-Modul statt finden, wird für diesen Test
aber an der Kommandozeile durchgeführt. Beim Import an den beiden Schulen werden
je vier Lehrer angelegt:

.. code-block:: console

   $ /usr/share/ucs-school-import/scripts/ucs-school-user-import \
     --verbose \
     --user_role teacher \
     --infile test_users_A-1.csv \
     --school \
     schuleA

   ------ User import statistics ------
   Read users from input data: 4
   Created ImportTeacher: 4
     ['yola.lenz', 'iphigenie.lemgo', 'felix.adams', 'radomila.meygger']
   Modified ImportTeacher: 0
   Deleted ImportTeacher: 0
   Errors: 0
   ------ End of user import statistics ------

   $ /usr/share/ucs-school-import/scripts/ucs-school-user-import \
     --verbose \
     --user_role teacher \
     --infile test_users_B-1.csv \
     --school \
     schuleB

   ------ User import statistics ------
   Read users from input data: 4
   Created ImportTeacher: 4
     ['stan.kinker', 'jonathan.heuelman', 'ingward.bohnenkae', 'vincent.stoertlae']
   Modified ImportTeacher: 0
   Deleted ImportTeacher: 0
   Errors: 0
   ------ End of user import statistics ------


Nun soll ``yola.lenz`` von ``schuleA`` nach ``schuleB`` verschoben werden. Dazu
wird eine CSV Datei :file:`test_users_A-2.csv` ohne die Zeile mit
``"Yola","Lenz"`` aus :file:`test_users_A-1.csv` erzeugt, sowie eben diese Zeile
in :file:`test_users_B-2.csv` eingefügt. Dort muss ``schuleA`` noch durch
``schuleB`` ersetzt werden. Die neuen Dateien sehen wie folgt aus:

.. code-block:: console

   $ cat test_users_A-2.csv

   "Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"
   "schuleA","Iphigenie","Lemgo","1a","A teacher.","+63-727-768248",""
   "schuleA","Felix","Adams","1a","A teacher.","+15-263-530094",""
   "schuleA","Radomila","Meygger","1a","A teacher.","+11-364-599925",""


.. code-block:: console

   $ cat test_users_B-2.csv

   "Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"
   "schuleB","Stan","Kinker","1a","A teacher.","+91-299-143803",""
   "schuleB","Jonathan","Heuelmann","1a","A teacher.","+74-656-351455",""
   "schuleB","Ingward","Bohnenkämper","1a","A teacher.","+24-351-217608",""
   "schuleB","Vincent","Störtländer","1a","A teacher.","+67-303-103581",""
   "schuleB","Yola","Lenz","1a","A teacher.","+74-686-445678",""


Beim Import an ``schuleA`` wird ``yola.lenz`` scheinbar gelöscht. Tatsächlich
wird sie aber in die Schule ``limbo`` verschoben:

.. code-block:: console

   $ udm users/user list --filter uid=yola.lenz | egrep 'DN|school:'
   DN: uid=yola.lenz,cn=lehrer,cn=users,ou=schuleA,<base dn>
     school: schuleA

   $ /usr/share/ucs-school-import/scripts/ucs-school-user-import \
     --verbose \
     --user_role teacher \
     --infile test_users_A-2.csv \
     --school \
     schuleA

   [..]
   ------ Deleting 1 users... ------
   Removing ImportTeacher(name='yola.lenz', school='schuleA', dn='uid=yola.lenz,cn=lehrer,cn=users,ou=schuleA,<base dn>') from school 'schuleA'...
   Moving ImportTeacher(name='yola.lenz', school='schuleA', dn='uid=yola.lenz,cn=lehrer,cn=users,ou=schuleA,<base dn>') to limbo school u'limbo'.
   [..]

   ------ User import statistics ------
   Read users from input data: 3
   Modified ImportTeacher: 3
     ['iphigenie.lemgo', 'felix.adams', 'radomila.meygger']
   Deleted ImportTeacher: 1
     ['yola.lenz']
   Modified ImportTeacher: 0
   Deleted ImportTeacher: 0
   Errors: 0
   ------ End of user import statistics ------

   $ udm users/user list --filter uid=yola.lenz | egrep 'DN|school:'
   DN: uid=yola.lenz,cn=lehrer,cn=users,ou=limbo,<base dn>
     school: limbo


Beim Import an ``schuleB`` wird ``yola.lenz`` aus der Schule ``limbo`` dort hin
verschoben:

.. code-block:: console

   $ /usr/share/ucs-school-import/scripts/ucs-school-user-import \
     --verbose \
     --user_role teacher \
     --infile test_users_B-2.csv \
     --school \
     schuleB

   [..]
   User ImportTeacher(name='yola.lenz', school='limbo', dn='uid=yola.lenz,cn=lehrer,cn=users,ou=limbo,<base dn>') is in limbo school u'limbo', moving to 'schuleB'.
   Reactivating ImportTeacher(name=None, school='schuleB', dn=None)...
   User will change school. Previous school: 'limbo', new school: 'schuleB'.
   Moving ImportTeacher(name='yola.lenz', school='limbo', dn='uid=yola.lenz,cn=lehrer,cn=users,ou=limbo,<base dn>') from school 'limbo' to 'schuleB'...
   [..]

   ------ User import statistics ------
   Read users from input data: 5
   Modified ImportTeacher: 5
     ['stan.kinker', 'jonathan.heuelman', 'ingward.bohnenkae', 'vincent.stoertlae']
     ['yola.lenz']
   Modified ImportTeacher: 0
   Deleted ImportTeacher: 0
   Errors: 0
   ------ End of user import statistics ------

   $ udm users/user list --filter uid=yola.lenz | egrep 'DN|school:'
   DN: uid=yola.lenz,cn=lehrer,cn=users,ou=schuleB,<base dn>
     school: schuleB


Der umgekehrte Fall, in dem ein zu verschiebender Benutzer an der Zielschule
importiert wird, bevor er an der ursprünglichen Schule gelöscht wird, kann z.B.
folgendermaßen erzeugt werden: Die Zeile von ``"Iphigenie","Lemgo"`` wird in das
CSV der ``schuleB`` kopiert, wobei die Spalte ``"Schule"`` angepasst und aus dem
CSV der ``schuleA`` entfernt wird. Der Import wird nun an ``schuleB`` vor
``schuleA`` durchgeführt. Zwischendurch wird die Lehrerin Mitglied beider
Schulen sein. Das Benutzerkonto würde sich folgendermaßen ändern:

.. code-block:: console

   # vor dem Import:
   DN: uid=iphigenie.lemgo,cn=lehrer,cn=users,ou=schuleA,<base dn>
     school: schuleA

   # nach dem Import an schuleB:
   DN: uid=iphigenie.lemgo,cn=lehrer,cn=users,ou=schuleA,<base dn>
     school: schuleA
     school: schuleB

   # nach dem Import an schuleA:
   DN: uid=iphigenie.lemgo,cn=lehrer,cn=users,ou=schuleB,<base dn>
     school: schuleB
