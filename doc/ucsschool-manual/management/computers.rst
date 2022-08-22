.. _school-setup-umc-computers:

Verwaltung von Rechnern
=======================

Für die Anbindung von Arbeitsplatzrechnern in Form von z.B. Windows-Rechnern
werden im Verzeichnisdienst Rechnerkonten benötigt.

Rechnerkonten werden z.B. von Windows-Rechnern automatisch beim Domänenbeitritt
angelegt. Sie können aber auch vor dem Domänenbeitritt manuell über das
UMC-Modul *Rechner (Schulen)* eingepflegt werden. Dies ist unter anderem für
*IP-Managed-Clients* wie z.B. Netzwerkdrucker notwendig.

Das Anlegen der Rechnerkonten vor der Inbetriebnahme bringt den Vorteil, dass
z.B. die für DHCP notwendigen Informationen wie IP- und MAC-Adresse schon
hinterlegt sind.

.. _school-setup-umc-computers-create:

Anlegen von Rechnerkonten
-------------------------

Im zentralen Suchdialog des UMC-Moduls ist oberhalb der Tabelle die Schaltfläche
:guilabel:`Hinzufügen` auszuwählen, um den Assistenten für ein neues
Rechnerkonto zu starten.

Sind mehrere Schulen in der |UCSUAS|-Umgebung eingerichtet, ist zunächst
auszuwählen, in welcher Schule das Rechnerkonto angelegt werden soll. Wurde nur
eine Schule eingerichtet, wird dieses Auswahlfeld automatisch ausgeblendet.

Im Auswahlfeld *Rechnertyp* stehen bis zu vier Rechnertypen zur Auswahl:

* ``Windows-System`` für Windows-Rechner ab Windows XP

* ``Mac OS X``

* ``Gerät mit IP-Adresse`` für z.B. Netzwerkdrucker mit eigener IP-Adresse

Auf der nächste Seite des Assistenten müssen folgende Attribute des neuen
Rechnerkontos angegeben werden:

* *Name*,
* *IP-Adresse*
* *MAC-Adresse*

Um Probleme beim Domänenbeitritt zu vermeiden, muss der Name des Rechnerkontos
mit dem Namen des Rechners übereinstimmen. Die *Subnetzmaske* kann in den
meisten Fällen auf der Voreinstellung belassen werden. Die MAC-Adresse wird
unter anderem für die statische Vergabe der IP-Adressen per DHCP verwendet. Die
Angabe der Inventarnummer ist optional.

.. note::

   Als IP-Adresse kann auch die Adresse des Subnetzes angegeben werden (z.B.
   ``192.168.2.0`` bei einer Subnetzmaske von ``255.255.255.0``). Der Assistent
   wählt dann automatisch eine freie IP-Adresse aus dem angegebenen Subnetz aus
   (z.B. ``192.168.2.20``) und weist sie dem neuen Rechnerkonto zu.

.. _school-setup-umc-computers-modify:

Bearbeiten von Rechnerkonten
----------------------------

Zum Bearbeiten eines Rechnerkontos ist dieses in der Tabelle auszuwählen
und die Schaltfläche :guilabel:`Bearbeiten` anzuklicken. Im
folgenden Dialog können IP-Adresse, MAC-Adresse, Subnetzmaske und
Inventarnummer angepasst werden.

Das Bearbeiten des Rechnernamens ist nicht möglich.

Sofern der angemeldete UMC-Benutzer die Rechte für das UMC-Modul *Rechner* aus
der Modulgruppe *Domäne* besitzt, wird zusätzlich die Schaltfläche *Erweiterte
Einstellungen* angezeigt. Über sie kann das UMC-Modul *Rechner* geöffnet werden,
in dem viele erweiterte Einstellungen für das Rechnerkonto möglich sind.

.. _school-setup-umc-computers-delete:

Löschen von Rechnerkonten
-------------------------

Zum Löschen von Rechnerkonten sind diese in der Tabelle auszuwählen und
anschließend die Schaltfläche :guilabel:`Löschen` anzuklicken. Nach dem
Bestätigen werden die Rechnerkonten aus dem Verzeichnisdienst entfernt.
