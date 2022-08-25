.. _installation-single:
.. _installation-single-primary-directory-node:

Installation einer Single-Server-Umgebung
=========================================

Zunächst muss ein UCS System mit der Systemrolle |UCSPRIMARYDN_e| (kurz:
Primary) installiert werden. Die :ref:`Installation von UCS
<installation-chapter>` ist in :cite:t:`ucs-manual` beschrieben. Es ist
empfohlen während der Installation keine zusätzliche Software auszuwählen.

Nach der erfolgreichen UCS-Installation muss die App |UCSUAS_p| installiert
werden. Jedes UCS-System bietet ein webbasiertes Konfigurationsinterface an,
Univention Management Console, kurz UMC. Dies ist via Webbrowser erreichbar,
dazu kann einfach der Name oder die IP-Adresse des Servers in die Adresszeile
des Webbrowsers eingegeben werden. Es erscheint eine Kachel mit der Bezeichnung
*System- und Domäneneinstellungen*. Nach einem Klick auf die Kachel wird eine
Anmeldemaske angezeigt. Dort erfolgt die Anmeldung mit dem Benutzer
``Administrator``. Sofern noch nicht geändert, entspricht das Passwort dem während
der UCS-Installation vergebenen Passwort für den Benutzer ``root``.

Nun kann die Kachel *App Center* geöffnet und dort die Applikation |UCSUAS_e|
installiert werden. Für die Installation ist den Anweisungen zu folgen, bspw.
kann eine Lizenzaktivierung notwendig sein. Details dazu sind im
:cite:t:`ucs-manual` zu finden.


.. _install-via-app-center:

.. figure:: /images/appcenter_ucsschool.png
   :alt: Installation von UCS@school über das Univention App Center

   Installation von UCS@school über das Univention App Center

Nach dem Abschluss der Installation über das App Center erfolgt die
Konfiguration von |UCSUAS|. Diese wird mit dem |UCSUAS|
Konfigurationsassistenten durchgeführt. Dieser ist in UMC über den Bereich
*Schul-Administration* erreichbar.

.. _install-umc-wizard:

.. figure:: /images/install-umc-wizard.png
   :alt: Starten des UCS@school-Konfigurationsassistenten

   Starten des UCS@school-Konfigurationsassistenten

Auf der ersten Seite fragt der Konfigurationsassistent nach dem
Installationsszenario. Hier ist die ``Single-Server-Umgebung`` auszuwählen.

.. _install-umc-wizard-single-server:

.. figure:: /images/installation-single-server.png
   :alt: Single-Server-Umgebung

   Single-Server-Umgebung

Auf der zweiten Seite muss der Name der Schule und das Schulkürzel eingegeben
werden. Innerhalb von |UCSUAS| wird dieser Name immer wieder angezeigt. Sobald
der Name der Schule eingetragen ist und in das Feld für das Schulkürzel geklickt
wird, wird ein Wert für das Schulkürzel vorgeschlagen. Dieser Wert kann
entsprechend angepasst werden.

* Der Name der Schule kann dabei Leerzeichen und Sonderzeichen enthalten.

* Das Schulkürzel darf nur aus Buchstaben, Zahlen und Unterstrichen bestehen.

Das Schulkürzel wird im Verzeichnisdienst als Name für die
Organisationseinheiten (OU) verwendet (siehe auch :ref:`structure`), zusätzlich
wird das Schulkürzel als Grundlage für Gruppen-, Freigabe- und Rechnernamen
verwendet.

.. important::

   Das Schulkürzel kann nach der initialen Konfiguration von |UCSUAS| nicht mehr
   modifiziert werden.

.. _install-umc-wizard-single-schoolname:

.. figure:: /images/installation-singleserver-schoolname.png
   :alt: Eingabe der Schuldaten

   Eingabe der Schuldaten

Nach der abschließenden Bestätigung startet die Konfiguration von |UCSUAS|.
Dabei werden diverse Pakete installiert und konfiguriert. Die Dauer schwankt je
nach Geschwindigkeit der Internetverbindung und Serverausstattung.

Installation und Konfiguration von |UCSUAS| sollten mit einem Neustart des
Systems abgeschlossen werden. Im Anschluss kann die weitere Konfiguration der
Schule vorgenommen werden, siehe :ref:`school-setup-cli`.

.. important::

   Nach Abschluss der Installation auf dem |UCSPRIMARYDN| muss auf allen anderen
   gejointen Systemen der Domäne der Befehl
   :command:`univention-run-join-scripts` ausgeführt werden, damit der
   installierte |UCSUAS|-Join-Hook benötigte Konfigurationspakete auf den
   Systemen nachinstallieren kann.

   Dieser Vorgang kann je nach Rolle des Systems und dessen Systemperformance
   mehrere Minuten dauern und darf nicht unterbrochen werden.
