.. _workgroups:

Arbeitsgruppen verwalten
========================

Jeder Schüler ist Mitglied seiner Klasse. Darüber hinaus gibt es die
Möglichkeit, Schüler und Lehrer in klassenübergreifende Arbeitsgruppen (AGs)
einzuordnen. Dieses Modul erlaubt es, neue Arbeitsgruppen anzulegen, zu
bearbeiten und zu löschen.

Das Anlegen einer Arbeitsgruppe legt automatisch auch einen Datenbereich auf dem
Schulserver (Dateifreigabe) an, auf den alle Mitglieder der Arbeitsgruppe
Zugriff erhalten. Der Name der Dateifreigabe ist identisch mit dem gewählten
Namen der Arbeitsgruppe. Diese Funktion lässt sich über das Deaktivieren der
Option *Freigabe erstellen* abschalten. Diese Entscheidung kann nach Erstellung
der Arbeitsgruppe nicht mehr geändert werden.

Nach einem Klick auf *Arbeitsgruppen verwalten* wird eine Liste aller
Arbeitsgruppen angezeigt.

Über das Eingabefeld *Suchmuster* können die angezeigten Arbeitsgruppen
eingeschränkt werden. Trägt man hier beispielsweise ``inf`` ein, werden nur
Arbeitsgruppen angezeigt, die die Zeichenkette ``inf`` enthalten (z.B. die
Informatik-AG).

Eine neue Arbeitsgruppe kann über die Option *Arbeitsgruppe hinzufügen*
eingerichtet werden. Es muss mindestens der Name der *Arbeitsgruppe* eingegeben
werden. Optional kann eine *Beschreibung* hinterlegt werden.

Eine bestehende Arbeitsgruppe kann durch Auswahl und die Option
*Löschen* gelöscht werden.

.. _select-workgroup:

.. figure:: /images/workgroup_1_selected.png
   :alt: Auswahl einer Arbeitsgruppe

   Auswahl einer Arbeitsgruppe

Ein Klick auf den Namen der Arbeitsgruppe öffnet ein neues Fenster. Der Name
einer bereits bestehenden *Arbeitsgruppe* kann nachträglich nicht geändert
werden.

Im Eingabefeld *Mitglieder* wird eine Liste der Schüler und Lehrer angezeigt,
die Mitglied der Arbeitsgruppe sind. Ein Klick auf *Hinzufügen* öffnet einen
neuen Dialog.

.. _assign-pupils:

.. figure:: /images/workgroup_2_add_students.png
   :alt: Zuweisen von Schülern zu einer Arbeitsgruppe

   Zuweisen von Schülern zu einer Arbeitsgruppe

Es erscheint eine Liste aller Schüler und Lehrer der Schule. Die Liste der
angezeigten Benutzer kann eingeschränkt werden, indem über den Menüpunkt
*Benutzergruppe oder Klasse* eine Klasse oder AG ausgewählt wird. Es werden dann
nur die Schüler und Lehrer dieser Klasse dargestellt. Durch Eingabe von
Benutzer-, Vor- und/oder Nachname in das Eingabefeld *Name* und anschließendem
Klick auf *Suchen* kann auch gezielt nach einem Benutzer gesucht werden. Die
Benutzer, die zu der Arbeitsgruppe hinzugefügt werden sollen, können durch
Aktivieren des Auswahlkästchens vor dem Benutzernamen markiert werden. Ein Klick
auf :guilabel:`Hinzufügen` fügt die Benutzer dann der Arbeitsgruppe hinzu.

Benutzer können aus der Arbeitsgruppe entfernt werden, indem das
Auswahlkästchens vor dem zu entfernenden Benutzer aktiviert und und anschließend
auf *Entfernen* geklickt wird.

Ab |UCSUAS| 4.4v7 können E-Mailadressen für Arbeitsgruppen aktiviert und
verwaltet werden, sollte dieses Feature von einem Administrator eingerichtet
worden sein. Dazu muss die Option *E-Mail-Adresse aktivieren* aktiviert
werden. Dadurch werden weitere Eingabefelder freigeschaltet. Die E-Mail-Adresse
wird nur lesend angezeigt, da sie automatisch über ein zuvor konfiguriertes
Muster zusammengesetzt wird.

.. _manage-workgroup-emails:

.. figure:: /images/workgroup_3_manage_email.png
   :alt: Konfiguration der E-Mail-Adresse für eine Arbeitsgruppe

   Konfiguration der E-Mail-Adresse für eine Arbeitsgruppe

Die beiden letzten Eingabefelder können dazu genutzt werden, die Nutzer und
Gruppen zu beschränken, die E-Mails an diese Arbeitsgruppe senden dürfen. Sind
beide Eingabefelder leer, so ist diese E-Mail-Adresse unbeschränkt. Wurde jedoch
in mindestens eines dieser Felder ein Benutzer oder eine Gruppe eingetragen,
werden alle E-Mails von Absendern, die sich nicht in einer dieser Listen
befinden, abgelehnt. Das Eingabefeld wird analog zum schon zuvor beschriebenen
Eingabefeld *Mitglieder* genutzt.

Die E-Mail-Adresse einer Arbeitsgruppe kann jederzeit über den *Bearbeiten*
Dialog wieder deaktiviert werden. Dabei gehen sowohl die E-Mail-Adresse, als auch
die konfigurierten Absender-Limitierungen verloren.

Es kann vorkommen, dass das Feature zur Aktivierung von E-Mailadressen
nicht aktiviert ist, die Arbeitsgruppe aber von einer anderen Quelle
eine E-Mail-Adresse zugeordnet bekommen hat. In diesem Fall erscheinen
bei Bearbeiten der Arbeitsgruppe alle hier beschriebenen Eingabefelder,
bis auf die Möglichkeit die E-Mail-Adresse zu deaktivieren.
