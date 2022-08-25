.. _introduction:

#######################################
|UCSUAS| - Handbuch für Administratoren
#######################################

|UCSUAS| ist eine auf |UCSUCS| (UCS) basierende IT-Komplettlösung mit
zahlreichen Zusatzkomponenten für Nutzung, Betrieb und Management von
Informationstechnologie (IT) in Schulen. |UCSUAS| vereint die Stärken des
Enterprise-Betriebssystems UCS im Bereich einfacher und zentraler Verwaltung von
IT-Umgebungen mit den Vorteilen klassischer Schulsoftware für den
Computereinsatz im Unterricht.

UCS ist die ideale Plattform für Schulen und Schulträger, um IT gemeinsam mit
den dazu gehörenden Service- und Supportprozessen für eine oder mehrere Schulen
zentral und wirtschaftlich bereitzustellen. |UCSUAS| ergänzt UCS um zahlreiche
Komponenten für den IT-Betrieb und den IT-gestützten Unterricht in der Schule.

Die |UCSUMC| ermöglicht die zentrale, web-basierte Verwaltung aller Domänendaten
(z.B. Benutzer, Gruppen, Rechner, DNS/DHCP). Die Speicherung der Daten erfolgt
in einem Verzeichnisdienst auf Basis von OpenLDAP. Da viele Schuldaten primär in
schulträgerspezifischen Systemen erfasst werden, bringt |UCSUAS| unter anderem
eine CSV-Datei-basierte Importschnittstelle für Schülerdaten mit.

Um den IT-gestützten Unterricht zu ergänzen, wurde die Benutzeroberfläche der
|UCSUMC| an die Anforderungen von Lehrern angepasst. Dies ermöglicht zum
Beispiel die Organisation der Unterrichtsvorbereitung und Klassenraumplanung
sowie die temporäre Sperrung des Internetzugangs für ausgewählte Computer.
Lehrern ist es auch möglich, den Bildschirminhalt eines Schüler-PCs einzusehen,
via Netzwerk individuelle Hilfestellungen zu geben oder einen beliebigen Desktop
auf alle anderen Computer in der Klasse oder per Beamer zu übertragen. Auch bei
im Schulalltag wiederkehrenden Tätigkeiten, wie dem Zurücksetzen von Passwörtern
für Schüler-Benutzerkonten, werden Lehrer unterstützt.

Für die Bedienung der |UCSUAS|-spezifischen Module der |UCSUMC| steht
:cite:t:`ucsschool-teacher` bereit.

.. toctree::
   :caption: Inhalt
   :numbered:

   structure
   installation/index
   management/index
   manage-school-imports
   extended-configuration
   windows
   modules
   proxy
   radius
   exam-mode/index
   python-hooks

.. toctree::
   :hidden:

   bibliography
