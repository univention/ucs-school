.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration-json-format:

JSON-Konfigurationsformat
=========================

Das JSON-Format erlaubt Daten in verschachtelten Strukturen zu speichern, und
ist sowohl von Computern als auch Menschen zuverlässig zu lesen und zu
schreiben. Nach dem Editieren einer JSON-Datei kann ihre syntaktische
Korrektheit mit Hilfe einer Webseite zur JSON Validierung oder eines
Kommandozeilenprogramms überprüft werden:

.. code-block:: console

   $ python3 -m json.tool < my_config.json


Im Folgenden werden alle Konfigurationsschlüssel und ihre möglichen Werte und
Typen beschrieben.

* Schlüssel sind immer als Zeichenketten (``string``) zu behandeln und müssen in
  doppelten Anführungszeichen (``"``) stehen.

* Als Datentypen werden folgende Typen unterstützt:

  * Wahrheitswerte: ``boolean`` - ``true`` / ``false``

  * Ganzzahlen: ``int``

  * Gleitkommazahlen: ``float``

  * Listen: ``list`` - Werte die in ``[`` und ``]`` eingeschlossen sind.

  * Objekte: ``object`` - Neue Verschachtelungsebene die in ``{`` und ``}``
    eingeschlossen wird. Die Verschachtelungstiefe wird in den Schlüsseln wie
    oben beschrieben mit Doppelpunkten angezeigt.

.. note::

   Eine Kurzreferenz aller Konfigurationsschlüssel findet sich auf dem
   |UCSPRIMARYDN| im Verzeichnis :file:`/usr/share/doc/ucs-school-import/`.

.. _configuration-json-format-global:

Globale Konfiguration
---------------------

.. option:: dry_run, -n, --dry-run

   Ob ein Testlauf gestartet werden soll. Es werden keine Änderungen
   vorgenommen.

   Standard (``boolean``):
      ``false``


.. option:: logfile, -l, --logfile

   Datei in die das ausführliche Protokoll geschrieben werden soll. Es wird
   außerdem eine Datei, die auf :file:`.info` endet, mit weniger technischen
   Details, angelegt.

   Standard (``string``)
      :file:`/var/log/univention/ucs-school-import.log`

.. option:: verbose, -v, --verbose

   Ob ein ausführliches Protokoll auf die Kommandozeile geschrieben werden soll.

   Standard (``boolean``)
      ``true``


.. _configuration-json-format-userimport:

Konfiguration des Benutzerimports
---------------------------------

.. option:: classes

   Die Methoden der Klasse :py:class:`DefaultUserImportFactory` können
   überschrieben werden, ohne die Klasse selbst zu ändern.

   Die Namen der überschriebenen Methoden ohne vorangestelltes ``make_`` sind
   die Schlüssel, der volle Python-Pfad der Wert.

   Standardmäßig ist das Objekt leer und die Klasse
   :py:class:`DefaultUserImportFactory` wird unverändert verwendet.

   Ein Beispiel findet sich in
   :ref:`extending-subclassing-overwriting-factory-method`.

   Standard (``object``)
      ``{}``


.. option:: factory

   Voller Python-Pfad zu einer Python-Klasse, die von :py:class:`DefaultUserImportFactory`
   abgeleitet ist. Wenn gesetzt, wird sie an ihrer Stelle verwendet (siehe
   :ref:`extending-subclassing-replacing-factory-class`).

   Standard (``string``)
      :py:class:`ucsschool.importer.default_user_import_factory.DefaultUserImportFactory`


.. option:: input

   Objekt, welches Informationen über die Eingabedaten enthält.

   Standard (``object``)


.. option:: input:type

   Datenformat der angegebenen Eingabedatei. |UCSUAS| unterstützt derzeit nur
   ``CSV`` als Datenformat.

   Standard (``string``)
      ``csv``

.. option:: input:filename, -i, --infile

   Einzulesende Datei.

   Standard (``string``)
      :file:`/var/lib/ucs-school-import/new-format-userimport.csv`


.. option:: activate_new_users

   Objekt, welches Konfigurationsmöglichkeiten zur Benutzeraktivierung enthält.

   Standardmäßig ist im Objekt nur der Schlüssel ``default`` gesetzt.

   Weitere Schlüssel ``student``, ``staff``, ``teacher``, ``teacher_and_staff``
   sind möglich (siehe :ref:`configuration-default-key`).

   Standard (``object``)
      ``{"default": ..}``


.. option:: activate_new_users:default

   Diese Variable definiert, ob ein neuer Benutzer automatisch aktiviert werden
   soll. Ist ``false`` eingestellt, wird das Benutzerkonto beim Anlegen
   automatisch deaktiviert.

   Standard (``boolean``)
      ``true``


.. option:: csv

   Dieses Objekt enthält Informationen darüber, wie CSV-Eingabedaten
   interpretiert werden sollen.

   Standard (``object``)
      ``{"header_lines": .., "incell-delimiter": .., "mapping": ..}``


.. option:: csv:delimiter

   Diese Variable definiert das Trennzeichen zwischen zwei Spalten. Als Wert
   wird üblicherweise ein Komma, Semikolon oder Tabulator verwendet. Die
   Importschnittstelle versucht das Trennzeichen automatisch zu erkennen, wenn
   diese Variable nicht gesetzt ist.

   Standard (``string``)
      nicht gesetzt


.. option:: csv:header_lines

   Diese Variable definiert, wie viele Zeilen der Eingabedaten übersprungen
   werden sollen, bevor die eigentlichen Benutzerdaten anfangen.

   Wird der Wert ``1`` (Kopfdatensatz) verwendet, wird der Inhalt der ersten
   Zeile als Namen der einzelnen Spalten interpretiert. Die dort verwendeten
   Namen können dann in :option:`csv:mapping` als Schlüssel verwendet werden.

   Standard (``int``)
      ``1``


.. option:: csv:incell-delimiter

   Dieses Objekt enthält Informationen darüber, welches Zeichen *innerhalb*
   einer Zelle zwei Daten trennt und kann z.B. bei der Angabe von mehreren
   Telefonnummern verwendet werden. Es kann ein Standard (``default``) und pro
   |UCSUDM|-Attribut eine Konfiguration (mit dem Namen des Schlüssels in
   :option:`csv:mapping`) definiert werden.

   Standard (``object``)
      ``{"default": ..}``


.. option:: csv:incell-delimiter:default

   Standard-Trennzeichen *innerhalb* einer Zelle, wenn kein spezieller Schlüssel
   für die Spalte existiert.

   Standard (``string``)
      ``,``


.. option:: csv:mapping

   Enthält Informationen über die Zuordnung von CSV-Spalten zum Benutzerobjekt.
   Ist standardmäßig leer. Siehe :ref:`configuration-mapping`.

   Standard (``object``)
      ``{}``

.. option:: deletion_grace_period

   Dieses Objekt enthält Einstellungen zum Löschen von Benutzern.

   Standard (``object``)
      ``{"deactivation": .., "deletion": ..}``


.. option:: deletion_grace_period:deactivation

   Definiert in wie vielen Tagen ein Benutzer, der nicht mehr in den
   Eingabedaten enthalten ist, deaktiviert (nicht gelöscht) werden soll.

   Wenn ``0`` gesetzt ist, wird das betroffene |UCSUAS|-Benutzerkonto sofort
   deaktiviert.

   Wenn :option:`deletion_grace_period:deletion` auf einen kleineren oder den
   gleichen Wert gesetzt ist, wird das Benutzerobjekt gelöscht statt
   deaktiviert.

   Standard (``int``)
      ``0``

.. option:: deletion_grace_period:deletion

   Definiert die Anzahl der Tage, die nach dem Import vergehen sollen, bevor der
   Benutzer gelöscht aus dem Verzeichnisdienst wird.

   Bei einem Wert von ``0`` wird der Benutzer sofort gelöscht.

   Bei größeren Zahlen wird das geplante Löschdatum im |UCSUDM|-Attribut
   ``ucsschoolPurgeTimestamp`` gesetzt. Ein Cron Job löscht automatisch
   Benutzer, deren geplanter Löschzeitpunkt erreicht ist.

   Standard (``int``)
      ``0``


.. option:: normalize:firstname

   Definiert, ob der in der CSV-Datei angegebene Wert für den Vornamen (i.d.R.
   UTF-8-kodiert) auf die Kodierung ASCII normalisiert wird. Umlaute und
   Sonderzeichen werden dabei ersetzt (``ä`` wird zu ``ae``) oder entfernt.

   Standard (``boolean``)
      ``false``


.. option:: normalize:lastname

   Definiert, ob der in der CSV-Datei angegebene Wert für den Vornamen (i.d.R.
   UTF-8-kodiert) auf die Kodierung ASCII normalisiert wird. Umlaute und
   Sonderzeichen werden dabei ersetzt (``ä`` wird zu ``ae``) oder entfernt.

   Standard (``boolean``)
      ``false``


.. option:: scheme

   Enthält Informationen über die Erzeugung von Werten aus anderen Werten und
   Regeln.

   Es können Ersetzungen wie in den :ref:`users-templates` verwendet werden
   sowie alle Schlüssel aus :option:`csv:mapping`. Neben Formatvorlagen für
   ``email``, ``record_uid`` und ``username`` können Konfigurationen für
   beliebige |UCSUDM|-Attribute hinterlegt werden. ``[ALWAYSCOUNTER]`` und
   ``[COUNTER2]`` werden *nur* in ``scheme:email`` und ``scheme:username``
   verarbeitet.

   Standard (``object``)
      ``{"email": .., "record_uid": .., "username": {..}}``


.. option:: scheme:email

   Schema, aus dem die E-Mailadresse erzeugt werden soll. Zusätzlich zu den in
   :ref:`configuration-scheme-formatting` beschriebenen Ersetzungen kommen noch
   zwei weitere hinzu: ``[ALWAYSCOUNTER]`` und ``[COUNTER2]`` (siehe
   :ref:`configuration-unique-usernames-and-email`).

   Für die Verwendung des ``email``-Schemas ist es erforderlich, dass
   :option:`maildomain` oder die |UCSUCR|-Variable :envvar:`mail/hosteddomains`
   gesetzt ist. Anderenfalls wird keine Mailadresse generiert.

   Standard (``string``)
      ``"<firstname>[0].<lastname>@<maildomain>"``


.. option:: scheme:record_uid

   Schema aus dem die eindeutige ID des Benutzers in der Quelldatenbank
   (Schulverwaltungssoftware) erzeugt werden soll.

   Standard (``string``)
      ``"<email>"``


.. option:: scheme:username

   Enthält Informationen über die Erzeugung von Benutzernamen. Standardmäßig
   enthält das Objekt nur den Schlüssel ``default``.

   Weitere Schlüssel ``student``, ``staff``, ``teacher``, ``teacher_and_staff``
   sind möglich (siehe :ref:`configuration-default-key`).

   Zusätzlich zu den in :ref:`configuration-scheme-formatting` beschriebenen
   Ersetzungen kommen noch zwei weitere hinzu: ``[ALWAYSCOUNTER]`` und
   ``[COUNTER2]`` (siehe :ref:`configuration-unique-usernames-and-email`).

   Standard (``object``)
      ``{"default": ..}``


.. option:: scheme:username:default

   Schema aus dem der Benutzername erzeugt werden soll, wenn kein Schema
   speziell für diesen Benutzertyp (``scheme:username:teacher`` etc.) existiert.

   Standard (``string``)
       ``"<:umlauts><firstname>[0].<lastname>[COUNTER2]"``


.. option:: scheme:<udm attribute name>

   |UCSUDM|-Attribute, die aus einem Schema erzeugt werden sollen. Der Schlüssel
   braucht nicht in :option:`csv:mapping` vorzukommen.

   Standard (``string``)
      nicht gesetzt


.. option:: maildomain

   Der Wert dieser Variable wird beim Formatieren mit einem Schema in die
   Variable ``<maildomain>`` eingesetzt.

   Wenn nicht gesetzt, wird versucht
   ``<maildomain>`` durch Daten aus dem System zu füllen. Dafür wird die
   UCR-Variable :envvar:`mail/hosteddomains` herangezogen. Sind ``maildomain``
   und :envvar:`mail/hosteddomains` nicht gesetzt, werden keine Mailadressen
   automatisch generiert.

   Standard (``string``)
      nicht gesetzt


.. option:: mandatory_attributes

   Liste von |UCSUDM| Attributen, die an jedem Benutzer gesetzt sein müssen.

   Standard (``list``)
      ``["firstname", "lastname", "name", "record_uid", "school", "source_uid"]``


.. option:: no_delete, -m, --no-delete

   Wenn auf ``true`` gesetzt, werden keine Benutzer gelöscht, oder nur solche,
   für die es in den Eingabedaten **explizit** vermerkt ist.

   Dies kann genutzt werden, um eine Änderung an |UCSUAS|-Benutzern vorzunehmen,
   ohne einen vollständigen Soll-Zustand zu übergeben oder um neue Benutzer
   hinzuzufügen.

   Standard (``boolean``)
      ``false``


.. option:: output

   Dieses Objekt enthält Informationen über zu produzierende Dokumente.

   Standard (``object``)
      ``{"import_summary": ..}``


.. option:: output:new_user_passwords

   Diese Variable definiert den Pfad zu der CSV-Datei, in die Passwörter neuer
   Benutzer geschrieben werden.

   Auf den Dateinamen wird die Python-Funktion
   :py:meth:`datetime.datetime.strftime` angewandt. Wenn ein
   :ref:`Python-Format-String <strftime-strptime-behavior>` in ihm vorkommt,
   wird dieser umgewandelt (siehe Beispiel
   :option:`output:user_import_summary`).

   Standard (``string``)
      nicht gesetzt


.. option:: output:user_import_summary

   Diese Variable definiert den Pfad zu der CSV-Datei, in die eine Zusammenfassung
   des Import-Vorganges geschrieben wird. Auf den Dateinamen wird, wie bei
   :option:`output:new_user_passwords`, die Python-Funktion
   :py:meth:`datetime.datetime.strftime` angewandt.

   Standard (``string``)
      ``"/var/lib/ucs-school-import/summary/%Y/%m/user_import_summary_%Y-%m-%d_%H:%M:%S.csv"``


.. option:: password_length

   Definiert die Länge des zufälligen Passwortes, das für neue Benutzer erzeugt
   wird.

   Standard (``int``)
      ``15``

   Abhängig vom Vorhandensein spezifischer Benutzerpasswörter in den Importdaten
   geht der Importvorgang wie folgt mit Passwörtern um:

   Keine Passwörter definiert
      In den Importdaten sind **keine** Passwörter definiert: Der Importvorgang
      erzeugt zufällige Benutzerpasswörter in der konfigurierten Passwortlänge.


   Passwörter definiert
      In den Importdaten sind Benutzerpasswörter definiert:

      a. Länge der Benutzerpasswörter ``< password_length``: Der
         Importvorgang bricht ab mit folgender Meldung:
         ``ucsschool.importer.exceptions.BadPassword: Password is shorter than
         15 characters``.

      #. Länge der Benutzerpasswörter ``> password_length``: Der
         Importvorgang wird durchgeführt. Die Benutzerpasswörter werden auf die
         Länge von ``password_length`` gekürzt.

   Benutzer können zu jedem späteren Zeitpunkt ihr Passwort selbst setzen. Dabei
   greift die :ref:`Passwortrichtlinie für Benutzer <users-passwords>`. Der Wert
   aus ``password_length`` hat keinen Einfluss auf die Passwortrichtlinie. Nur
   der Importvorgang verwendet den Wert aus ``password_length``.

   .. seealso::

      Informationen über Passwortrichtlinien für Benutzer
         :ref:`users-passwords` in :cite:t:`ucs-manual`

.. option:: evaluate_password_policies

     Ab |UCSUAS| Version 5.0 v3: Schaltet die Evaluierung von Passwort Richtlinien während des Imports neuer Benutzer ein.

     Standard (``boolean``)
          ``false``

.. option:: school, -s, --school

   Schulkürzel/OU-Name der Schule, für die der Import sein soll. Dieser Wert
   gilt für alle Benutzer in den Eingabedaten.

   .. caution::

      Der Wert sollte nur gesetzt werden, wenn die Schule nicht über die
      Eingabedaten gesetzt wird.

   Standard (``string``)
      nicht gesetzt


.. option:: source_uid, --source_uid

   Eindeutige und unveränderliche Kennzeichnung der Datenquelle. Muss zwingend
   entweder in einer Konfigurationsdatei oder an der Kommandozeile gesetzt
   werden.

   Standard (``string``)
      nicht gesetzt


.. option:: tolerate_errors

   Definiert die Anzahl an für die Import-Software nicht-kritischen Fehlern,
   die toleriert werden sollen, bevor der Import abgebrochen wird.

   Wird der Wert ``-1`` verwendet, bricht der Import nicht ab und fährt mit dem
   nächsten Eingabedatensatz fort.

   Standard (``int``)
      ``0``


.. option:: user_deletion

   .. deprecated:: 4.2

      Bitte :option:`deletion_grace_period` verwenden.

   Standard (``object``)
      nicht gesetzt


.. option:: user_role, -u, --user_role

   Definiert die Benutzerrolle für alle Eingabedatensätze.

   .. caution::

      Diese Variable sollte nur gesetzt werden, wenn die Benutzerrolle nicht in
      den Eingabedaten enthalten ist und die Eingabedatensätze homogen alle die
      gleiche Benutzerrolle verwenden sollen.

   Erlaubte Werte sind ``student``, ``staff``, ``teacher`` und
   ``teacher_and_staff``.

   Standard (``string``)
      nicht gesetzt


.. option:: username

   Enthält Informationen über die Erzeugung von Benutzernamen.

   Standard (``object``)
      ``{"max_length": {..}``


.. _configuration-json-format-userimport-option-username-max_length:

.. option:: username:max_length

   Enthält Informationen über die Länge von Benutzernamen.

   Standard (``object``)
      ``{"default": .., "student": ..}``


.. option:: username:max_length:default

   Länge eines Benutzernamens, wenn keine Konfiguration speziell für diesen
   Benutzertyp (``username:max_length:staff`` etc.) existiert.

   .. warning::

      Benutzerkonten mit Benutzernamen über 20 Zeichen Länge sind vom Support
      für :program:`Samba`, :program:`Samba 4 Connector` und :program:`Active
      Directory Connector` ausgeschlossen.

      Für eine fehlerfreie Funktionalität von Windows-Clients in der Domäne
      dürfen Benutzernamen nicht über mehr als 20 Zeichen verfügen.

   Der Wert darf den Wert der |UCSUCR|-Variablen
   :envvar:`ucsschool/username/max_length` nicht überschreiten.

   Der Wert von ``username:max_length:student`` wird automatisch berechnet, wenn
   nicht explizit gesetzt. Er muss um die Länge des ``exam-prefix``
   (normalerweise ``exam-``, also ``5``) niedriger sein, als der von
   ``username:max_length:default``.

   Standard (``int``)
      ``20``


.. option:: username:allowed_special_chars

   Enthält die erlaubten Sonderzeichen in Benutzernamen. Außer dem Punkt (``.``)
   sind Bindestrich (``-``) und Unterstrich (``_``) erlaubt. Die Liste wird als
   ein ``string`` dargestellt und wäre für alle drei Zeichen: ``".-_"``.

   Standard (``string``)
      ``"."``


.. option:: school_classes_invalid_character_replacement

   Unerlaubte Zeichen im Namen einer Schulklasse werden mit diesem Wert ersetzt.
   Erlaubt sind Zahlen, Buchstaben (keine Umlaute) und die Zeichen ``. -_``.

   Standard (``string``)
      ``"-"``

