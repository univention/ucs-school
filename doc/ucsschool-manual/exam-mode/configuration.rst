.. _school-exam-configuration:

Konfiguration
=============

Für die Konfiguration des Klassenarbeitsmodus gibt es eine Reihe von
|UCSUCRV|\ n. Diese werden im folgenden aufgelistet und kurz erläutert.

Die nachfolgenden |UCSUCRV|\ n können geändert werden, um LDAP-Eigenschaften
der Klassenarbeitskonten, -gruppen und -container anzupassen. Sofern
diese Variablen manuell gesetzt werden, ist zu beachten, dass es sich
dabei um globale Einstellungen handelt und diese Variablen sowohl auf
dem |UCSPRIMARYDN| als auch auf den Schulservern identische Werte
aufweisen müssen.

.. envvar:: ucsschool/ldap/default/userprefix/exam

   Gibt den Präfix an, der dem ursprünglichen Benutzernamen im
   Klassenarbeitskonto vorangestellt wird. Er ist standardmäßig auf ``exam-``
   gesetzt.

.. envvar:: ucsschool/ldap/default/groupname/exam`

   Bezeichnet die Gruppe, der alle Klassenarbeitskonten sowie
   Klassenarbeitsrechner zugeordnet sind. Über diese Gruppe können spezifische
   Windows-Gruppenrichtlinien für den Klassenarbeitsmodus gesetzt werden. Der
   Standardname für diese Gruppe ist ``OU%(ou)s-Klassenarbeit``, wobei
   ``%(ou)s`` vom System automatisch durch den Namen der OU ausgetauscht wird.

.. envvar:: ucsschool/ldap/default/container/exam

   Definiert den Namen des Containers, unterhalb dem die Klassenarbeitskonten
   gespeichert werden. Standardmäßig ist der Name auf ``examusers`` gesetzt. Die
   LDAP-Position des Containers ist direkt unterhalb der Schul-OU.

.. envvar:: ucsschool/exam/user/homedir/autoremove

   Definiert, ob beim automatischen Löschen der Prüfungsbenutzer auch deren
   Heimatverzeichnis gelöscht werden soll. Der Standard ist ``no``.

.. envvar:: ucsschool/exam/user/disable

   Definiert, ob der originale Benutzer während einer Klassenarbeit deaktiviert
   werden soll, um die Nutzung anderer Dienste zu verhindern. Der Standard ist
   ``no``.

   Es empfiehlt sich, das Verhalten nach der Deaktivierung eines Benutzers in
   allen installierten Apps vorher zu überprüfen.

Das UMC-Modul zum Einrichten einer Klassenarbeit bietet die Möglichkeit
bestimmte Standardwerte zu definieren, um das Starten einer Klassenarbeit zu
vereinfachen. Dazu gehören:

.. envvar:: ucsschool/exam/default/room

   Definiert den vorausgewählten Raum für eine neue Klassenarbeit. Der Eintrag
   beinhaltet den LDAP-Namen des Raumes (inklusive des Schul-OU-Präfxies), also
   bspw. ``meineschule-PC Raum``. Ist die Variable nicht gesetzt, wird kein Raum
   vorausgewählt.

.. envvar:: ucsschool/exam/default/shares

   Gibt den vorausgewählten Freigabezugriff für eine neue Klassenarbeit an.
   Mögliche Werte sind:

   * ``all``: Zugriff auf alle Freigaben ohne Einschränkungen

   * ``home``: Eingeschränkten Zugriff auf lediglich das Heimatverzeichnis des
     (Klassenarbeits-)Benutzerkontos

   Ist die Variable nicht gesetzt, wird standardmäßig nur der Zugriff auf das
   Homeverzeichnis freigegeben.

.. envvar:: ucsschool/exam/default/internet

   Definiert die vorausgewählte Internetregel für eine neue Klassenarbeit.
   Mögliche Werte umfassen die Namen aller Internetregeln wie sie im UMC-Modul
   *Internetregeln definieren* angezeigt werden.

   Normalerweise werden die globalen Standardeinstellungen verwendet.

.. envvar:: ucsschool/exam/default/checkbox/distribution

   Definiert, ob beim Starten des Klassenarbeitsmodus das Auswahlkästchen
   *Unterrichtsmaterial verteilen* automatisch vorausgewählt ist. Mögliche Werte
   sind:

   * ``true``: Auswahlkästchen vorausgewählt

   * ``false``: Auswahlkästchen nicht vorausgewählt

.. envvar:: ucsschool/exam/default/checkbox/proxysettings

   Definiert, ob beim Starten des Klassenarbeitsmodus das Auswahlkästchen
   *Internetregeln definieren* automatisch vorausgewählt ist. Mögliche
   Werte sind:

   * ``true``: Auswahlkästchen vorausgewählt

   * ``false``: Auswahlkästchen nicht vorausgewählt

.. envvar:: ucsschool/exam/default/checkbox/sharesettings

   Definiert, ob beim Starten des Klassenarbeitsmodus das Auswahlkästchen
   *Freigabezugriff konfigurieren* automatisch vorausgewählt ist. Mögliche Werte
   sind:

   * ``true``: Auswahlkästchen vorausgewählt

   * ``false``: Auswahlkästchen nicht vorausgewählt

.. envvar:: ucsschool/exam/default/show/restart

   Definiert, ob die Seite zum Neustarten der Schülerrechner angezeigt werden
   soll. Standardmäßig deaktiviert.

Mit |UCSUAS| 4.4v3 gibt es die Möglichkeit in regelmäßigen Abständen
Sicherungskopien aller Schülerdaten zu speichern, während sie sich in einer
Klassenarbeit befinden. Diese Sicherungskopien werden in einem separaten Ordner
im Heimatverzeichnis des Lehrers gespeichert, welcher die Klassenarbeit
durchführt. Diese Funktionalität ist in dieser Version standardmäßig deaktiviert
und kann über die folgenden |UCSUCRV|\ n konfiguriert werden:

.. envvar:: ucsschool/exam/cron/backup/activated

   Definiert, ob das Skript :command:`exam-backup` automatisch durch Cron
   gestartet wird. Standardmäßig deaktiviert.

.. envvar:: ucsschool/exam/cron/backup

   Definiert den Zeitpunkt, an dem das Skript :command:`exam-backup` automatisch
   durch Cron gestartet wird. Standardmäßig alle 5 Minuten; Beispiel: ``*/5 * *
   * *``)

.. envvar:: ucsschool/exam/backup/compress

   Definiert, ob das Backup der Daten eines Schülers während einer Klassenarbeit
   komprimiert werden soll. Standardmäßig aktiviert.

.. envvar:: ucsschool/exam/backup/limit

   Definiert die maximale Anzahl an Zwischenergebnissen, die pro Schüler und
   Klassenarbeit gespeichert werden. Der Standardwert ist ``40`` und muss
   mindestens ``1`` sein. Wenn das Limit erreicht ist, werden keine weiteren
   Backups gespeichert.

   .. caution::

      Wenn diese Funktionalität aktiviert wird, sollte dabei dringend der Bedarf
      an Speicherplatz berücksichtigt werden, der hier anfällt.

      Sollte beispielsweise eine Klasse von 25 Schülern eine 45 Minuten dauernde
      Klassenarbeit schreiben und es werden dabei alle 5 Minuten ungefähr 10 MB
      pro Schülerin oder Schüler gesichert, so fallen dabei ungefähr 2,2 GB an
      Daten an.

