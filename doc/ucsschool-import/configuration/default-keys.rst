.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration-default-key:

*default*-Schlüssel
===================

Einige Einstellungen erlauben das Setzen von verschiedenen Werten, je nach Rolle
des Benutzers, der gerade importiert wird. In einem solchen Fall gibt es immer
den Schlüssel ``default``, der automatisch verwendet wird, wenn es keinen
Schlüssel in der Konfiguration für die betroffene Benutzerrolle gibt.

Erlaubte
Werte für die Benutzerrollen-Schlüssel sind:

* ``student``

* ``staff``

* ``teacher``

* ``teacher_and_staff``

Es müssen nicht zwangsläufig Schlüssel für alle Benutzerrollen angegeben werden.

Gilt für eine Einstellung z.B. das gleiche für Mitarbeiter und Lehrer und weicht
nur der Wert für die Schüler-Benutzerrolle ab, so reicht es aus, ``default`` und
``student`` zu konfigurieren. In den Fällen ``staff``, ``teacher`` und
``teacher_and_staff`` wird in Abwesenheit einer spezifischen Konfiguration
automatisch auf ``default`` zurückgefallen:

.. code-block:: json

   {
       "scheme": {
           "username": {
               "default": "<:umlauts><firstname>[0].<lastname>[COUNTER2]",
               "student": "<:umlauts><firstname>.<lastname><:lower>[ALWAYSCOUNTER]"
           }
       }
   }
