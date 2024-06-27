.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration-deleting-users:

Benutzer löschen
================

Das Löschen von Benutzern kann in zwei Varianten konfiguriert werden:

* Das Benutzerkonto wird sofort oder später gelöscht, nicht deaktiviert.

  Dies entspricht dem Löschen eines Kontos im |UCSUMC|-Modul *Benutzer* (siehe
  :ref:`users-management` in :cite:t:`ucs-manual`), zum definierten Zeitpunkt.

  Diese Variante wird ausgewählt durch das Setzen von
  :option:`deletion_grace_period:deletion` auf einen Wert kleiner oder gleich
  dem von :option:`deletion_grace_period:deactivation`.

  Ist der Wert von :option:`deletion_grace_period:deletion`\ ``=0``, wird
  sofort, während des Imports, gelöscht.

  Ist der Wert größer als ``0``, wird ein Verfallsdatum im |UCSUDM|-Attribut
  ``ucsschoolPurgeTimestamp`` gespeichert. Der Benutzer wird erst an diesem Tag
  durch einen Cron Job gelöscht.

* Das Benutzerkonto wird erst deaktiviert und später gelöscht.

  Dies entspricht dem Deaktivieren oder Setzen eines Kontoablaufdatums im
  |UCSUMC|-Modul *Benutzer* und späteren Löschens in selbigem. Der
  Benutzer wird zuerst deaktiviert und kann sich nicht mehr anmelden, aber erst
  zu dem gesetzten Datum gelöscht.

  Bis zum finalen Löschen kann das Benutzerkonto noch reaktiviert werden, sollte
  es durch einen Import wieder *angelegt* werden.

  Diese Variante wird ausgewählt durch das Setzen von
  :option:`deletion_grace_period:deletion` auf einen Wert größer dem von
  :option:`deletion_grace_period:deactivation`.

  Ist der Wert von :option:`deletion_grace_period:deactivation`\ ``=0``, wird
  der Account sofort, während des Imports, deaktiviert.

  Ist der Wert größer als ``0``, wird ein Verfallsdatum im |UCSUDM|-Attribut
  ``user_expiry`` gespeichert. Der Benutzer kann sich ab diesem Tag nicht mehr
  anmelden. Der Wert von :option:`deletion_grace_period:deletion` wird, wie in
  der ersten Variante beschrieben, im |UCSUDM|-Attribut
  ``ucsschoolPurgeTimestamp`` gespeichert und die Löschung später durch einen
  Cron Job durchgeführt.

.. warning::

   Der Cron Job, welcher Benutzer anhand des ``ucsschoolPurgeTimestamp`` löscht,
   ignoriert alle Benutzer, die keine ``ucsschoolRole`` haben, die von der |UCSUAS| Importsoftware erkannt wird.
   Das betrifft vor allem auch Schuladministratoren, da diese nicht über die Importsoftware verwaltet werden können.

Um eine der Löschvarianten zu ändern oder neue hinzuzufügen, muss von der Klasse
:py:class:`ucsschool.importer.mass_import.user_import.UserImport` abgeleitet und
die Methode :py:meth:`~ucsschool.importer.mass_import.user_import.UserImport.do_delete` überschrieben werden (siehe
:ref:`extending-subclassing`).
