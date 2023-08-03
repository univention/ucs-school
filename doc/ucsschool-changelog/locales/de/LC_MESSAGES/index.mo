��          �               ,  �   -  (   �  $  &     K  �   g  �   !  +  �  �  �  �  �  �   �	  �   >
  �   ;     �  �   �  �  �       �    �   �  (   �  S  �     (  �   F       m  �       R  '  �   z  Q  #  �   u       �     �        �   After the join script runs, you may update the UCR variable at any time before running a user import. You may also run the diagnostic for invalid usernames at any time using the System Diagnostic UMC module. Change in the Windows naming conventions During the update, services within the domain may fail. For this reason, the update should be performed within a maintenance window. It is generally recommended to install and test the update in a test environment first. The test environment should be identical to the production environment. General notes on the update If necessary, important notes about the update are covered in a separate section. The change information for previous version jumps can be found at https://docs.software-univention.de/. If you have any invalid usernames, the join script will leave the UCR variable unset. You may choose to do one of the following: In UCS 5.2, which will be the next minor release, invalid Windows usernames will no longer be allowed in any UCS\@school system, including domains that only have Linux machines. Please check your usernames with the System Diagnostic UMC module and fix any that are invalid, before doing the upgrade. In Windows there are some usernames that are reserved for `special use <https://learn.microsoft.com/en-us/troubleshoot/windows-server/identity/naming-conventions-for-computer-domain-site-ou>`_. Using a `username schema <https://docs.software-univention.de/ucsschool-import/latest/de/configuration/scheme-formatting.html>`_ for the import can lead to invalid usernames in Windows. If this happens, this can lead to errors in Windows environments, such as users being unable to login. Major updates for |UCSUAS| are released in the Univention App Center as a standalone app update. Minor updates and bug fixes (errata for |UCSUAS|) that do not require interaction with the administrator are released in the repository of the already released app version of |UCSUAS|. The changelog documents that Univention issues with each |UCSUAS| app version are then expanded accordingly with a new section that shows which packages were released at what time and which errors were fixed in the process. Set the ``ucsschool/validation/username/windows-check`` UCR variable to ``false``, to temporarily ignore invalid usernames for this minor release. The join script for this release will scan your usernames for invalid usernames. If none are found, it will set the ``ucsschool/validation/username/windows-check`` UCR variable to ``true``, so you can start getting the benefit of the checks right away. This document contains the changelogs with the detailed change information for the update of |UCSUAS| from version 5.0 v3 to 5.0 v4. Update process Use the System Diagnostic UMC module to see a list of invalid usernames and correct them, then set the ``ucsschool/validation/username/windows-check`` UCR variable to ``true``. We have added username validation when importing users, to prevent such invalid usernames from occurring. However, administrators can disable this check using the ``ucsschool/validation/username/windows-check`` UCR variable. When the variable is set to ``true``, the import will check if usernames are valid for Windows. If you have only Linux systems, you may choose to disable this check. |UCSUAS|-Update Project-Id-Version: UCS@school - 5.0v3 Changelog 
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2023-08-03 11:52+0000
PO-Revision-Date: 2023-02-06 09:57+0100
Last-Translator: Univention GmbH <packages@univention.de>
Language: de
Language-Team: Univention GmbH <packages@univention.de>
Plural-Forms: nplurals=2; plural=(n != 1);
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8
Content-Transfer-Encoding: 8bit
Generated-By: Babel 2.12.1
 Nachdem das Join-Skript durchgelaufen ist, kann die UCR Variable jederzeit vor dem Import gesetzt werden. Sie können ebenfalls die Diagnose für ungültige Benutzernamen über das UMC Modul "System Diagnose" starten. Änderung der Windows Namenskonventionen Während der Aktualisierung kann es zu Ausfällen von Diensten innerhalb der Domäne kommen. Aus diesem Grund sollte das Update innerhalb eines Wartungsfensters erfolgen. Grundsätzlich wird empfohlen das Update zunächst in einer Testumgebung einzuspielen und zu testen. Die Testumgebung sollte dabei identisch zur Produktivumgebung sein. Generelle Hinweise zum Update Sofern notwendig, werden wichtige Hinweise zum Update in einem separaten Abschnitt behandelt. Die Änderungsinformationen für vorherige Versionssprünge finden sich unter https://docs.software-univention.de/. Wenn Sie ungültige Benutzernamen haben, wird das Join-Skript die UCR Variable nicht setzen. Sie haben dann folgende Optionen:  In UCS 5.2, dem nächsten Minor Release, werden ungültige Windows Benutzernamen in UCS\@school Systemen nicht länger unterstützt. Dies gilt auch für Domänen, die nur Linux Systeme beinhalten. Bitte überprüfen Sie ihre Benutzernamen mit dem UMC Modul "System Diagnose" und ändern Sie die Benutzernamen, die ungültig sind, bevor Sie das Upgrade durchführen. In Windows gibt es Benutzernamen, die für `spezielle Verwendungszwecke <https://learn.microsoft.com/en-us/troubleshoot/windows-server/identity/naming-conventions-for-computer-domain-site-ou>`_ reserviert sind. Wenn Sie für die `Generierung von Benutzernamen <https://docs.software-univention.de/ucsschool-import/latest/de/configuration/scheme-formatting.html>`_ ein Schema verwenden, kann dies zu ungültigen Benutzernamen in Windows führen. Dies kann zu Fehlern in Windows Umgebungen führen, z.B. Benutzer die sich nicht einloggen können. Größere Updates für |UCSUAS| werden im Univention App Center als eigenständiges App-Update heraus gegeben. Kleinere Updates und Fehlerbereinigungen (Errata für |UCSUAS|), die keine Interaktion mit dem Administrator erforderlich machen, werden im Repository der bereits veröffentlichten App-Version von |UCSUAS| heraus gegeben. Die Changelog Dokumente, die Univention mit jeder |UCSUAS| App-Version heraus gibt, werden dann entsprechend um einen neuen Abschnitt erweitert, aus dem ersichtlich wird, zu welchem Zeitpunkt welche Pakete veröffentlicht und welche Fehler dabei behoben wurden. Sie können die UCR Variable ``ucsschool/validation/username/windows-check`` auf ``false`` setzen, um die Validierung temporär für dieses Minor Release auszuschalten. Das mit diesem Release ausgelieferte Join-Skript überprüft, ob alle im System verwendeten Benutzernamen unterstützt werden. Wenn keine ungültigen Benutzernamen gefunden wurden, wird die UCR Variable ``ucsschool/validation/username/windows-check`` UCR variable auf ``true`` gesetzt, sodass die neue Validierung sofort eingesetzt wird. Dieses Dokument enthält die Changelogs mit den detaillierten Änderungsinformationen zum Update von |UCSUAS| von Version 5.0 v3 nach 5.0 v4. Update-Prozess Benutzen Sie das UMC Modul "System Diagnose", um eine Liste der ungültigen Benutzernamen zu bekommen. Nach der Korrektur der Benutzernamen können Sie die UCR Variable ``ucsschool/validation/username/windows-check`` auf ``true`` setzen. Wir eine Validierung während des Imports von Benutzern hinzugefügt, um diese ungültigen Benutzernamen zu verhindern. Administratoren können diese Validierung mit der UCR Variable ``ucsschool/validation/username/windows-check`` deaktivieren. Wenn die Variable auf ``true`` gesetzt ist, validiert der Import die Benutzernamen. Wenn Sie nur Linux Systeme haben, können sie diese Überprüfung deaktivieren. |UCSUAS|-Update 