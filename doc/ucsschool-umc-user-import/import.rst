.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _procedure:

*************************
Ablauf des Importvorgangs
*************************

Das UMC-Modul leitet den Anwender in mehreren Schritten durch den
Import:

.. _process:

.. figure:: /images/import_ui_process.png
   :alt: Schritte eines Importvorganges

   Schritte eines Importvorganges

Ein neuer Import kann in der Übersichtsseite durch Klicken auf :guilabel:`Neuen
Benutzerimport durchführen` gestartet werden. Wenn noch nie ein Import
durchgeführt wurde, startet das UMC-Modul direkt mit dem ersten Schritt für
einen neuen Import. In allen anderen Fällen wird zunächst die Übersicht
angezeigt.

.. note::

   Sollte sich der Anwender per *Single Sign-On* (z.B. über SAML) angemeldet
   haben, erscheint ein Fenster, das (u.U. mehrfach) zur Eingabe des eigenen
   Benutzerpasswortes auffordert.

.. _overview1:

.. figure:: /images/import_ui_overview1.png
   :alt: Übersichtsseite

   Übersichtsseite

#. Zuerst muss der Typ der zu importierenden Benutzer ausgewählt werden.

   .. _choose-user-type:

   .. figure:: /images/import_ui_choose_user_type.png
      :alt: Auswahl des Benutzertyps

      Auswahl des Benutzertyps

#. Anschließend kann die CSV-Datei mit den Benutzerdaten ausgewählt
   werden.

   .. _choose-csv-file:

   .. figure:: /images/import_ui_upload_csv.png
      :alt: Hochladen der CSV-Datei

      Hochladen der CSV-Datei

#. Nun werden die Daten geprüft und es wird ein Test-Import durchgeführt, um
   mögliche Fehler vorab zu erkennen. Das Benutzerverzeichnis wird dabei nicht
   verändert.

#. Je nach Menge der zu importierenden Daten, kann der Test-Import einige Zeit
   beanspruchen.

   * War die Simulation erfolgreich, kann nun der tatsächlich Import gestartet
     werden.

     .. _start-import:

     .. figure:: /images/import_ui_start_import.png
        :alt: Simulation war erfolgreich

        Simulation war erfolgreich

   * Traten während des Test-Imports Fehler auf, wird eine Fehlermeldung
     angezeigt. Unterhalb der Fehlermeldung ist im Text ein Link. Durch Klicken
     auf diesen, wird eine E-Mail mit der Fehlermeldung an einen Administrator
     verfasst.

     .. _sim-had-error:

     .. figure:: /images/import_ui_simulation_error.png
        :alt: Simulation hatte Fehler

        Simulation hatte Fehler

#. Nach dem Start des Imports kehrt das UMC-Modul zur Übersichtsseite zurück.
   Wenn der neue Import-Job noch nicht angezeigt wird, kann die Liste mit der
   Schaltfläche :guilabel:`Aktualisieren` neu geladen werden.

   .. _overview2:

   .. figure:: /images/import_ui_overview2.png
      :alt: Übersichtsseite mit gestartetem Import

      Übersichtsseite mit gestartetem Import

