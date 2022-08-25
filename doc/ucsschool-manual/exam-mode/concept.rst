.. _school-exam-concept:

Technische Hintergründe
=======================

Zur Verwendung des Klassenarbeitsmodus sind folgende Voraussetzungen zu
erfüllen:

* Verwendung einer Samba 4-Domäne (AD-Domäne)

* Einsatz von Windows XP oder höher auf den Prüfungscomputern

* Import von Computerkonten und Zuordnung der Computer zu Computerräumen

* Die Verwendung des UCS@school-HTTP-Proxys durch die Prüfungscomputer zur
  Filterung des Internetzugriffs

Eine neue Klassenarbeit kann über das Modul *Klassenarbeit starten* begonnen
werden. Beim Durchlaufen der einzelnen Schritte werden von der Lehrkraft ein
Name für die Klassenarbeit und die teilnehmenden Klassen/Arbeitsgruppen
ausgewählt. Zusätzlich können für die Arbeit notwendige Dateien hochgeladen
sowie Computerraumeinstellungen ausgewählt werden.

Damit Schülern nicht die Möglichkeit gegeben wird, auf ihr bisheriges
Heimatverzeichnis zuzugreifen, werden zum Zeitpunkt des Einrichtens der
Klassenarbeit für die ausgewählten Schülerkonten spezielle Klassenarbeitskonten
neu angelegt.

Der Anmeldename für das Klassenarbeitskonto setzt sich aus einem festgelegten
Präfix (standardmäßig ``exam-``) und dem normalen Benutzernamen zusammen.
Beispielsweise wird für den Benutzer ``anton123`` das Klassenarbeitskonto
``exam-anton123`` angelegt, mit dem er sich während der Klassenarbeit anmelden
muss.

Für das Klassenarbeitskonto wird ein neues Heimatverzeichnis erzeugt,
Passwörter und andere Konteneinstellungen werden jedoch aus dem ursprünglichen
Benutzerkonto direkt übernommen. Schüler können die Zugriffsberechtigungen ihrer
Heimatverzeichnisse nicht verändern. Dadurch wird verhindert, dass ein Schüler
sein Heimatverzeichnis für weitere Schüler freigegeben kann.

Um Schülern den Zugriff auf andere Dienste (z.B. Mail oder Cloud) während einer
Klassenarbeit zu verwehren, kann die UCR-Variable
:envvar:`ucsschool/exam/user/disable` aktiviert werden (siehe
:ref:`school-exam-configuration`).

Für deaktivierte Nutzerkonten wird kein Klassenarbeitskonto angelegt. Diese
werden beim Hinzufügen zur Klassenarbeit ignoriert. Soll ein Schüler an einer
Klassenarbeit teilnehmen, muss dessen Nutzerkonto aktiviert sein. Wie Benutzer
aktiviert/deaktiviert werden können, wird in :cite:t:`ucs-manual` im Abschnitt
:ref:`users-management-table-account` beschrieben.

Alle Klassenarbeitskonten der Schüler sowie alle Rechner des Computerraumes sind
für den Zeitraum der Klassenarbeit Mitglieder der Gruppe
:samp:`OU{OU-Name}-Klassenarbeit``. Durch diese Gruppe können spezifische
Einschränkungen für Schüler und Rechner mit Hilfe von Windows-Gruppenrichtlinien
vorgenommen werden (siehe :ref:`school-exam-gpo`).

.. note::

   Damit die Einstellungen der Gruppenrichtlinien für die Rechner entsprechend
   greifen, ist es wichtig, dass die Schülerrechner des Computerraumes nach dem
   Einrichten einer Klassenarbeit neu gestartet werden. Dieser Vorgang wird
   durch das UMC-Modul *Klassenarbeit starten* unterstützt, indem alle
   eingeschalteten Rechner automatisch neu gestartet werden können.

   Zusätzlich ist es aus dem selben Grund wichtig, dass nach Beenden einer
   Klassenarbeit die Schülerrechner entweder ausgeschaltet oder neu gestartet
   werden. Nur so können die ursprünglichen Einstellungen der Gruppenrichtlinien
   wieder wirksam werden.

   Damit leicht erkannt werden kann, dass die Gruppenrichtlinien für den
   Klassenarbeitsmodus an den Rechnern wirksam sind, weisen Sie zum Beispiel ein
   optisch klar zu unterscheidendes Hintergrundbild über die Richtlinien zu.
