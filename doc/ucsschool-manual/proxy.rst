.. _school-proxy:

******************************
Web-Proxy auf den Schulservern
******************************

In der Grundeinstellung läuft auf jedem Schulserver (bzw. im
Single-Server-Betrieb auf dem |UCSPRIMARYDN|) ein Proxy-Server auf Basis von
*Squid* im Zusammenspiel mit *squidGuard*. Der Proxy erlaubt Lehrern in
Unterrichtsstunden und im Klassenarbeitsmodus den Zugriff auf einzelne Webseiten
zu beschränken oder auch generell bestimmte Webseiten zu sperren. Dies ist in
:cite:t:`ucsschool-teacher` beschrieben.

Der Proxyserver muss zwingend auf dem jeweiligen Schulserver betrieben werden.

.. _school-proxy-setup:

Einrichtung
===========

.. highlight:: console

Die Proxykonfiguration wird in der Grundeinstellung durch DHCP über die
WPAD-Option verteilt. Siehe `WAPD auf Wikipedia
<https://de.wikipedia.org/wiki/Web_Proxy_Autodiscovery_Protocol>`_.

Soll die WPAD-Option abgeschaltet werden, so muss die Option an dem betreffenden
DHCP-Service-Objekt entfernt werden. Dies kann entweder im UMC-Modul
*DHCP* am betreffenden DHCP-Service-Objekt auf dem Reiter
*Erweiterte Einstellungen* unter *Low-level DHCP
configuration* oder an der Kommandozeile geschehen.

Das DHCP-Service-Objekt trägt in der Standardkonfiguration den Namen des
Schulkürzels und sollte daher in der UMC leicht identifizierbar sein. Um die
richtige DN und Option auf der Kommandozeile zu finden, können zuerst alle
DHCP-Service-Objekte aufgelistet werden. Die nachfolgenden Befehle sollten als
Benutzer root auf dem |UCSPRIMARYDN| ausgeführt werden:

.. code-block::

   $ udm dhcp/service list


So können in der folgenden Zeile :samp:`{DN}` und :samp:`{FQDN}` durch konkrete
Werte ersetzt werden:

.. code-block::

   $ udm dhcp/service modify \
     --dn DN \
     --remove option='wpad "http://FQDN/proxy.pac"'

Beispiel:

.. code-block::

   root@primary:~# udm dhcp/service list

   DN: cn=school123,cn=dhcp,ou=school123,dc=example,dc=com
     option: wpad "http://replica123.example.com/proxy.pac"
     service: school123

   DN: cn=example.com,cn=dhcp,dc=example,dc=com
     service: example.com

   root@primary:~# udm dhcp/service modify --dn cn=school123,cn=dhcp,ou=school123,dc=example,dc=com \
   > --remove option='wpad "http://replica123.example.com/proxy.pac"'
   Object modified: cn=school123,cn=dhcp,ou=school123,dc=example,dc=com
   root@primary:~#


Auf dem UCS-System, auf dem der betroffene DHCP-Server läuft (in
Single-Server-Umgebungen ist dies der |UCSPRIMARYDN| in Multi-Server-Umgebungen
i.d.R. ein konkreter Schulserver), muss anschießend eine UCR-Variable entfernt
und der DHCP-Server neu gestartet werden:

.. code-block::

   $ ucr unset dhcpd/options/wpad/252
   $ systemctl restart univention-dhcp


Um Domains, IP-Adressen, Netzwerke oder URLs von der Verwendung des Proxies
auszunehmen, können die UCR-Variablen :envvar:`proxy/pac/exclude/*` gesetzt
werden. Eine Liste der möglichen Einstellungen samt Erklärungen wird angezeigt
mit:

.. code-block::

   $ ucr search --verbose ^proxy/pac/exclude/


Die Verteilung der Proxykonfiguration mittels DHCP-WPAD-Option wird jedoch nicht
von allen Browsern unterstützt. Die Konfiguration kann alternativ über eine
Proxy-Autokonfigurationsdatei (PAC-Datei) automatisiert werden. In PAC-Dateien
sind die relevanten Konfigurationsparameter zusammengestellt. Die PAC-Datei
eines Schulservers steht unter der folgenden URL bereit:

:samp:`http://{schulserver.domaene.de}/proxy.pac`

Im Internet Explorer wird die PAC-Datei beispielsweise unter
:menuselection:`Internetoptionen --> Reiter Verbindungen --> LAN-Einstellungen
--> Automatisches Konfigurationsskript verwendet` zugewiesen.

In Firefox kann die PAC-Datei im Menü unter :menuselection:`Allgemein -->
Einstellungen --> Verbindungs-Einstellungen --> Automatische
Proxy-Konfigurations-URL` zugewiesen werden.

Bei Einsatz von Samba 4 kann die Proxy-Konfiguration alternativ auch über
Gruppenrichtlinien zugewiesen werden.

Bei der PAC- und der WPAD-Datei handelt es sich um die gleiche Datei
(:file:`/var/www/proxy.pac`). Es können daher die gleichen UCR-Variablen
verwendet werden um Domains, IP-Adressen, Netzwerke oder URLs von der Verwendung
des Proxies auszunehmen (:envvar:`proxy/pac/exclude/*`).

.. _school-proxy-blacklists:

Einbindung von externen Blacklisten
===================================

Der Proxy von |UCSUAS| unterstützt (ab |UCSUAS| 4.0 R2 und mindestens UCS 4.0
Erratum 163) die Einbindung von externen Blacklisten, welche als Textdateien
vorliegen müssen.

Die Textdateien dürfen jeweils nur Domänennamen oder URLs enthalten. Pro Zeile
darf nur ein Eintrag (Domänenname/URL) enthalten sein. Die Textdateien müssen
unterhalb des Verzeichnisses :file:`/var/lib/ucs-school-webproxy/` abgelegt
werden. Die Verwendung von weiteren Unterverzeichnissen ist möglich.

Eingebunden werden die Blacklisten über das Setzen von folgenden
UCR-Variablen:

* :envvar:`proxy/filter/global/blacklists/domains`

* :envvar:`proxy/filter/global/blacklists/urls`.

Diese Variablen enthalten die Dateinamen der Domänen-Blacklisten bzw.
URL-Blacklisten. Die Dateinamen sind relativ zum Verzeichnis
:file:`/var/lib/ucs-school-webproxy` anzugeben und müssen durch Leerzeichen
voneinander getrennt werden.

Die Einbindung der folgenden, exemplarischen Blacklist-Dateien

.. code-block::

   /var/lib/ucs-school-webproxy/extblacklist1/domains
   /var/lib/ucs-school-webproxy/extblacklist1/urls
   /var/lib/ucs-school-webproxy/bl2/list-domains
   /var/lib/ucs-school-webproxy/bl2/list-urls
   /var/lib/ucs-school-webproxy/bl3-dom
   /var/lib/ucs-school-webproxy/bl3-urls


kann über die nachfolgenden :command:`ucr set`-Befehle erreicht werden:

.. code-block::

   $ ucr set proxy/filter/global/blacklists/domains=\
       "extblacklist1/domains bl2/list-domains bl3-dom"
   $ ucr set proxy/filter/global/blacklists/urls=\
       "extblacklist1/urls bl2/list-urls bl3-urls"


Die Blacklisten werden vom Proxy in der Standardeinstellung mit niedriger
Priorität ausgewertet, d.h. (temporäre) Whitelisten von Schuladministratoren und
Lehrern haben Vorrang. Um die globalen Blacklisten vorrangig auszuwerten, kann
die UCR-Variable :envvar:`proxy/filter/global/blacklists/forced` auf den Wert
``yes`` gesetzt werden. Die Blacklisten können anschließend nicht mehr durch
Schuladministratoren oder Lehrer in der UMC umgangen bzw. zeitweilig deaktiviert
werden.

.. caution::

   Es ist zu beachten, dass bei einer Aktualisierung der
   Blacklist-Textdateien die internen Filterdatenbanken des Proxys nicht
   ebenfalls automatisch aktualisiert werden. Um dies zu erreichen,
   müssen die beiden UCR-Variablen erneut gesetzt werden.

.. note::

   Abhängig von der Anzahl der Einträge in den eingebundenen
   Blacklisten, kann die Aktualisierung der internen Filterdatenbanken
   beim Setzen der UCR-Variablen mehrere Sekunden benötigen.
