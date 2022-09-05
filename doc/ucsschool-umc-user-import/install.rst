.. _install-conf-format:

*******************************************
Installation, Konfiguration und Dateiformat
*******************************************

.. highlight:: console

Installation
============

Die Installation muss auf dem |UCSPRIMARYDN| stattfinden:

.. code-block::

   $ univention-install ucs-school-umc-import

.. _configuration:

Konfiguration
=============

Das Setzen der |UCSUCR|-Variablen :envvar:`ucsschool/import/error/mail-address`
ist wichtig, damit Anwender beim Auftreten eines Fehlers, eine E-Mail an den
Administrator schicken können, indem sie auf den oben beschriebenen Link
klicken.

.. code-block::

   $ ucr set ucsschool/import/error/mail-address=admin@ihre-schule.de


Technisch basiert der grafische Benutzer-Import auf Komponenten der Software die
im :external+uv-ucsschool-import:doc:`Handbuch Import-Schnittstelle <index>`
beschrieben sind. Deren Konfiguration erfolgt in einer JSON Datei. Die Datei
:file:`/usr/share/ucs-school-import/configs/user_import_http-api.json` sollte
als Ausgangsbasis für eigene, angepasste Konfigurationen verwendet werden. Die
Konfiguration wird aktiviert, indem sie an die richtige Position kopiert wird:

.. code-block::

   $ cp /usr/share/ucs-school-import/configs/user_import_http-api.json \
     /var/lib/ucs-school-import/configs/user_import.json

Das Sicherheitskonzept ermöglicht es Benutzern Rechte zu erteilen, um Importe
nur an bestimmten Schulen und nur für bestimmte Benutzertypen durchzuführen,
sowie die Ergebnisse dieser Import-Jobs einzusehen. Während der Installation
wurde für jede Schule eine Gruppe :samp:`{$OU}-import-all` erstellt. An diesen
Gruppen wurde die Option *UCS@school Import-Berechtigungen* aktiviert. In der
UMC können für diese Gruppen auf der Karteikarte *UCS@school*
*Import-Berechtigungen* festgelegt werden.

Eine *Import-Berechtigung* setzt sich zusammen aus einer Liste von Schulen
(standardmäßig nur die Schule für die die Gruppe erzeugt wurde) und einer Liste
von Benutzertypen (Rollen). Alle Benutzer, die Mitglieder dieser Gruppe sind,
können Imports für die aufgelisteten Benutzertypen an den aufgelisteten Schulen
durchführen. Verschachtelte Gruppen werden nicht unterstützt.

Sollen zusätzlich zu den automatisch erzeugten Gruppen neue angelegt werden, so
muss an diesen zum einen die Option *UCS@school Import-Berechtigungen*
aktiviert, und zum anderen die UMC-Richtlinie
:samp:`cn=schoolimport-all,cn=UMC,cn=policies,{$LDAP_BASE}` zugewiesen werden.

Alle an einem Import-Job beteiligten, und von ihm erzeugten, Dateien finden sich
unter :file:`/var/lib/ucs-school-import/jobs/{$JAHR}/{$JOB-ID}/`:
Konfigurationsdateien, Hooks, Logdateien, CSV-Dateien (Eingabedaten, Passwörter
neuer Benutzer, Zusammenfassung).

.. note::

   Sollte auf dem |UCSPRIMARYDN| ein SSL-Zertifikat mit abweichenden FQDNs
   verwendet werden, wird beim Öffnen des UMC-Moduls *Benutzerimport* eine
   Fehlermeldung auftauchen, da der lokale Rechnername nicht mit den
   Rechnernamen im SSL-Zertifikat übereinstimmt. In diesem Fall muss die
   UCR-Variable :envvar:`ucsschool/import/http_api/client/server` entsprechend
   auf den/einen Rechnernamen (FQDN) des SSL-Zertifikats gesetzt werden.

   Zusätzlich sollte die UCR-Variable
   :envvar:`ucsschool/import/http_api/ALLOWED_HOSTS` den lokalen FQDN sowie den
   im SSL-Zertifikat verwendeten FQDN enthalten.

   Nach dem Setzen der beiden
   UCR-Variablen müssen einige Dienste neu gestartet werden:

   .. code-block:: console

      $ systemctl restart ucs-school-import-http-api ucs-school-import-celery-worker

.. _file-format:

Datenformat
===========

Das Format der CSV-Datei ist anpassbar. Generell gilt aber folgendes:

* Die erste Zeile führt die Bezeichner der Spalten auf. Zum Beispiel:

  .. code-block::

     "Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"


* Daten in Spalten sind in doppelten Anführungszeichen eingeschlossen.

* Die Spalten sind durch Komma voneinander getrennt.

* Es muss jeweils eine Spalte für die primäre Schule eines Benutzers, seinen
  Vor- und Nachnamen geben.

* Mehrere Klassennamen werden durch Komma, ohne Freizeichen, getrennt aufgezählt
  (z.B. ``1a,2b,3c``). Klassennamen dürfen, aber brauchen nicht, den Namen der
  Schule (mit einem Bindestrich verbunden) vorangestellt haben (z.B.
  ``Scholl-1a,Scholl-2b,Scholl-3c``). Wird der Name der Schule vorangestellt,
  *muss* dies der gleiche Wert sein wie in der Spalte für die Schule.

.. caution::

   Für die Aufbereitung der Daten ist es besonders wichtig darauf zu achten,
   dass Benutzern in der Rolle Schüler immer eine Schulklasse zugewiesen ist.
   Benutzerkontodaten werden an anderen Stellen weiter verarbeitet.

   Wenn die Angabe für die Schulklasse eines Schülers fehlt, kann die
   Weiterverarbeitung gestört werden.

   Detaillierte Informationen wie sich Benutzerkonten UCS@school von UCS
   unterschieden, finden sich im :uv:kb:`Knowledge Base Artikel "How a
   UCS@school user should look like" <15630>`.

Beispieldaten für Testläufe können mit Hilfe eines Skripts erzeugt werden:

.. code-block::

   $ /usr/share/ucs-school-import/scripts/ucs-school-testuser-import \
     --httpapi \                 # Format passend zu user_import_http-api.json erzeugen
     --students 20 \             # Anzahl Benutzer, alternativ: --staff --teachers --staffteachers
     --classes 2 \               # Anzahl zu erzeugender Klassen
     --create-email-addresses \  # E-Mail-Adressen erzeugen
     SchuleEins                  # Schule (OU) in die importiert werden soll


Die erzeugte Datei heißt :samp:`test_users_{$DATUM_$UHRZEIT}.csv` und passt zur
Konfiguration in
:file:`/usr/share/ucs-school-import/configs/ucs-school-testuser-http-import.json`.

Eine solche Datei sieht z.B. so aus:

.. code-block::

   "Schule","Vorname","Nachname","Klassen","Beschreibung","Telefon","EMail"
   "SchuleEins","Jeanne","Oberbockstruck","1a","A student.","+24-165-622645","jeannem.oberbockstruck@example.de"
   "SchuleEins","Jehanne","Obergöker","1b","A student.","+16-456-810331","jehannem.mobergoeker@example.de"
   "SchuleEins","Çetin","Schrage","1a","A student.","+93-982-722661","cetinm.schrage@example.de"
   "SchuleEins","Zwenna","Schomaker","1b","A student.","+39-504-246300","zwennam.schomakerm@example.de"
