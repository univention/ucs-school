.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _student-passwords:

Passwörter (Schüler)
====================

Dieses Modul erlaubt Lehrern das Zurücksetzen von Schülerpasswörtern. Die
bestehenden Passwörter können aus Sicherheitsgründen nicht ausgelesen werden.
Wenn Schüler ihr Passwort vergessen, muss ein neues Passwort vergeben werden.
Mit den folgenden Schritten kann ein Schülerpasswort neu gesetzt werden:

* Die Passwort-Funktion kann über *Passwörter (Schüler)* aufgerufen werden.

* Es erscheint eine Liste aller Schüler der Schule. Die Liste der Schüler kann
  eingeschränkt werden, indem über das Auswahlfeld *Klasse oder Arbeitsgruppe*
  eine Klasse oder AG ausgewählt wird. Es werden dann nur die Schüler dieser
  Klasse dargestellt.

  .. _passwordreset1:

  .. figure:: /images/passwords_students_1.png
     :alt: Zurücksetzen von Schülerpasswörtern

     Zurücksetzen von Schülerpasswörtern

* Durch Eingabe von Benutzer-, Vor- und/oder Nachname in das Eingabefeld *Name*
  und anschließendem Klick auf :guilabel:`Suchen` kann auch gezielt nach einem
  Schüler gesucht werden.

  .. _searching-pupils:

  .. figure:: /images/passwords_students_2.png
     :alt: Suche nach Schülerkonten

     Suche nach Schülerkonten

* Aus der Liste der angezeigten Schüler sind anschließend ein oder mehrere
  Schüler durch das Markieren des grauen Auswahlkastens vor dem Schülernamen
  auszuwählen. Anschließend ist die Schaltfläche :guilabel:`Passwort
  zurücksetzen` oberhalb der Schülerliste auszuwählen.

  .. _passwordreset2:

  .. figure:: /images/passwords_students_3.png
     :alt: Zurücksetzen eines Schülerpassworts

     Zurücksetzen eines Schülerpassworts

* In das Feld *Neues Passwort* wird das neue Passwort für den oder die Schüler
  eingetragen. Ist der Haken vor dem Feld *Benutzer muss das Passwort bei der
  nächsten Anmeldung ändern* aktiviert, ist das dabei vergebene Passwort nur
  temporär gültig. Wenn der Schüler sich mit diesem Zwischenpasswort anmeldet,
  muss das Passwort direkt geändert werden. Es wird empfohlen, diese Option aus
  Sicherheitsgründen aktiviert zu lassen. Dadurch ist das neue Passwort, welches
  der Schüler anschließend setzt, nur ihm bekannt.

* Für Passwörter können Mindestanforderungen definiert werden, etwa mindestens
  acht Zeichen Länge. Wenn das eingegebene Passwort gegen diese Kriterien
  verstößt, wird ein Hinweis ausgegeben und es muss ein neues Passwort
  eingegeben werden.
