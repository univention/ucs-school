.. _school-setup-umc-user:

Verwaltung einzelner Benutzerkonten
===================================

Für die manuelle Pflege von einzelnen Benutzerkonten wird auf dem |UCSPRIMARYDN|
das UMC-Modul *Benutzer (Schulen)* bereitgestellt, welches sich in der
UMC-Modulgruppe *Schul-Administration* befindet. Es ermöglicht das Suchen nach,
sowie das Anlegen, Bearbeiten und Löschen von Schülern, Lehrern und Mitarbeitern
in der |UCSUAS|-Umgebung.

.. _school-setup-umc-user-create:

Anlegen eines Benutzerkontos
----------------------------

Um den Assistenten für das Hinzufügen eines neuen Benutzers zu starten, ist die
Schaltfläche :guilabel:`Hinzufügen` oberhalb der Tabelle auszuwählen. In
|UCSUAS|-Umgebungen ohne bestehende Benutzer fragt das Modul automatisch beim
Öffnen, ob jetzt der erste Benutzer angelegt werden soll.

.. important::

   Es ist wichtig, dass beim Anlegen einzelner Benutzer für |UCSUAS| das
   UMC-Modul *Benutzer (Schulen)* verwendet wird, weil sich |UCSUAS| Benutzer
   von regulären UCS Benutzern unterscheiden.

   Detaillierte Informationen zu den Unterschieden der Benutzerkonten finden
   sich in :uv:kb:`How a UCS@school user should look like <15630>`.

Die erste Seite des Assistenten fragt zunächst die gewünschte Benutzerrolle für
das neue Benutzerkonto ab. Zur Auswahl stehen die folgenden Benutzerrollen:

* *Schüler*
* *Lehrer*
* *Lehrer und Mitarbeiter*
* *Mitarbeiter*

Die einzelnen Benutzerrollen werden in :ref:`structure-userroles` genauer
beschrieben. Sind mehrere Schulen in der |UCSUAS|-Umgebung eingerichtet, wird
zusätzlich abgefragt, in welcher Schule das Benutzerkonto angelegt werden soll.

Über die Schaltfläche :guilabel:`Weiter` gelangt man auf die zweite Seite des
Assistenten. Dort werden die für |UCSUAS| relevanten Benutzerattribute
abgefragt. Die folgenden Attribute müssen angegeben werden:

* *Vorname*
* *Nachname*
* *Benutzername*
* *Klasse*

Über die Schaltfläche :guilabel:`Neue Klasse erstellen` ist es möglich, direkt
in das UMC-Modul *Klassen (Schule)* zu wechseln, um dort eine weitere
Schulklasse anlegen zu können. Ein Benutzer in der Rolle Schüler benötigt immer
eine Schulklasse. Benutzerkontodaten werden an anderen Stellen weiter
verarbeitet. Wenn die Angabe für die Klasse eines Schülers fehlt, kann die
Weiterverarbeitung gestört werden.

Die folgenden Attribute sind optional:

* *E-Mail*
* *Passwort*
* *deaktiviert*
* *Geburtstag*

Ist kein Passwort vergeben, muss das Passwort vom Administrator (oder Lehrer)
zurückgesetzt werden, bevor das Benutzerkonto vom Benutzer erstmals verwendet
werden kann.

.. note::

   Ab |UCSUAS| Version 5.0 v3 kann über die |UCSUCRV|
   :envvar:`ucsschool/wizards/schoolwizards/users/check-password-policies`
   die Evaluierung von Passwort Richtlinien während des Anlegens neuer Benutzer eingeschaltet werden.
   Gültige Werte sind :envvar:`yes` und :envvar:`no`. Die Evaluierung ist standardmäßig ausgeschaltet.
   Passwort Richtlinien werden beim Bearbeiten von Benutzern immer evaluiert.


Nach dem Anklicken der Schaltfläche :guilabel:`Speichern` wird das Benutzerkonto
im Verzeichnisdienst angelegt und eine Benachrichtigung über den Erfolg der
Aktion angezeigt. Anschließend wird wieder die zweite Seite des Assistenten
angezeigt, um weitere Benutzerkonten anlegen zu können. Die Einstellungen für
Schule und Benutzerrolle bleiben dabei erhalten. Mit der Verwendung der
Schaltfläche :guilabel:`Abbrechen` gelangt man zurück zum zentralen Suchdialog
des UMC-Moduls.

.. important::

   Die Benutzernamen müssen schulübergreifend eindeutig sein. D.h. es
   ist nicht möglich, den gleichen Benutzernamen an zwei
   unterschiedlichen Schulen zu verwenden.

.. important::

   Benutzernamen dürfen keine von Windows reservierten Namen enthalten. Siehe
   `Microsoft Dokumentation <https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file>`_
   für weitere Informationen.

.. note::

   Über die |UCSUCRV|
   :envvar:`ucsschool/wizards/schoolwizards/users/optional_visible_fields`
   können die angezeigten optionalen Felder angepasst werden. Ab |UCSUAS|
   4.4 v9 kann hier auch das Ablaufdatum
   (*expiration_date*) hinzugefügt werden werden.

.. _school-setup-umc-user-modify:

Bearbeiten eines Benutzerkontos
-------------------------------

Zum Bearbeiten eines Benutzerkontos ist dieses in der Tabelle auszuwählen und
die Schaltfläche :guilabel:`Bearbeiten` anzuklicken. Im folgenden Dialog können
die Attribute des Benutzerkontos bearbeitet werden. Das nachträgliche Ändern des
Benutzernamens ist nicht möglich.

Sofern der angemeldete UMC-Benutzer die Rechte für das UMC-Modul *Benutzer* aus
der Modulgruppe *Domäne* besitzt, wird zusätzlich die Schaltfläche *Erweiterte
Einstellungen* angezeigt. Über sie kann das UMC-Modul *Benutzer* geöffnet
werden, in dem viele erweiterte Einstellungen für das Benutzerkonto möglich
sind.

.. _school-setup-umc-user-delete:

Löschen von Benutzerkonten
--------------------------

Zum Löschen von Benutzerkonten sind diese in der Tabelle auszuwählen und
anschließend die Schaltfläche :guilabel:`Löschen` anzuklicken.
Nach dem Bestätigen werden die Benutzerkonten aus dem Verzeichnisdienst
entfernt.
