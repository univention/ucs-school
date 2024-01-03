.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _testing-cmdline:

*************************
Test an der Kommandozeile
*************************

Das Testen einer Konfiguration, insbesondere bei Änderungen an der
Spalten-Zuordnung, ist u.U. an der Kommandozeile schneller als in der UMC. Bei
Verwendung der richtigen Kommandozeilenparameter wird *beinahe* der gleiche
Importvorgang ausgeführt, wie wenn er vom UMC-Modul gestartet würde.

Das Skript, das Beispieldaten erzeugt, druckt am Ende die benötigten
Kommandozeilenparameter exakt aus. Hier ein Beispiel:

.. code-block::

   --school 'SchuleEins' \
   --user_role 'ROLE' \
   --source_uid 'schuleeins-ROLE' \
   --conffile '/usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json' \
   --infile 'test_users_2018-07-04_12:31:46.csv'


:samp:`{ROLE}` muss mit ``student``, ``staff``, ``teacher`` oder
``teacher_and_staff`` ersetzt werden, und ``SchuleEins`` mit der entsprechenden
:samp:`OU` (in ``'schuleeins-ROLE'`` in Kleinbuchstaben).
