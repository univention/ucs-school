.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _umc:
.. _umc-login:

************************************
|UCSUMC| - Die Verwaltungsoberfläche
************************************

Der IT-gestützte Unterricht wird mit einer Oberfläche verwaltet, der |UCSUMC|
(UMC). Diese wird über einen Web-Browser (z.B. Mozilla Firefox) angezeigt und
kann erreicht werden, indem in die Adresszeile des Web-Browsers eine Adresse in
der Form :samp:`https://{schulserver.schultraeger.de}/umc/` eingetragen wird.
Die genaue Adresse wird vom Schul-Administrator bekannt gegeben. Beim ersten
Zugriff muss das Sicherheitszertifikat des Servers bestätigt werden.

.. _ssl-warning:

.. figure:: /images/firefox_ssl_certificate.png
   :alt: Sicherheitszertifikatswarnung in Firefox

   Sicherheitszertifikatswarnung in Firefox

Einige ältere Web-Browser werden nicht unterstützt, die Oberfläche benötigt
mindestens die folgenden Versionen:

* Google Chrome ab Version 37

* Mozilla Firefox ab Version 38

* Microsoft Internet Explorer ab Version 11

* Safari (auf dem iPad 2) ab Version 9

Wird kein unterstützter Browser vorgefunden, wird eine Warnung ausgegeben und es
können Darstellungsprobleme auftreten.

.. _login:

.. figure:: /images/login.png
   :width: 500px
   :alt: Anmeldung an der Univention Management Console

   Anmeldung an der Univention Management Console

Nach Aufruf der URL erscheint die Anmeldemaske, in der *Benutzername* und
*Passwort* eingegeben werden müssen.

Die genaue Anzahl der angezeigten Funktionen richtet sich nach der Anzahl der
auf dem jeweiligen Schulserver eingerichteten Dienste. Funktionen, die einem
Benutzer aufgrund fehlender Rechte nicht zur Verfügung stehen, werden dem
Benutzer nicht angezeigt. So können die Dialoge der UMC-Module während der
Benutzung von den hier abgebildeten Dialogen abweichen. Die genauen Unterschiede
sind den einzelnen Modulbeschreibungen zu entnehmen. Die einzelnen Kapitel sind
nach den Namen der Menüpunkte benannt.

.. _module-overview:

.. figure:: /images/module_overview_Administrator_admin.png
   :alt: Übersichtsseite der Funktionen eines Schuladministrators

   Übersichtsseite der Funktionen eines Schuladministrators
