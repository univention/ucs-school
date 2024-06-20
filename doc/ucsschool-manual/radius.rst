.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _radius:

***********************************************
Authentifizierung des WLAN-Zugriffs über RADIUS
***********************************************

RADIUS ist ein Authentifizierungsprotokoll in Computernetzen. Es wird in
|UCSUAS| für die Authentifizierung von Rechnern für den Wireless-LAN-Zugriff
eingesetzt.

Der RADIUS-Server muss auf den *Access Points* entsprechend konfiguriert werden.
Die vom Client übertragenen Benutzerkennungen werden dann durch den festgelegten
RADIUS-Server geprüft, der wiederum für die Authentifizierung auf den
UCS-Verzeichnisdienst zugreift.

.. _radius-install:

Installation und Konfiguration des RADIUS-Servers
=================================================

Um RADIUS-Unterstützung einzurichten, muss das Paket
:program:`ucs-school-radius-802.1x` auf dem Schulserver der Schule installiert
werden, in der WLAN-Authentifizierung eingerichtet werden soll. Außerdem muss
das Paket :program:`ucs-school-webproxy` auf dem Schulserver installiert sein.

Beginnend mit |UCSUAS| 4.4 wird während der Installation des Pakets
:program:`ucs-school-radius-802.1x` auch automatisch die App :program:`RADIUS`
mit seinen zusätzlichen Features installiert. Der entsprechende Abschnitt
:ref:`ip-config-radius` in :cite:t:`ucs-manual` ist daher auch zu prüfen.

Nun müssen alle *Access Points* der Schule in der RADIUS-Konfiguration zusammen
mit einem Passwort hinterlegt werden, um einen Vertrauenskontext zwischen Access
Point und RADIUS-Server zu schaffen. Dies kann ab UCS 4.4 entweder in der
|UCSUMC| erfolgen, sofern für jeden Access Point ein Rechnerobjekt im
LDAP-Verzeichnis hinterlegt wird, oder in der Konfigurationsdatei
:file:`/etc/freeradius/3.0/clients.conf`.

Pro *Access Point* sollte ein zufälliges Passwort erstellt werden. Dies kann
z.B. mit dem Befehl :command:`makepasswd` geschehen. Die Kurzbezeichnung ist
frei wählbar. Ein Beispiel für einen solchen Eintrag:

.. code-block::

   client AP01 {
       secret = a9RPAeVG
       ipaddr = 192.168.100.101
   }


.. _radius-config:

Konfiguration der *Access Points*
=================================

Nun müssen die *Access Points* konfiguriert werden. Die dafür nötigen Schritte
unterscheiden sich je nach Hardwaremodell, prinzipiell müssen die folgenden vier
Optionen konfiguriert werden:

* Der Authentifizierungmodus muss auf RADIUS-Authentifzierung umgestellt werden.
  Diese Option wird oft auch als *WPA Enterprise* bezeichnet.

* Die IP-Adresse des Schulservers muss als RADIUS-Server angegeben werden.

* Der Radius-Port ist ``1812``, sofern kein abweichender Port in *FreeRADIUS*
  konfiguriert wurde.

* Das in der UMC bzw. in der Datei :file:`/etc/freeradius/3.0/clients.conf`
  hinterlegte Passwort.

.. _radius-client:

Konfiguration der zugreifenden Clients
======================================

Der zugreifende Client muss zunächst das UCS-Wurzelzertifikat importieren. Es
kann z.B. von der Startseite des |UCSPRIMARYDN| unter dem Link
*Wurzelzertifikat* bezogen werden. Anschließend muss er eine Netzwerkverbindung
mit den folgenden Parametern konfigurieren:

* Authentifizierung per WPA und TKIP als Verschlüsselungsverfahren

* ``PEAP`` und ``MSCHAPv2`` als Authentifizierungsprotokoll

Die Konfiguration unterscheidet sich je nach Betriebssystem des Clients. Eine
exemplarische Schritt-für-Schritt-Anleitung findet sich unter
:uv:help:`Einrichtung des WLAN-Zugriffs über RADIUS für Windows 10 <21827>`.

.. _radius-wlan:

Freigabe des WLAN-Zugriffs in der |UCSUMC|
==========================================

In der Grundeinstellung ist der WLAN-Zugriff nicht zugelassen. Um einzelnen
Benutzergruppen WLAN-Zugriff zu gestatten, muss in der |UCSUMC| im Modul
*Internetregeln definieren* eine Regel hinzugefügt - oder eine
bestehende editiert werden, in der die Option
*WLAN-Authentifizierung aktiviert* aktiviert ist.

Weiterführende Dokumentation zur Freigabe des WLAN-Zugriffs finden sich in
:cite:t:`ucsschool-teacher`.

.. _radius-error:

Fehlersuche
===========

Im Fehlerfall sollte die Logdatei :file:`/var/log/freeradius/radius.log` geprüft
werden:

* Erfolgreiche Logins führen zu einem Logeintrag ``Auth: Login OK``.
* Fehlgeschlagene Authentifizierung führt beispielsweise zu ``Auth: Login incorrect``.

Weitere Informationen zur Fehlersuche sind in :cite:t:`ucs-manual`, im Abschnitt
:ref:`ip-config-radius`, beschrieben.
