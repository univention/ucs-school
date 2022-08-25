.. _module-overview:

************************************************
Übersicht über die schulspezifischen Anwendungen
************************************************

.. _ucsschool-modules:

Modulübersicht
==============

|UCSUAS| stellt eine Reihe von Modulen für die |UCSUMC| bereit, die für den
IT-gestützten Unterricht verwendet werden können.

Im folgenden werden die Module kurz beschrieben. Eine ausführliche Beschreibung
der Verwendung der Module findet sich in :cite:t:`ucsschool-teacher`.

Einige Module stehen Lehrern und Schuladministratoren zur Verfügung während
andere Module nur Schuladministratoren vorbehalten sind:

Passwörter (Schüler)
   *Passwörter (Schüler)* erlaubt Lehrern das Zurücksetzen von
   Schüler-Passwörtern.

Passwörter (Lehrer)
   *Passwörter (Lehrer)* erlaubt Schuladministratoren das Zurücksetzen von
   Lehrer-Passwörtern.

Passwörter (Mitarbeiter)
   *Passwörter (Mitarbeiter)* erlaubt Schuladministratoren das Zurücksetzen von
   Mitarbeiter-Passwörtern.

Computerraum
   Das Modul *Computerraum* erlaubt die Kontrolle der Schüler-PCs und des
   Internetzugangs während einer Unterrichtsstunde. Der Internetzugang kann gesperrt
   oder freigegeben werden und einzelne Internetseiten können gezielt
   freigegeben werden.

   Wenn eine entsprechende Software (*Veyon*) auf den Schüler-PCs installiert
   ist, besteht auch die Möglichkeit diese PCs zu steuern. So kann
   beispielsweise der Bildschirm gesperrt werden, so dass in einer Chemie-Stunde
   die ungeteilte Aufmerksamkeit auf ein Experiment gelenkt werden kann.

   Außerdem kann der Bildschirminhalt eines PCs auf andere Systeme übertragen
   werden. Dies erlaubt es Lehrern, auch ohne einen Beamer Präsentationen
   durchzuführen.

Helpdesk kontaktieren
   Jede Schule wird durch einen Helpdesk betreut. Der Helpdesk kann z.B. durch
   eine Support-Organisation beim Schulträger oder durch technisch versierte
   Lehrer an den Schulen umgesetzt werden. Über das Modul *Helpdesk
   kontaktieren* können Lehrer und Schuladministratoren eine E-Mailanfrage
   stellen. Die Konfiguration des Helpdesk-Moduls wird in
   :ref:`school-setup-generic-configure-helpdesk` beschrieben.

Arbeitsgruppen verwalten
   Jeder Schüler ist Mitglied seiner Klasse. Darüber hinaus gibt es die
   Möglichkeit mit dem Modul *Arbeitsgruppen verwalten* Schüler und Lehrer in
   klassenübergreifende Arbeitsgruppen einzuordnen.

   Das Anlegen einer Arbeitsgruppe legt automatisch einen Datenbereich auf dem
   Schulserver (Dateifreigabe) an, auf den alle Mitglieder der Arbeitsgruppe
   Zugriff erhalten. Der Name der Dateifreigabe ist identisch mit dem gewählten
   Namen der Arbeitsgruppe.

   Das Anlegen, Bearbeiten und Löschen von Arbeitsgruppen ist in der
   Standardkonfiguration sowohl den Lehrern als auch den Schuladministratoren
   erlaubt.

Drucker moderieren
   Mit dem Modul *Drucker moderieren* können Ausdrucke der Schüler geprüft
   werden. Die anstehenden Druckaufträge können vom Lehrer betrachtet und
   entweder verworfen oder zum Drucken freigegeben werden. Dadurch können
   unnötige oder fehlerhafte Ausdrucke vermieden werden.

Materialien verteilen
   Das Modul *Materialien verteilen* vereinfacht das Verteilen und Einsammeln
   von Unterrichtsmaterial an Klassen oder Arbeitsgruppen.

   Optional kann eine Frist zum Verteilen und Einsammeln festgelegt werden. So
   ist es möglich, Aufgaben zu verteilen, die bis zum Ende der Unterrichtsstunde
   zu bearbeiten sind. Nach Ablauf der Frist werden die verteilten Materialien
   dann automatisch wieder eingesammelt und im Heimatverzeichnis des Lehrers
   abgelegt.

Computerräume verwalten
   Mit dem Modul *Computerräume verwalten* werden Computer einer Schule einem
   Computerraum zugeordnet. Diese Computerräume können von den Lehrern zentral
   verwaltet werden, etwa indem der Internetzugang freigegeben wird.

Unterrichtszeiten
   Das Modul *Unterrichtszeiten* erlaubt es, die Zeiträume der jeweiligen
   Unterrichtsstunden pro Schule zu definieren.

Lehrer Klassen zuordnen
   Für jede Klasse gibt es einen gemeinsamen Datenbereich. Damit Lehrer auf
   diesen Datenbereich zugreifen können, müssen sie mit dem Modul *Lehrer
   Klassen zuordnen* der Klasse zugewiesen werden.

Internetregeln definieren
   Für die Filterung des Internetzugriffs wird ein Proxy-Server eingesetzt, der
   bei dem Abruf einer Internetseite prüft, ob der Zugriff auf diese Seite
   erlaubt ist. Ist das nicht der Fall, wird eine Informationsseite angezeigt.
   Dies wird in :ref:`school-proxy` weitergehend beschrieben.

   Wenn Schüler beispielsweise in einer Schulstunde in der Wikipedia
   recherchieren sollen, kann eine Regelliste definiert werden, die Zugriffe auf
   alle anderen Internetseiten unterbindet. Diese Regelliste kann dann vom
   Lehrer zugewiesen werden.

   Mit dem Modul *Internetregeln definieren* können die Regeln verwaltet werden.

.. _ucsschool-reset-passwords:

Passwörter zurücksetzen
=======================

Mit den Modulen *Passwörter (Schüler)*, *Passwörter (Lehrer)* und *Passwörter
(Mitarbeiter)* lassen sich Benutzerpasswörter zurücksetzen. Die
Benutzeroberfläche der Module ist identisch. Es werden alle
Schüler/Lehrer/Mitarbeiter der gewählten *Schule* angezeigt. Durch Auswahl einer
*Klasse oder Arbeitsgruppe* und/oder Nutzung der Suchleiste lässt sich die Menge
der angezeigten Nutzer weiter eingrenzen.

.. _reset-student-password:

.. figure:: /images/reset_student_password.png
   :alt: Zurücksetzen von Schülerpasswörtern

   Zurücksetzen von Schülerpasswörtern

Durch Auswahl eines oder mehrerer Nutzer und Anklicken von :guilabel:`PASSWORT
ZURÜCKSETZEN`, kann ein neues Passwort für die jeweiligen Nutzer festgelegt
werden.

.. _reset-student-password-popup:

.. figure:: /images/reset_student_password_popup.png
   :alt: Festlegen eines neuen Passworts

   Festlegen eines neuen Passworts

Aus Sicherheitsgründen ist es vor dem Zurücksetzen des Passwortes erforderlich,
dass der aktuell eingeloggte Nutzer sein Passwort erneut eingeben muss.

Die bestehenden Schüler-Passwörter können außerdem nicht ausgelesen werden. Wenn
Schüler ihr Passwort vergessen, muss ein neues Passwort vergeben werden.
Schuladministratoren dürfen die Passwörter von Lehrern und Mitarbeitern
zurücksetzen.

Neben dem Namen und Nutzernamen der angezeigten Nutzer wird außerdem gezeigt,
bei wem eine Änderung des Passwortes bei der nächsten Anmeldung erforderlich
ist. Die Passwortänderung ist dann erforderlich, wenn beim Zurücksetzen eines
Passworts die Checkbox *Benutzer muss das Passwort bei der nächsten Anmeldung
ändern* angewählt wurde. Das Verhalten dieser Checkbox lässt sich durch folgende
UCR-Variablen ändern:

.. envvar:: ucsschool/passwordreset/password-change-on-next-login

   Wenn mit ``true`` eingeschaltet, wird der Wert der Checkbox standardmäßig
   eingeschaltet.

.. envvar:: ucsschool/passwordreset/force-password-change-on-next-login

   Wenn mit ``true`` eingeschaltet, wird das Ändern des Wertes in der Checkbox
   verhindert.

