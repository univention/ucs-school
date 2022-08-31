.. _configuration-cmdline-parameters:

Kommandozeilenparameter
=======================

.. program:: ucs-school-user-import

.. code-block:: console

   $ /usr/share/ucs-school-import/scripts/ucs-school-user-import --help
   usage: ucs-school-user-import [-h] [-c CONFFILE] [-i INFILE]
                   [-l LOGFILE] [-m] [-n] [-s SCHOOL]
                   [--set [KEY=VALUE [KEY=VALUE ...]]]
                   [--source_uid source_uid] [-u USER_ROLE] [-v]
   optional arguments:
     -h, --help            show this help message and exit
     -c CONFFILE, --conffile CONFFILE
               Configuration file to use (see
               /usr/share/doc/ucs-school-import for an
               explanation on configuration file stacking).
     -i INFILE, --infile INFILE
               CSV file with users to import (shortcut for
               --set input:filename=...).
     -l LOGFILE, --logfile LOGFILE
               Write to additional logfile (shortcut for
               --set logfile=...).
     --set [KEY=VALUE [KEY=VALUE ...]]
               Overwrite setting(s) from the configuration file. Use ':' in
               key to set nested values (e.g. 'scheme:email=...').
     -m, --no-delete
               Only add/modify given user objects. User objects not
               mentioned within input files are not deleted/deactived
               (shortcut for --set no_delete=...) [default: False].
     -n, --dry-run
               Dry run - don't actually commit changes to LDAP (shortcut
               for --set dry_run=...) [default: False].
     --source_uid source_uid
               The ID of the source database (shortcut for
               --set source_uid=...) [mandatory either here or in the
               configuration file].
     -s SCHOOL, --school SCHOOL
               Name of school. Set only, if the source data does not
               contain the name of the school and all users are from one
               school (shortcut for --set school=...) [default: None].
     -u USER_ROLE, --user_role USER_ROLE
               Set this, if the source data contains users with only one
               role <none|student|staff|teacher|teacher_and_staff>
               (shortcut for --set user_role=...) [default: None].
     -v, --verbose
               Enable debugging output on the console [default: False].

Nahezu alle Kommandozeilenparameter können auch in den Konfigurationsdateien
angegeben werden. Um Variablen aus Konfigurationsdateien an der Kommandozeile zu
setzen, kann ``--set`` verwendet werden. Verschachtelte
Konfigurationsvariablen können mit dem Doppelpunkt angegeben werden.

Um z.B. ``2`` als die Anzahl der Kopfzeilen in einer CSV-Datei anzugeben, kann
entweder in einer Konfigurationsdatei stehen:

.. code-block:: json

   {
       "csv": {
           "header_lines": 2
       }
   }


oder es kann an der Kommandozeile der folgende Parameter verwendet
werden:

.. code-block::

   --set csv:header_lines=2

Alle Zuweisungen für Variablen können mit Leerzeichen getrennt hinter dem
Kommandozeilenparameter ``--set`` aufgelistet werden. Dabei ist zu beachten,
dass nur ein ``--set``-Parameter an der Kommandozeile ausgewertet wird.

.. code-block::

   --set csv:header_lines=2 maildomain=univention.de no_delete=True


