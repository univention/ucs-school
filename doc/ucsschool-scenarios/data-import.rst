.. _import:

***********
Datenimport
***********

Nach Abschluss der Installation der zentralen Systeme sind die Daten in das
LDAP-Verzeichnis zu importieren, die für die Einrichtung und den Betrieb von
Schulen benötigt werden. Dies sind Informationen über die Schulen, die IP-Netze,
Benutzerkonten und weitere Objekte.

Der Datenimport sollte erfolgen, bevor Schulserver und Rechner ausgerollt
werden. Weiterhin sollten die unterschiedlichen Daten in der Reihenfolge
importiert werden, wie sie in diesem Kapitel vorgegeben ist. Darüber hinaus
sollten die Daten, die in CSV-Dateien gespeichert werden, für die spätere
Analyse und Überarbeitung gesichert abgelegt werden.

.. _import-schools:

Schulen
=======

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Im ersten Schritt werden die Schulen importiert. Durch den Datenimport wird im
LDAP-Verzeichnis die Container-Struktur erstellt, die für die späteren Importe
benötigt wird. Um alle Schulen in einem Schritt zu importieren, ist eine
CSV-Datei zu erstellen.

Das Vorgehen zum Import ist wie folgt:

* :download:`Vorlage für den Import </ucsschool-import-vorlagen.xlsx>` öffnen und
  Tabelle *Schulen* ausfüllen.

  * Die Spalten für *Schulkürzel*, *Schulname* und *Server Pädagogik* sind
    Pflichtfelder.

  * Die Spalte *Server Verwaltung* ist optional.

  * Die Spalte *Server Fileshare* bleibt im Normalfall leer. Sie kann in ganz
    bestimmten Fällen ausgefüllt werden.

  .. _fig-import-schools:

  .. figure:: /images/1_schulen_import.png
     :alt: Schulen

     Schulen

* Export der Tabelle ins CSV-Format mit Komma als Trennzeichen für Felder.

  .. _fig-import-schools-save-as:

  .. figure:: /images/2_schulen_save_as.png
     :alt: Kopie speichern als CSV-Datei

     Kopie speichern als CSV-Datei

  .. _fig-import-schools-csv-parameters:

  .. figure:: /images/3_schulen_csv-parameters.png
     :alt: Export Parameter

     Export Parameter

* Die CSV-Datei :file:`schulen.csv` ist auf dem |UCSPRIMARYDN| in folgendem
  Verzeichnis abzulegen: :file:`/usr/local/ucsschool/import_data/`. Das
  Verzeichnis muss ggf. zuerst angelegt werden: :file:`mkdir -p
  /usr/local/ucsschool/import_data`

* Um die CSV-Datei weiterverarbeiten zu können, muss sie im Unix-Format
  vorliegen. Sollte sie auf unter Windows oder macOS gespeichert worden sein, so
  muss sie konvertiert werden. Dazu ist auf dem |UCSPRIMARYDN| der folgende
  Befehl auf die Datei anzuwenden:

  .. code-block:: console


     $ dos2unix schulen.csv

  Vorweg muss das Paket :program:`dos2unix` installiert werden, siehe
  :ref:`software-config-repo` in :cite:t:`ucs-manual`. Nach der Aktivierung des
  Repositories ist der folgende Befehl zu Installation des Pakets auszuführen:

  .. code-block:: console


     $ univention-install dos2unix


  Alternativ kann die Datei auf dem |UCSPRIMARYDN| mit dem Texteditor
  :program:`Vim` geöffnet und dieser zum konvertieren verwendet werden:

  .. code-block:: console

     $ vim schulen.csv
       # In der Vim Befehlszeile:
       :set ff=unix
       :wq

* Die CSV-Datei aus der Vorlage enthält noch zwei Kopfzeilen, die mit dem
  Zeichen ``#`` beginnen, diese müssen vor der weiteren Verarbeitung entfernt
  werden:

  .. code-block:: console

     $ sed -i '1,2d' /usr/local/ucsschool/import_data/schulen.csv


* Der Import kann abschließend mit folgendem Befehl ausgeführt werden:

  .. code-block:: console

     $ /usr/share/ucs-school-import/scripts/create_ou \
       --infile=/usr/local/ucsschool/import_data/schulen.csv

.. _import-networks:

Netze
=====

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Der Import der Netze ist notwendig, um Rechner und Server in den Schulen
einrichten zu können. Beim Import werden unter anderem passende Richtlinien für
DHCP, DNS und Routing erstellt.

Die Netze sind entsprechend der :ref:`concepts-network` in eine CSV-Datei
einzutragen. In `Skriptbasierter Import von Netzwerken
<https://docs.software-univention.de/ucsschool-handbuch-5.0.html#school:schoolcreate:network:import>`_
in :cite:t:`ucsschool-admin` ist das Datenformat für den Import beschrieben.

In der Datei :download:`ucsschool-import-vorlagen.xlsx
</ucsschool-import-vorlagen.xlsx>` ist eine Vorlage in der Tabelle *Netze*
vorhanden, die verwendet werden kann. Es ist zu beachten, dass der
Feldtrennzeichen in diesem Fall *Tabulator* sein muss.

Das weitere Vorgehen ist wie folgt:

* Die CSV-Datei :file:`networks.csv` ist auf dem |UCSPRIMARYDN| in folgendem
  Verzeichnis abzulegen: :file:`/usr/local/ucsschool/import_data/`.

* Die CSV-Datei aus der Vorlage enthält noch zwei Kopfzeilen, die mit dem
  Zeichen ``#`` beginnen, diese müssen vor der weiteren Verarbeitung entfernt
  werden:

  .. code-block:: console

     $ sed -i '1,2d' /usr/local/ucsschool/import_data/networks.csv


* Der Import kann abschließend mit folgendem Befehl ausgeführt werden:

  .. code-block:: console

     $ /usr/share/ucs-school-import/scripts/import_networks \
         /usr/local/ucsschool/import_data/networks.csv


.. _import-clients:

Rechner
=======

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Der Import von Rechnern ist insbesondere notwendig, um die Rechner in den
Schulen mit der richtigen MAC-Adresse in |UCSUAS| zu hinterlegen, so dass diese
über DHCP konfiguriert und in den |UCSUAS| UMC-Modulen verwendet werden können.
Weitere Dienste, wie Softwareverteilungslösungen verwenden diese Informationen
ebenfalls weiter.

Das Datenformat der CSV-Datei ist in `Import von Rechnerkonten für Windows-PCs
<https://docs.software-univention.de/ucsschool-handbuch-5.0.html#school:schoolcreate:computers>`_
in :cite:t:`ucsschool-admin` beschrieben.

Es sollte eine CSV-Datei je Schule erstellt werden, die alle Rechner der
jeweiligen Schule entsprechend des Netz- und Namenskonzeptes enthält.

In der Datei :download:`ucsschool-import-vorlagen.xlsx
</ucsschool-import-vorlagen.xlsx>` ist eine Vorlage in der Tabelle *Rechner*
vorhanden, die verwendet werden kann. Es ist zu beachten, dass der
Feldtrennzeichen in diesem Fall *Tabulator* sein muss.

Das weitere Vorgehen ist wie folgt:

* Die CSV-Datei :file:`computers_SCHULE.csv` ist auf dem |UCSPRIMARYDN| in
  folgendem Verzeichnis abzulegen: :file:`/usr/local/ucsschool/import_data/`

* Die CSV-Datei aus der Vorlage enthält noch zwei Kopfzeilen, die mit dem
  Zeichen ``#`` beginnen, diese müssen vor der weiteren Verarbeitung entfernt
  werden:

  .. code-block:: console

     $ sed -i '1,2d' /usr/local/ucsschool/import_data/computers_SCHULE.csv



* Der Import kann abschließend mit folgendem Befehl ausgeführt werden:

  .. code-block:: console

     $ /usr/share/ucs-school-import/scripts/import_computer \
         /usr/local/ucsschool/import_data/computers_SCHULE.csv


.. _import-printers:

Drucker
=======

.. admonition:: Gültigkeit

   Für Szenario :ref:`3 <scenario-3>` und :ref:`4 <scenario-4>`.

Der Import der Drucker ist notwendig, damit für diese automatisch eine
entsprechende DNS- und DHCP-Konfiguration vorgenommen wird und die Drucker
sofort in der Schule im Netz verfügbar sind.

Das Datenformat der CSV-Datei ist in
`Konfiguration von Druckern an der Schule <https://docs.software-univention.de/ucsschool-handbuch-5.0.html#school:setup:cli:printers>`_ in :cite:t:`ucsschool-admin`
beschrieben.

In der Datei :download:`ucsschool-import-vorlagen.xlsx
</ucsschool-import-vorlagen.xlsx>` ist eine Vorlage in der Tabelle *Drucker*
vorhanden, die verwendet werden kann. Es ist zu beachten, dass der
Feldtrennzeichen in diesem Fall *Tabulator* sein muss.

Das weitere Vorgehen ist wie folgt:

* Die CSV-Datei :file:`printers.csv` ist auf dem |UCSPRIMARYDN| in folgendem
  Verzeichnis abzulegen: :file:`/usr/local/ucsschool/import_data/`

* Die CSV-Datei aus der Vorlage enthält noch zwei Kopfzeilen, die mit dem
  Zeichen ``#`` beginnen, diese müssen vor der weiteren Verarbeitung entfernt
  werden:

  .. code-block:: console

     $ sed -i '1,2d' /usr/local/ucsschool/import_data/printers.csv


* Der Import kann abschließend mit folgendem Befehl ausgeführt werden:

  .. code-block:: console

     $ /usr/share/ucs-school-import/scripts/import_printer \
         /usr/local/ucsschool/import_data/printers.csv


.. _import-users-classes:

Benutzer / Klassen
==================

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Für |UCSUAS| gibt es momentan mehrere Möglichkeiten Nutzer und Klassen in das
System zu importieren.

Die Konfiguration des kommandozeilenbasierten Benutzerimports ist in
:cite:t:`ucsschool-cli-import` dokumentiert.

Die Einrichtung und Verwendung des zugehörigen |UCSUMC| Moduls ist in
:ref:`install-conf-format` in :cite:t:`ucsschool-umc-user-import` nachzulesen.
