.. _changelog-main:

***************
|UCSUAS|-Update
***************

Dieses Dokument enthält die Changelogs mit den detaillierten
Änderungsinformationen zum Update von |UCSUAS| von Version 5.0 v2 nach 5.0 v3.

Sofern notwendig, werden wichtige Hinweise zum Update in einem separaten
Abschnitt behandelt. Die Changelogs werden nur in Englisch gepflegt. Die
Änderungsinformationen für vorherige Versionssprünge finden sich unter
https://docs.software-univention.de/.

.. _changelog-prepare:

Generelle Hinweise zum Update
=============================

Während der Aktualisierung kann es zu Ausfällen von Diensten innerhalb der
Domäne kommen. Aus diesem Grund sollte das Update innerhalb eines
Wartungsfensters erfolgen. Grundsätzlich wird empfohlen das Update zunächst in
einer Testumgebung einzuspielen und zu testen. Die Testumgebung sollte dabei
identisch zur Produktivumgebung sein.

.. _changelog-veyon-update:

Update der Software zur Kontrolle und Überwachung von Computerräumen
====================================================================

Die Leistung und Stabilität der Computerraumüberwachung ist mit |UCSUAS| 5.0 v3
verbessert worden.

.. caution::

   Die Applikation ``UCS@school Veyon Proxy`` aus dem App-Center muss auf
   ``4.7.4.6`` aktualisiert werden. Zudem müssen die Windows-Rechner mit der
   passenden Veyon-Applikation ausgestattet werden. Eine passende Version wird
   mit |UCSUAS| mitgeliefert (``4.7.4``), und kann wie in
   :ref:`school-windows-veyon` beschrieben installiert werden.

Die Statusindikatoren der Computerraum-Modul-Seite können mit bis zu einer
Minute Verzögerung aktualisiert werden. Dies ist ein bekanntes Problem und wird
bald mit einem Errata-Update korrigiert.

Je nach vorhandener Hardware, Bandbreite und Anzahl der PCs im Computerraum ist
es möglich, dass Feineinstellungen am Präsentationsmodus vorgenommen werden
müssen, wenn die Performance nicht zufriedenstellend ist. Siehe hierzu die
:uv:help:`Kurzanleitung: Performance des Präsentationsmodus verbessern <20264>`.

Mit diesem Release wird zudem die Update-Sperre für Systeme mit Computerräumen
aufgehoben. Somit können Systeme von UCS 4.4 auf UCS 5.0 aktualisiert werden,
wenn auf dem System alle Computerräume auf Veyon migriert wurden.

.. _changelog-newerrata:

Updateprozess
=============

Größere Updates für |UCSUAS| werden im Univention App Center als eigenständiges
App-Update herausgegeben. Kleinere Updates und Fehlerbereinigungen (Errata für
|UCSUAS|), die keine Interaktion mit dem Administrator erforderlich machen,
werden im Repository der bereits veröffentlichten App-Version von |UCSUAS|
herausgegeben. Die Changelog-Dokumente, die Univention mit jeder |UCSUAS|
App-Version herausgibt, werden dann entsprechend um einen neuen Abschnitt
erweitert, aus dem ersichtlich wird, zu welchem Zeitpunkt welche Pakete
veröffentlicht und welche Fehler dabei behoben wurden.
