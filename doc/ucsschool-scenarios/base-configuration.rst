.. _base-configuration:

******************
Basiskonfiguration
******************

.. admonition:: Gültigkeit

   Für :ref:`alle <scenarios>` Szenarien.

Folgende Konfigurationen müssen **vor** dem Anlegen der ersten Schulen umgesetzt
werden.

.. _base-configuration-mail:

Zustellung von Systemmails
==========================

|UCSUCS| verschickt regelmäßig E-Mails, um aktuelle Ereignisse aus dem
Monitoring und Ergebnisse von Routineaufgaben zu kommunizieren. Diese E-Mails
sind für den Betrieb von großer Wichtigkeit und müssen unbedingt beachtet
werden. Damit diese E-Mail zugestellt werden können, ist der E-Mailversand wie
folgt zu konfigurieren.

Um eine einfache und homogene Konfiguration der |UCSUCR|-Variablen zu erreichen,
sollten |UCSUCR|-Richtlinien verwendet werden.

#. E-Mailalias für ``root`` auf ein System stellen/umleiten: Wenn zum Beispiel
   alle E-Mails an den Benutzer ``root`` an den |UCSPRIMARYDN| umgeleitet werden
   sollen, ist die |UCSUCR|-Variable :envvar:`mail/alias/root` auf den Wert
   ``root@ucsrz01.example.org`` zu stellen. ``example.org`` muss durch den
   tatsächlichen Domänennamen ersetzt werden.

#. Anschließend ist auf dem Zielsystem, in diesem Beispiel auf dem
   |UCSPRIMARYDN|, die Zieladresse für alle E-Mails an ``root`` zu hinterlegen.
   Die E-Mailadresse wird ebenfalls über |UCSUCR|-Variable
   :envvar:`mail/alias/root` festgelegt, zum Beispiel ``admins@example.org``.

#. Damit das Zielsystem die E-Mail annehmen kann, ist auf dem Zielsystem die App
   :program:`Mailserver` zu installieren. Außerdem ist der Zugang zu einem
   entfernten Mailserver zu konfigurieren, über den die E-Mails zugestellt
   werden können. Die :ref:`mail-serverconfig-relay` ist in :cite:t:`ucs-manual`
   beschrieben.

#. Mit dieser Konfiguration werden alle E-Mails, die auf einem beliebigen Server
   an den Benutzer ``root`` geschickt
   werden, an die konfigurierte E-Mailadresse weitergeleitet.

   Es ist sinnvoll zu prüfen, ob es weitere lokale Konten von Systembenutzern
   gibt, die E-Mails erhalten. Diese sollte alle auf den Benutzer ``root``
   umgeleitet werden. Insbesondere sind die |UCSUCR|-Variablen
   :envvar:`mail/alias/postmaster` und :envvar:`mail/alias/webmaster` auf den
   Wert ``root`` zu setzen.

.. _base-configuration-globale-ucr:
.. _table-global-ucr-settings:


Globale |UCSUCR|-Richtlinie
===========================

Die globale |UCSUCR|-Richtlinie wird in der |UCSUMC| über die Kategorie *Domäne*
und das Modul *Richtlinien* bearbeitet. Die Richtlinie hat den Namen
:command:`ucsschool-ucr-settings` und ist vom Typ |UCSUCR|. Um folgende Einträge
sollte die Richtlinie erweitert werden:

.. envvar:: directory/manager/web/module/autosearch

   Deaktiviert die automatische Suche nach allen Objekten beim Öffnen der
   |UCSUDM|-Module. Dies beschleunigt das Arbeiten mit vielen LDAP-Objekten.

   Wert: ``0``


.. envvar:: ucsschool/wizards/autosearch

   Deaktiviert die automatische Suche nach allen Objekten beim Öffnen der
   |UCSUAS|-Module. Dies beschleunigt das Arbeiten mit vielen LDAP-Objekten.

   Wert: ``false``


.. envvar:: ucsschool/assign-teachers/autosearch

   Deaktiviert die automatische Suche nach allen Objekten beim Öffnen des
   |UCSUAS|-Moduls zum Zuweisen von Lehrkräften. Dies beschleunigt das Arbeiten
   mit vielen LDAP-Objekten.

   Wert: ``false``


.. envvar:: ucsschool/assign-classes/autosearch

   Deaktiviert die automatische Suche nach allen Objekten beim Öffnen des
   |UCSUAS|-Moduls zum Zuweisen von Klassen. Dies beschleunigt das Arbeiten mit
   vielen LDAP-Objekten.

   Wert: ``false``


.. envvar:: ucsschool/workgroups/autosearch

   Deaktiviert die automatische Suche nach allen Objekten beim Öffnen des
   |UCSUAS|-Moduls zum Bearbeiten von Arbeitsgruppen. Dies beschleunigt das
   Arbeiten mit vielen LDAP-Objekten.

   Wert: ``false``


.. envvar:: ucsschool/passwordreset/autosearch

   Deaktiviert die automatische Suche nach allen Objekten beim Öffnen des
   |UCSUAS|-Moduls zum Zurücksetzen von Passwörtern. Dies beschleunigt das
   Arbeiten mit vielen LDAP-Objekten.

   Wert: ``false``


.. envvar:: ucsschool/passwordreset/autosearch_on_change

   Deaktiviert die automatische Suche nach allen Objekten im |UCSUAS|-Modul zum
   Zurücksetzen von Passwörtern nachdem der Suchfilter geändert wurde. Dies
   vereinheitlicht das Verhalten der |UCSUAS|-Module, kann bei Bedarf aber auch
   auf dem Standardwert belassen bzw. nicht angepasst werden.

   Wert: ``false``


.. envvar:: samba4/sysvol/sync/from_downstream

   Konfiguriert die SYSVOL-Replikation unidirektional vom |UCSPRIMARYDN| zu den
   |UCSUAS| Schulservern. Dies beugt Problemen mit der Replikation vor.

   Wert: ``false``


.. envvar:: samba4/sysvol/sync/from_upstream/delete

   Konfiguriert die SYSVOL-Replikation unidirektional vom |UCSPRIMARYDN| zu den
   |UCSUAS| Schulservern. Dies beugt Problemen mit der Replikation vor.

   Wert: ``true``


.. envvar:: nagios/client/allowedhosts

   Erlaubt den Zugriff des Monitoring-Servers, :program:`Nagios`, auf den
   *NRPE-Dienst* der übrigen Systeme.

   Wert: ``[IP-Adresse des Monitoring Servers, zum Beispiel 10.0.0.20]``

.. envvar:: ucsschool/helpdesk/recipient

   Definiert die E-Mailadresse, an die Nachrichten vom |UCSUAS| Helpdesk-Modul
   geschickt werden. Die Zustellung sollte unbedingt getestet werden! Siehe auch
   :ref:`base-configuration-mail`.

   Wert: ``[E-Mailadresse des Helpdesks, zum Beispiel admins@example.org]``


.. envvar:: mail/alias/root

   Definiert die E-Mailadresse für Systemmails (Cron / Monitoring). Die
   Zustellung sollte unbedingt getestet werden! Siehe auch
   :ref:`base-configuration-mail`.

   Wert: ``[E-Mailadresse des Betreibers, zum Beispiel admins@example.org]``


.. envvar:: ucsschool/import/generate/policy/dhcp/dns/set_per_ou

   Verhindert das automatische Anlegen bestimmter DHCP-DNS-Richtlinien für den
   Edukativ-Bereich der Schulen. Bei der Verwendung des Verwaltungsnetzes ist
   dies hinderlich. Die notwendigen DHCP-Richtlinien werden später durch den
   Netzimport korrekt angelegt

   Wert: ``false``

.. _base-configuration-central-ucr:

Zentrale |UCSUCR|-Richtlinie
============================

Eine |UCSUCR|-Richtlinie für die zentralen Server wird benötigt, um
sicherzustellen, dass die Konfigurationen der Server gleichartig sind.
Dazu ist in der |UCSUMC| über die Kategorie *Domäne*
und das Modul *Richtlinien* zu öffnen und die
zentrale Richtlinie anzulegen.

Dazu wird eine neue Richtlinie vom Typ |UCSUCR| im Container
``policies/config-registry`` erstellt. Die Richtlinie soll
``ucr_central`` heißen und folgende Einträge
enthalten:

.. list-table:: UCR-Variablen zur Zeitserver-Konfiguration
   :name: table-central-ucr-settings
   :header-rows: 1
   :widths: 2 5 5

   * - UCR-Variable
     - Wert
     - Beschreibung

   * - :envvar:`timeserver`
     - ``[FQDN oder IP-Adresse des ersten externen Zeitservers]``
     - Zeitserver von dem die gesamte Domäne ihre Uhrzeit bezieht. Beispiele:
       ``ptbtime1.ptb.de`` oder ``0.europe.pool.n tp.org``.

   * - :envvar:`timeserver2`
     - ``[FQDN oder IP-Adresse des zweiten externen Zeitservers]``
     - Zeitserver von dem die gesamte Domäne ihre Uhrzeit bezieht. Beispiele:
       ``ptbtime1.ptb.de`` oder ``0.europe.pool.n tp.org``.

   * - :envvar:`timeserver3`
     - ``[FQDN oder IP-Adresse des dritten externen Zeitservers]``
     - Zeitserver von dem die gesamte Domäne ihre Uhrzeit bezieht. Beispiele:
       ``ptbtime1.ptb.de`` oder ``0.europe.pool.n tp.org``.

.. note::

   Die |UCSUAS| Schulserver setzen automatisch den |UCSPRIMARYDN| und die
   |UCSBACKUPDN|-Server als Zeitserver. Damit wird automatisch eine Kaskadierung
   erreicht.

Abschließend ist die Richtlinie mit den zentralen Servern zu verknüpfen. In der
|UCSUMC| ist dazu in der Kategorie *Domäne* das Modul *LDAP-Verzeichnis*
auszuwählen und der Container ``computers`` zu öffnen. Nun ist mit der rechten
Maustaste der Container anzuklicken und die Option
*Bearbeiten* zu selektieren.

Auf Reiter Richtlinien ist nun der Punkt *Richtlinie: Univention Configuration
Registry* zu öffnen und als dem Dropdown *Richtlinien-Konfiguration* die eben
erstellte Richtlinie ``ucr_central`` auszuwählen.

Die Richtlinie wird nun auf alle Systeme unterhalb des Containers ``computer``
vererbt.
