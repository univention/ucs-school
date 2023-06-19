.. SPDX-FileCopyrightText: 2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration-ucr:

UCR Konfiguration
=================

``ucsschool/stop_notifier``
---------------------------

Wenn der Import beginnt, ist der Notifier standardmäßig deaktiviert. Dies wird
gemacht, um Synchronisationsprobleme zu vermeiden, die auftreten, wenn viele
Änderungen in kurzer Zeit aufeinander folgen. Das kann beispielsweise mit dem
AD- oder S4-Connector passieren.

Allerdings hat das Stoppen des Notifiers auch unerwünschte Folgen: Prüfungen
können nicht gestartet werden und Änderungen an Benutzern, wie das Anlegen,
Löschen oder Modifizieren, werden erst nach Beendigung des Imports wirksam.

Da allerdings alle uns bekannten Probleme mit den bidirektionalen Konnektoren
mittlerweile behoben worden sind, gibt es eine UCR-Variable,
``ucsschool/stop_notifier``, um das Ausschalten des Notifiers zu verhindern.
Diese Variable ist experimentell und sollte mit Vorsicht genutzt werden.
Ausserdem sollte die LDAP-Datenbank nach Importen regelmäßig auf Fehler
überprüft werden.

Wenn ein bidirektionaler Connector ein Objekt verarbeitet, aber gleichzeitig
eine weitere Änderung an dem Objekt stattfindet, kann es passieren, dass das
Objekt auf den Zustand vor der zweiten Änderung zurückgesetzt wird. Dies ist
eher bei Objekten der Fall, die sich in kurzer Zeit sehr häufig ändern. Ein
wahrscheinliches Beispiel währen Gruppenobjekte, speziell die
Gruppenmitgliedschaften. Es wird davon ausgegangen, dass so etwas nicht mehr
auftritt, es kann allerdings nicht mit absoluter Sicherheit ausgeschlossen
werden.

Ein Weg Fehler in einem Connector zu finden, ist es die Integrität von Gruppen
und Benutzern nach einem Import mit aktiviertem Notifier durchzuführen.
