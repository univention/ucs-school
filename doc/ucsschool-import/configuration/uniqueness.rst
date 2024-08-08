.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration-unique-usernames-and-email:

Einmalige Benutzernamen und E-Mailadressen
==========================================

Benutzernamen und E-Mailadressen müssen in der gesamten Domäne, nicht nur an
einer Schule, einmalig sein. Darüber hinaus kann es die Anforderung geben, dass
Benutzernamen und E-Mailadressen auch *historisch einmalig* sind, also auch dann
nicht wiederverwendet werden, wenn die vorherigen Konten bereits lange gelöscht
sind.

Aus diesem Grund können zur Erzeugung von Benutzernamen und E-Mailadressen, über
die üblichen Variablen in Formatierungsschema (siehe
:ref:`configuration-scheme-formatting`) hinaus, spezielle Zählervariablen
verwendet werden. Diese Variablen werden bei ihrer Verwendung automatisch
hochgezählt. Ihr Wert wird pro Benutzername bzw. E-Mailadresse gespeichert. Es
existieren zwei Variablen, die sich darin unterscheiden, wie die ersten Benutzer
mit gleichem Benutzernamen bzw. E-Mailadresse, benannt werden:

``[ALWAYSCOUNTER]``
   ``[ALWAYSCOUNTER]`` ist ein Zähler, der bei seiner ersten Verwendung eine
   ``1`` einsetzt.

   Benutzernamen für ``anton`` wären: ``anton1``, ``anton2``, ``anton3``...

   Analog für ``anton@dom.ain``: ``anton1@dom.ain``, ``anton2@dom.ain``,
   ``anton3@dom.ain``...

``[COUNTER2]``
   ``[COUNTER2]`` ist ein Zähler, der bei seiner ersten Verwendung keine Zahl
   einsetzt, erst bei seiner zweiten.

   Benutzernamen für ``anton`` wären: ``anton``, ``anton2``, ``anton3``...

   Analog für ``anton@dom.ain``: ``anton@dom.ain``, ``anton2@dom.ain``,
   ``anton3@dom.ain``...

Im folgenden Beispiel würden für ``Bea Schmidt`` die Benutzernamen
``b.schmidt``, ``b.schmidt2``, ``b.schmidt3`` sowie E-Mailadressen
``bea.schmidt1@dom.ain``, ``bea.schmidt2@dom.ain``, ``bea.schmidt3@dom.ain``
erzeugt werden:

.. code-block:: json

   {
       "scheme": {
           "username": {
               "default": "<:umlauts><firstname>[0].<lastname><:lower>[COUNTER2]"
           },
           "email": "<firstname>.<lastname>[ALWAYSCOUNTER]@<maildomain>"
       },
       "maildomain": "dom.ain",
   }


Die ``[0]`` im Beispiel bedeutet, dass nur das erste Zeichen des davor stehenden
Attributes genommen wird. Es ist auch möglich Bereiche anzugeben. Weitere
Informationen dazu finden sich in :ref:`users-templates` in
:cite:t:`ucs-manual`.

Um Zählervariablen nach Tests auf ``0`` zurück zu setzen, kann das Skript
:file:`/usr/share/ucs-school-import/scripts/reset_schema_counter` verwendet
werden. Mit Hilfe eines Filters kann beschränkt werden, welche Zähler gelöscht
werden sollen. In einem Testlauf kann dies überprüft werden. Mit der Option
``--help`` werden die Aufrufparameter angezeigt. Standardmäßig werden die Zähler
für Benutzernamen zurück gesetzt. Um Zähler für E-Mailadressen zu löschen, muss
``--email`` verwendet werden.

.. warning::

    Um einen aussagekräftigen Benutzernamen zu gewährleisten, geht die Logik von maximal
    drei Zeichen für die Zählervariablen aus, wenn ein Benutzername unter Berücksichtigung
    der :ref:`maximalen Länge <configuration-json-format-userimport-option-username-max_length>` generiert wird.
    Dies bedeutet, dass davon ausgegangen wird, dass der Zähler maximal bis 999 zählen muss.

    Technisch wird es allerdings nicht verhindert, dass der Zähler über 999 hinausgeht und somit vierstellig wird.
    Sollte dieser Fall eintreten, werden Benutzernamen generiert, die ein Zeichen länger als das konfigurierte Maximum sein können.

    Wird in der Umgebung keine Unterstützung für :program:`Samba`, :program:`Samba 4 Connector` und :program:`Active Directory Connector`
    benötigt, hat dies keine negativen Auswirkungen.

    Muss allerdings eine maximale Länge für Benutzernamen eingehalten werden, so wird empfohlen ein alternatives
    Schema zu entwickeln, welches weniger doppelte Benutzernamen erzeugt.


.. _configuration-unique-usernames-and-email-extending:

Programmierung neuer Zählervariablen
------------------------------------

Um neue Zählervariablen hinzuzufügen, muss von der Klasse
:py:class:`ucsschool.importer.utils.username_handler.UsernameHandler` abgeleitet
und die Methode
:py:meth:`~ucsschool.importer.utils.username_handler.UsernameHandler.counter_variable_to_function`
überschrieben werden (siehe :ref:`extending-subclassing`).

Um diese neuen Zählervariablen auch für E-Mailadressen zu verwenden, muss
:py:class:`ucsschool.importer.utils.username_handler.EmailHandler` von der
neuen, abgeleiteten
:py:class:`~ucsschool.importer.utils.username_handler.UsernameHandler` Klasse
*sowie* von :py:class:`~ucsschool.importer.utils.username_handler.EmailHandler`
abgeleitet werden. Um Zählervariablen *nur* für E-Mailadressen hinzuzufügen,
muss nur von der Klasse
:py:class:`~ucsschool.importer.utils.username_handler.EmailHandler` abgeleitet,
und oben beschriebene Methoden überschrieben werden.
