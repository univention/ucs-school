.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-setup-umc-schools:

Verwaltung von Schulen
======================

Die Daten einer Schule werden in einer Organisationseinheit (OU) - einem
Teilbaum des LDAP-Verzeichnisdienstes - gespeichert (siehe auch
:ref:`structure`). Die Verwaltung der logischen Einheit *Schule* kann in der
|UCSUMC| über das Modul *Schulen* erfolgen, welches sich in der Modulgruppe
*Schul-Administration* befindet. Es ermöglicht das Suchen nach, sowie das
Anlegen, Bearbeiten und Löschen von Schulen in der |UCSUAS|-Umgebung.

Bevor ein neuer Schulserver der |UCSUAS|-Domäne beitreten kann, muss die
dazugehörige Schule angelegt werden.

.. _school-setup-umc-schools-create:

Anlegen von Schulen
-------------------

Um den Assistenten für das Hinzufügen einer neuen Schule zu starten, ist
die Schaltfläche :guilabel:`Hinzufügen` oberhalb der Tabelle
auszuwählen. Bei Neuinstallationen ohne bestehende Schulen fragt das
UMC-Modul automatisch beim Öffnen, ob jetzt die erste Schule angelegt
werden soll.

Der Assistent fragt in jeder |UCSUAS|-Umgebung mindestens die beiden Werte *Name
der Schule* und *Schulkürzel* ab. In Multi-Server-Umgebungen wird zusätzlich der
Name des edukativen Schulservers abgefragt, welcher später die Dienste für die
neue Schule bereitstellen soll.

Im Eingabefeld *Name der Schule* ist eine beliebige Beschreibung für die Schule
(z.B. *Gymnasium Mitte*) anzugeben, die keiner Zeichenlimitierung unterliegt.
Sie wird später in den |UCSUAS|-Modulen angezeigt, wenn zwischen
unterschiedlichen Schulen zu wählen ist. Nachdem ein Wert eingetragen wurde,
wird beim Wechsel in das nächste Eingabefeld automatisch ein Vorschlag für das
*Schulkürzel* generiert.

Das Schulkürzel ist i.d.R. ein kurzer Bezeichner für die Schule, der sich später
an unterschiedlichen Stellen wiederfindet. Es wird automatisch u.a. als Präfix
für Gruppen- und Freigabenamen verwendet. Darüber hinaus wird das Schulkürzel
als Name für die Organisationseinheit (OU) im Verzeichnisdienst verwendet.
Häufig kommen hier Schulnummern wie ``340`` oder zusammengesetzte Kürzel wie
``g123m`` oder ``gymmitte`` zum Einsatz.

In Single-Server-Umgebungen ist die Angabe eines Rechnernamens für Schulserver
nicht erforderlich, während in Multi-Server-Umgebungen der
*Rechnername des Schulservers* angegeben werden muss. Der eingetragene
Schulserver wird automatisch als Dateiserver für Klassen- und Benutzerfreigaben
verwendet (siehe :ref:`school-setup-generic-windows-attributes` und
:ref:`school-windows-shares`). Optional kann auch der :guilabel:`Rechnername des
Verwaltungsservers` angegeben werden, sofern dieser verwendet werden soll.

Nach dem erfolgreichen Anlegen der Schule über die Schaltfläche
:guilabel:`Speichern` erscheint eine Statusmeldung im oberen Teil der |UCSUMC|.

.. caution::

   Bei Schulservern bzw. Verwaltungsservern muss die Schule
   **vor** dem Domänenbeitritt des Systems angelegt
   und der Rechnername des Schulservers bzw. Verwaltungsservers an der
   Schule hinterlegt werden.

   Stimmen hinterlegter Rechnername und der Name des beitretenden Systems nicht
   überein, wird ein |UCSREPLICADN| ohne |UCSUAS|-Funktionalität installiert und
   eingerichtet.

.. important::

   Das Schulkürzel darf ausschließlich aus Buchstaben (``a-z`` und ``A-Z``),
   Ziffern (``0-9``) und dem Bindestrich (``-``) bestehen, da es unter anderem
   die Grundlage für Gruppen-, Freigabe- und Rechnernamen bildet.

   Der Name des Schulservers bzw. Verwaltungsservers darf nur aus
   Kleinbuchstaben, Ziffern sowie dem Bindestrich bestehen (``a-z``, ``0-9`` und
   ``-``). Der Name darf nur mit einem Kleinbuchstaben beginnen, mit einem
   Kleinbuchstaben oder einer Ziffer enden und ist auf eine Länge von 12 Zeichen
   beschränkt. Bei Abweichungen von diesen Vorgaben kann es zu Problemen bei der
   Verwendung von Windows-Clients kommen.

.. _school-setup-umc-schools-schoolserver-multiple-ous:

Mehrere Schulen auf einem Schulserver verwalten
-----------------------------------------------

Wie in :ref:`structure-ou-schoolserver-multiple-ous` bereits
beschrieben wurde, können mehrere Schulen auf einen Schulserver
repliziert werden. Für die Einrichtung sind zusätzliche Schritte
notwendig, die nachfolgend beschrieben werden:

* In der UMC kann die Zuweisung eines Schulservers zu einer Schule nur beim
  Anlegen der Schule erfolgen. Damit mehrere Schulen vom gleichen Schulserver
  verwaltet werden, muss beim Anlegen der betreffenden Schulen im Feld
  *Rechnername des Schulservers im Edukativnetz* der gleiche Name des
  Schulservers angegeben werden (siehe :ref:`fig-umc-multi-ou-create`).

  Auf der Kommandozeile ist die Zuweisung über das Kommando :command:`create_ou`
  beim Anlegen einer Schule möglich. Im folgenden Beispiel werden die Schulen
  ``gymwest`` und ``bswest`` angelegt, die den Schulserver ``dcwest`` verwenden
  sollen.

  .. code-block:: console

     $ cd /usr/share/ucs-school-import/scripts/
     $ ./create_ou gymwest dcwest
     $ ./create_ou bswest dcwest


  .. _fig-umc-multi-ou-create:

  .. figure:: /images/umc-multi-ou-create.png
     :alt: Anlegen einer neuen Schule

     Anlegen einer neuen Schule

* Nach dem Anlegen der Schulen bzw. dem Zuweisen der Schulserver zu den Schulen
  ist im UMC-Modul *Schulen* die betreffende Schule zu öffnen und dort unter
  *Erweiterte Einstellungen* zu prüfen, ob die korrekten Dateiserver für
  Heimatverzeichnisse und Klassenfreigaben hinterlegt sind (siehe
  :ref:`fig-umc-multi-ou-modify`). Diese Werte sind auch zu prüfen, wenn diese
  in der Vergangenheit bereits korrekt waren, da sie ggf. während der
  Schulserver-Zuweisung neu gesetzt werden.

  .. _fig-umc-multi-ou-modify:

  .. figure:: /images/umc-multi-ou-modify.png
     :alt: Das Setzen von Dateiservern für eine Schule

     Das Setzen von Dateiservern für eine Schule

* Es ist zu beachten, dass bereits während des Anlegens einer neuen Schule für
  den betroffenen Schulserver neue Zugriffsberechtigungen auf das
  LDAP-Verzeichnis gesetzt werden, die den laufenden Betrieb auf einem
  Schulserver negativ beeinflussen können. Die Zuweisung bzw. das Anlegen der
  Schule sollte daher in einem geeigneten Wartungsfenster stattfinden.

  Falls ein bereits existierender Schulserver einer weiteren Schule zugewiesen
  wurde, der bereits erfolgreich der |UCSUAS|-Domäne beigetreten ist, *muss*
  dieser Schulserver den Domänenbeitritt erneut durchführen, um einen
  konsistenten Zustand des LDAP-Verzeichnisses auf dem Schulserver herzustellen.

.. warning::

   Die Verwendung des DHCP-Servers auf einem Schulserver, dem mehrere
   Schulen zugewiesen wurden, wird nicht unterstützt.

.. _school-setup-umc-schools-modify:

Bearbeiten von Schulen
----------------------

Zum Bearbeiten einer bestimmten Schule ist diese in der Tabelle
auszuwählen und die Schaltfläche :guilabel:`Bearbeiten`
anzuklicken. Im folgenden Dialog kann der Name der Schule angepasst
werden. Das nachträgliche Ändern des Schulkürzels ist nicht möglich.

Darüber hinaus können durch einen Klick auf *Erweiterte Einstellungen* die für
die Schule zuständigen Freigabeserver eingesehen und modifiziert werden. Die
genaue Funktion dieser Freigabeserver wird in
:ref:`school-setup-generic-windows-attributes` und :ref:`school-windows-shares`
beschrieben.

Das nachträgliche Hinzufügen von Schulservern für das Verwaltungsnetz
ist derzeit nicht über die UMC möglich. Auf der Kommandozeile kann dies
jedoch über das Tool :command:`create_ou` erreicht werden.
Diesem Tool sind als Parameter der OU-Name, der Rechnername des
existierenden Schulservers im Edukativnetz und der noch fehlende
Rechnername für den Schulserver im Verwaltungsnetz zu übergeben.

Im folgenden Beispiel wird für die Schule ``gymmitte``, die bereits den
Schulserver ``dcgymmitte`` im Edukativnetz einsetzt, zusätzlich der Schulserver
``admgymmitte`` für das Verwaltungsnetz hinterlegt:

.. code-block:: console

   $ cd /usr/share/ucs-school-import/scripts/
   $ ./create_ou gsmitte dcgymmitte admgymmitte


.. _school-setup-umc-schools-delete:

Löschen von Schulen
-------------------

Zum Löschen einer bestimmten Schule ist diese in der Tabelle auszuwählen
und die Schaltfläche :guilabel:`Löschen` anzuklicken.

.. danger::

   Das Löschen einer Schule umfasst auch das unwiderrufliche Entfernen aller
   damit verbundenen Objekte wie Benutzerkonten, Klassen, Arbeitsgruppen,
   Rechner, DHCP-Leases, Drucker und Freigaben.

   Das Löschen einer Schule kann nicht rückgängig gemacht werden.
