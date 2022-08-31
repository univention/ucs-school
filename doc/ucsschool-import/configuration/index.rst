.. _configuration:

*************
Konfiguration
*************

Die Konfiguration des Imports wird über Dateien im `JSON-Format
<https://de.wikipedia.org/wiki/JavaScript_Object_Notation>`_ und
Kommandozeilenparameter gesteuert. Alle Kommandozeilenparameter können als
Variablen in den Konfigurationsdateien verwendet werden, so dass ein Ausführen
der Importsoftware ohne Kommandozeilenparameter möglich ist. Es ist aber auch
möglich, über Kommandozeilenparameter sämtliche Variablen, die in
Konfigurationsdateien stehen, zu überschreiben.

Beim Start von :command:`ucs-school-user-import` werden nacheinander mehrere
Konfigurationsdateien eingelesen. Jede Datei fügt der Konfiguration neue
Konfigurationsvariablen hinzu oder überschreibt bereits existierende
Konfigurationsvariablen von vorher eingelesenen Konfigurationsdateien.

Die Konfiguration des Imports wird in der folgenden Reihenfolge (mit
aufsteigender Priorität) über folgende Konfigurationsdateien und
Kommandozeilenparameter eingelesen:

1. :file:`/usr/share/ucs-school-import/configs/global_defaults.json`: Diese
   Datei sollte nicht manuell editiert werden!

2. :file:`/var/lib/ucs-school-import/configs/global.json`: Diese Datei kann
   manuell angepasst werden - siehe unten.

3. :file:`/usr/share/ucs-school-import/configs/user_import_defaults.json`: Diese
   Datei sollte nicht manuell editiert werden.

4. :file:`/var/lib/ucs-school-import/configs/user_import.json`: Diese Datei kann
   manuell angepasst werden - siehe unten.

5. Eine JSON-Datei, die mit dem Parameter ``-c`` an der Kommandozeile angegeben
   wurde.

6. Variablen, die über den Kommandozeilenparameter ``--set`` gesetzt wurden.

Die Konfigurationsdateien unterhalb von
:file:`/usr/share/ucs-school-import/configs/` sollten nicht editiert werden. Sie
sind Teil der |UCSUAS|-Installation und werden u.U. von Updates überschrieben.

Die Dateien unter :file:`/var/lib/ucs-school-import/configs/` werden automatisch
bei der Installation angelegt und sind eigens dafür vorgesehen, eigene
Einstellungen bzw. Konfigurationen vorzuhalten. Die Dateien bleiben bei Updates
unangetastet.

Folgendes Verfahren wird empfohlen:

1. Um Variablen zu überschreiben, die in
   :file:`/usr/share/ucs-school-import/configs/global_defaults.json` gesetzt
   werden, können eigene Werte in die Datei
   :file:`/var/lib/ucs-school-import/configs/global.json` eingetragen werden.

2. Um Variablen zu überschreiben, die in
   :file:`/usr/share/ucs-school-import/configs/user_import_defaults.json`
   gesetzt werden, können eigene Werte in die Datei
   :file:`/var/lib/ucs-school-import/configs/user_import.json` eingetragen
   werden.

   Falls regelmäßig aus mehreren Quellverzeichnissen Benutzer importiert werden,
   sollten in dieser Datei auch Variablen gesetzt werden, die für alle
   Datenquellen gleichermaßen gelten.

3. Pro Quellverzeichnis sollte eine Konfigurationsdatei unterhalb von
   :file:`/var/lib/ucs-school-import/configs/` abgelegt werden, welche
   schließlich an der Kommandozeile mit ``-c`` angegeben wird. Diese Datei
   enthält Konfigurationseinstellungen, die auf die Spezifika der jeweiligen
   Schule bzw. Schulverwaltungssoftware einzugehen, und die jeweilige
   ``source_uid`` passend zum Quellverzeichnis.

Die resultierende Konfiguration, die sich aus eingelesenen Konfigurationsdateien
sowie verwendete Kommandozeilenparameter zusammenstellt, wird am Anfang jedes
Importlaufes angezeigt und in alle Protokolldateien geschrieben. Um eine
Konfiguration zu testen, kann ein Probelauf mit ``--dry-run`` gestartet (und
jederzeit gefahrlos abgebrochen) werden. Der Parameter simuliert einen Import,
ohne dass Änderungen an |UCSUAS|-Benutzern vorgenommen werden.

Eine detaillierte Beschreibung zu möglichen Optionen der globalen Konfiguration
befindet sich auch auf dem Primary/Backup Directory Node unter
:file:`/usr/share/doc/ucs-school-import/global_configuration_readme.txt`.
Informationen zum Benutzerimport gibt es unter
:file:`/usr/share/doc/ucs-school-import/user_import_configuration_readme.txt.gz`.

.. toctree::

   command-line
   format
   default-keys
   mapping
   scheme-formatting
   uniqueness
   delete-users
