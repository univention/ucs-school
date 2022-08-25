.. _install:

************
Installation
************

|UCSUAS| basiert auf |UCSUCS| (UCS) und wird dabei als Repository-Komponente aus
dem Univention App Center eingebunden. Die :ref:`Installation von UCS
<installation-chapter>` ist :cite:t:`ucs-manual` dokumentiert. Nachfolgend wird
nur auf ggf. auftretende Unterschiede zur Grundinstallation von |UCSUCS| sowie
die Installation von |UCSUAS| selbst eingegangen.

Im Folgenden werden zwei Installationsvarianten beschrieben: 

#. Die Installation als Single-Server-Umgebung 

#. Die Installation als Multi-Server-Umgebung mit einem |UCSPRIMARYDN| und
   mindestens einem Schulserver.

In beiden Fällen wird empfohlen, während des Installationsprozesses von |UCSUAS|
keine weiteren Aktionen in der UMC oder auf der Kommandozeile auszuführen.
Sollten Sie das Fenster im Browser während des Installationsprozesses von
|UCSUAS| schließen, läuft die Installation selbst dennoch auf dem System weiter.
Um den Status der Installation dann noch zu überprüfen, können Sie die Logdatei
in :file:`/var/log/univention/management-console-module-schoolinstaller.log`
konsultieren.

Die nachträgliche Umwandlung einer Single-Server-Umgebung in eine
Multi-Server-Umgebung wird unterstützt und in
:ref:`school-installation-migration-single2multi` genauer beschrieben.

In beiden Varianten wird standardmäßig bei der Erstinstallation von |UCSUAS| auf
dem |UCSPRIMARYDN| eine Demonstrationsschule inklusive Testnutzern konfiguriert.
Die Schule trägt den Namen *DEMOSCHOOL* und kann für eigene Tests verwendet
werden. Das Passwort für die automatisch angelegten Nutzer ``demo_student``,
``demo_teacher`` und ``demo_admin`` befindet sich in der Datei
:file:`/etc/ucsschool/demoschool.secret`. Um das Anlegen der
Demonstrationsschule zu verhindern, muss die UCR-Variable
:envvar:`ucsschool/join/create_demo` auf den Wert ``no`` gesetzt werden,
**bevor** der |UCSUAS|-Konfigurationsassistent durchlaufen wird. Das Setzen der
UCR-Variable ist entweder über das UMC-Modul *Univention Configuration Registry*
oder auf der Kommandozeile mit dem Befehl :command:`ucr set
ucsschool/join/create_demo=no` möglich.

.. versionadded:: 4.4

   Der Installationsprozess nutzt seit |UCSUAS| 4.4 das Feature *Join-Hooks*.

   Join-Hooks werden in einer |UCSUAS|-Umgebung vom |UCSPRIMARYDN| im
   LDAP-Verzeichnis hinterlegt und automatisch während des Join-Vorgangs bzw.
   während der Ausführung von Join-Skripten ausgeführt. Der |UCSUAS|-Join-Hook
   installiert auf allen Systemen der Domäne automatisch die App |UCSUAS_p| aus
   dem Univention App Center und installiert die auf dem jeweiligen System
   benötigten |UCSUAS|-Pakete, sofern diese fehlen. Für die Erstinstallation der
   Pakete wird der Join-Hook je nach Rolle des Systems und dessen
   Systemperformance mehrere Minuten benötigen. Der Join-Vorgang darf dabei
   nicht abgebrochen werden.

   Der Hostname darf nur aus Kleinbuchstaben, Ziffern sowie dem Bindestrich
   bestehen (``a-z``, ``0-9`` und ``-``) und zur Trennung nur einzelne Punkte
   enthalten. Der Hostname darf außerdem nur mit einem Kleinbuchstaben beginnen,
   mit einem Kleinbuchstaben oder einer Ziffer enden und ist auf eine Länge von
   13 Zeichen beschränkt.

.. toctree::
   :caption: Kapitelinhalte

   single
   multi
   single-to-multi
   integrate-self-service
