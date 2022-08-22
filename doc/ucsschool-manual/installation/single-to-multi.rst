.. _school-installation-migration-single2multi:

Umwandlung Single-Server- in Multi-Server-Umgebung
==================================================

|UCSUAS|-Umgebungen, die als Single-Server-Umgebung installiert/eingerichtet
wurden, können bei Bedarf nachträglich in eine Multi-Server-Umgebung umgewandelt
werden. Die Umwandlung ermöglicht die Aufnahme von Schulservern in die Domäne.

Für die Umwandlung sind einige Befehle auf der Kommandozeile des |UCSPRIMARYDN|\
s auszuführen, die einen Austausch des |UCSUAS|\ -Metapakets sowie eine
Konfigurationsänderung durchführen. Bitte beachten Sie das Minuszeichen hinter
dem zweiten Paketnamen am Ende der ersten Zeile:

.. code-block:: console

   $ univention-install ucs-school-multiserver ucs-school-singleserver-
   $ ucr unset ucsschool/singlemaster


Durch die beiden Befehle wird das Meta-Paket :program:`ucs-school-singleserver`
deinstalliert und im gleichen Zug das Paket :program:`ucs-school-multiserver`
installiert.

Mit der Deinstallation des Pakets :program:`ucs-school-singleserver` werden die
nachfolgenden |UCSUAS|-spezifischen Pakete (z.B. UMC-Module), die normalerweise
nicht auf einem |UCSPRIMARYDN| der Multi-Server-Umgebung installiert sind,
automatisch zur Löschung vorgesehen. Die eigentliche Löschung der betroffenen
Pakete findet während des nächsten Updates oder durch den manuellen Aufruf von
:command:`apt-get autoremove` statt. Dabei ist zu beachten, dass neben den
genannten Paketen ggf. auch ungenutzte Paketabhängigkeiten entfernt werden.

.. code-block::

   ucs-school-branding
   ucs-school-netlogon
   ucs-school-netlogon-user-logonscripts
   ucs-school-old-homedirs
   ucs-school-old-sharedirs
   ucs-school-umc-computerroom
   ucs-school-umc-distribution
   ucs-school-umc-exam
   ucs-school-umc-helpdesk
   ucs-school-umc-internetrules
   ucs-school-umc-lessontimes
   ucs-school-umc-printermoderation
   ucs-school-webproxy
   univention-squid-kerberos


Um die Löschung einzelner Pakete zu vermeiden, kann der folgende Befehl
verwendet werden, bei dem :samp:`{$PAKETNAME}` durch den gewünschten Paketnamen
auszutauschen ist:

.. code-block:: console

   $ apt-get unmarkauto $PAKETNAME


Richtlinien, die (ggf. automatisch von |UCSUAS|) an Container der Schul-OUs
verknüpft wurden, sollten auf ihre Einstellungen hin überprüft werden. Dies
betrifft unter anderem die DHCP-DNS-Einstellungen.

Nachdem die oben genannten Schritte ausgeführt wurden, sollte abschließend der
UMC-Server auf dem |UCSPRIMARYDN| neu gestartet werden:

.. code-block:: console

   $ service univention-management-console-server restart


.. caution::

   Es ist zu beachten, dass auch nach der abgeschlossenen Umwandlung in eine
   Multi-Server-Umgebung der auf dem |UCSPRIMARYDN| installierte Dienst *Samba
   4* bestehen bleibt und nicht automatisch deinstalliert wird.
