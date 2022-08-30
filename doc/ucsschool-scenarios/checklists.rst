.. _setup-checklist:

******************************************
Checklisten: Organisatorisch und technisch
******************************************

Im Folgenden haben wir einige Fragen zusammengestellt, über die Sie sich direkt
am Anfang der Projektplanung Gedanken machen sollten.

.. _setup-manual-organisation:

Organisation
============

.. rst-class:: white-square

* Welches Szenario soll umgesetzt werden? Siehe :ref:`scenarios`.

* Wer ist Betreiber der Gesamtinfrastruktur?

* Verfügt der Betreiber über das erforderliche Wissen? Siehe
  :ref:`preparations-workshop`.

* Wie werden Schulen über die Einführung der neuen IT-Infrastruktur informiert?
  Siehe :ref:`preparations-info`.

* Wer baut in den Schulen Server, Rechner und Drucker auf und tauscht diese im
  Fehlerfall aus?

* In welcher Reihenfolge erfolgt der Rollout an den Schulen (nicht in allen
  Szenarien notwendig)? Siehe :ref:`preparations-school-selection`.

* In welchem zeitlichen Rahmen soll der Rollout der Pilot-Installation und
  später der Gesamtinfrastruktur erfolgen?

* Welche administrativen Aufgaben sollen durch die Schulen übernommen werden,
  zum Beispiel Passwörter zurücksetzen?

* Wie werden Schulen mit den neuen Lösungen w.z.B. |UCSUAS| vertraut gemacht?
  Siehe :ref:`preparations-training`.

* Wie und bei wem melden Schulen Probleme? Siehe :ref:`concepts-support`.

* Wie wird die Qualität des erbrachten IT-Angebots gemessen? Welches sind die
  entscheidenden Parameter, um dies zu messen?

* Wie wird sichergestellt, dass die zukünftigen Anforderungen der Schulen
  erfasst und von der Gesamtinfrastruktur erfüllt werden?

* Wer ist verantwortlich für die Pflege von Informationen in der
  Schulverwaltungssoftware und wie können diese Daten importiert werden?

.. _setup-manual-zentrale:

Zentral bereitgestellte IT-Angebote
===================================

.. rst-class:: white-square

* Wo werden die zentralen Server betrieben? Siehe
  :ref:`infrastructure-and-hardware-requirements-servers`.

* Nach welchen Konzepten wird die Gesamtinfrastruktur betrieben, insbesondere
  Netzkonzept, sowie Namenskonzepte für Benutzer und Rechner? Siehe
  :ref:`concepts`.

* Wie wird die Aufrechterhaltung des Betriebs sichergestellt, zum Beispiel
  Monitoring, Datensicherung und Notfallpläne? Siehe
  :ref:`installation-managed-node` und :ref:`concepts-backup`.

* Wer führt die initiale Installation und Einrichtung durch?

  * Installation der UCS Systeme mit der App |UCSUASp|, siehe
    :ref:`install`.

  * Welche Basiskonfigurationen sollen vorgenommen werden? Siehe
    :ref:`base-configuration`.

  * Wie erfolgt der Import von Benutzer-, Rechner- und Netzdaten? Siehe
    :ref:`import`.

* Welche VPN-Lösung wird eingesetzt (nicht in allen Szenarien notwendig)? Siehe
  :ref:`infrastructure-and-hardware-requirements-infrastructure-vpn`.

* Welche über die Basis IT-Infrastruktur hinausgehenden Angebote und
  Einstellungen sollen angeboten werden? Wie werden die über das Internet
  zugänglichen zentralen Angebote vor unerwünschtem Zugriff geschützt?

* Soll die Schulen zukünftig über einen zentralen Proxy auf das Internet
  zugreifen?

* Wie erfolgt der Zugriff auf zentral bereitgestellte Webdienste (Portal,
  Self-Service ...) aus dem Internet?

  * Stellt der Rechenzentrumsbetreiber *Load Balancer* und *Reverse Proxy* als
    Dienst bereit?

  * Welche externen Domänennamen sollen für den Zugriff auf die Webdienste
    verwendet werden?

  * Ist sichergestellt, dass zu den Domänennamen passende SSL/TLS Zertifikate
    vorhanden sind und diese regelmäßig erneuert werden?

.. _setup-manual-schulen:

Dezentral an den Schulen bereitgestellte IT-Angebote
====================================================

.. rst-class:: white-square

* Wer ist lokaler Ansprechpartner für die IT-Infrastruktur in der Schule?

* Setzt die Schule bereits eine Schulserver-Lösung ein? Welche Funktionen sind
  der Schule wichtig?

* Wie schnell und stabil ist der Internetzugang der Schule? Siehe
  :ref:`infrastructure-and-hardware-requirements-infrastructure-internet`.

* Wer betreibt den Internetzugang und ist für die Entstörung zuständig?

* Welche aktiven und passiven Netzkomponenten sind im Einsatz, zum Beispiel
  DSL-Router/Switches/Access Points, und wer kennt die Zugangsdaten?

* Welches IP-Netz wird aktuell in der Schule verwendet? Welche Komponenten
  müssen angepasst werden, um das Netzkonzept (siehe
  :ref:`setup-manual-zentrale`) umzusetzen?

* Ist in der Schule strukturierte Verkabelung in allen Computerräumen vorhanden?
  Siehe :ref:`infrastructure-and-hardware-requirements-infrastructure-network`.
  Wie sind die Patchfelder und Netzdosen belegt?

* Welche Bauarbeiten und Beschaffungen müssen vorgenommen werden, um die
  Betriebsbereitschaft für die Schule herzustellen?

* Kann mit dem verfügbaren Internetzugang ein VPN betrieben werden (nicht in
  allen Szenarien notwendig)? Siehe
  :ref:`infrastructure-and-hardware-requirements-infrastructure-vpn`.

.. _setup-manual-wlan:

WLAN und BYOD
=============

.. rst-class:: white-square

* Kann mit dem verfügbaren Internetzugang ein VPN betrieben werden?

* Sind professionelle Access Points vorhanden, die VLANs, mehrere SSIDs sowie
  RADIUS bzw. IEEE 802.1X unterstützen?

* Wie können die Access Points zentral konfiguriert werden? Ist eine Management
  Software oder ein WLAN-Controller vorhanden?

* Wo wird der RADIUS-Service betrieben?

* Wie greifen die mobilen Geräte auf das Internet zu, zum Beispiel direkt oder
  über einen transparenten Proxy?

* Wie hoch sind die notwendigen Investitionen, um die Betriebsbereitschaft für
  das WLAN herzustellen?

* Welche IT-Angebote, zentral und dezentral, sollen von den Geräten im WLAN
  verwendet werden können?
