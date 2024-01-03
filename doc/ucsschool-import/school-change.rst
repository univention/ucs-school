.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-change:

************
Schulwechsel
************

Bei einem Schulwechsel verlässt ein Schüler oder Lehrer seine ursprüngliche
Schule *A* und wird an einer anderen Schule *B* aufgenommen. Hierbei sind
folgende Szenarien denkbar:

#. Schule *A* und Schule *B* werden vom gleichen Quellverzeichnis abgedeckt und
   gemeinsam verwaltet. D.h. die für den Benutzer hinterlegte Schule ändert sich
   in einem Schritt von Schule *A* auf Schule *B*. Die Importsoftware kann das
   Benutzerobjekt verschieben, ohne dass sich Daten wie Benutzername, User-ID,
   Telefonnummer oder Passwort ändern.

#. Schule *A* und Schule *B* werden vom gleichen Quellverzeichnis abgedeckt, die
   beiden Schulverwaltungen pflegen die Daten ihrer Schüler oder Lehrer jedoch
   unabhängig voneinander. Der Schulwechsel findet also in zwei Schritten statt.
   Es können zwei Szenarien auftreten:

   a. Der Benutzer wird an Schule *A* entfernt und erst später an Schule *B* neu
      aufgenommen. Wurde das Benutzerkonto gelöscht und nicht deaktiviert, verliert
      der Benutzer alle Benutzerdaten und erhält ein komplett neues Benutzerkonto
      inkl. Benutzernamen, User-ID, Passwort etc.

   #. Der Benutzer wird an Schule *B* aufgenommen, bevor er an Schule *A* entfernt
      wird. Das Benutzerkonto wird kurzfristig an zwei Schulen repliziert,
      die Daten bleiben während der gesamten Zeit (auch nach Entfernen von
      Schule *A*) erhalten.

#. Schule *A* und Schule *B* werden von unterschiedlichen Quellverzeichnissen
   abgedeckt. Der Benutzer wird in Schule *A* entfernt und vorher oder später in
   Schule *B* neu angelegt. Der Benutzer erhält dann einen neuen Benutzernamen,
   User-ID, Passwort etc. Das Übernehmen des Benutzerkontos ist nicht ohne
   weiteres möglich.
