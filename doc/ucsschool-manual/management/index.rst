.. _school-setup-umc:

****************************************
Verwaltung von Schulen über die |UCSUMC|
****************************************

|UCSUAS| bietet für viele der regelmäßig wiederkehrenden Verwaltungsaufgaben
spezielle UMC-Module und -Assistenten an, die beim Anlegen, Modifizieren und
Löschen von z.B. Schulen, Benutzerkonten und Rechnern unterstützen.

Ergänzend hierzu gibt es Programme für die Kommandozeile, die auch eine
automatisierte Pflege der |UCSUAS|-Umgebung zulassen. Diese werden in
:ref:`school-setup-cli` näher beschrieben.

.. important::

   Das Bearbeiten von |UCSUAS| Objekten außerhalb der |UCSUAS|-UMC-Module oder
   des Benutzer-Imports kann zu fehlerhaften Objekten führen.

   Um diese Objekte sichtbar zu machen, werden ab |UCSUAS| 4.4 v8 Objekte
   validiert, die aus dem Verzeichnisdienst in |UCSUAS| geladen werden.

   Zusätzlich zu den Fehlermeldungen in den regulären Log Dateien wird eine
   Ausgabe des gesamten Objekts in die nur vom Benutzer ``root`` lesbare Datei
   :file:`/var/log/univention/ucs-school-validation.log` geschrieben.

   Mit der |UCSUCRV| :envvar:`ucsschool/validation/logging/backupcount` kann
   gesetzt werden, wie viele Kopien dieser Datei in Rotation gehalten werden,
   bevor die erste gelöscht wird. Als Standard ist ``60`` gesetzt.

   Mit der |UCSUCRV| :envvar:`ucsschool/validation/logging/enabled` kann an- und
   abgeschaltet werden, ob in die beiden Dateien
   :file:`/var/log/univention/ucs-school-validation.log` und
   :file:`/var/log/univention/management-console-module-schoolwizards.log`
   geloggt werden soll. Als Standard ist ``yes`` gesetzt.


.. toctree::
   :caption: Kapitelinhalte

   schools
   users
   classes
   computers
   rest-api
