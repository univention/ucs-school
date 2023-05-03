.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _school-exam:

*******************
Klassenarbeitsmodus
*******************

Der Klassenarbeitsmodus ermöglicht die gezielte Einschränkung der
Computernutzung für Schüler einer Klasse. Über das UMC-Modul für den
Klassenarbeitsmodus kann ein Lehrer einen Klassenraum für die exklusive Nutzung
durch bestimmte Gruppen konfigurieren. Der Klassenarbeitsmodus bietet darüber
hinaus auch einen direkten Zugriff auf die Funktionalitäten der
Materialverteilung.

Hintergründe zur technischen Umsetzung werden in :ref:`school-exam-concept` und
mögliche Konfigurationsschnittstellen in :ref:`school-exam-configuration`
genannt.

Für die Dauer des Klassenarbeitsmodus werden die ausgewählten Schüler und Räume
in eine speziell benannte Gruppe aufgenommen. Dies macht es möglich mit Hilfe
von Windows-Gruppenrichtlinien spezifische Einschränkungen für die Benutzung von
Windows-Rechnern im gewählten Raum zu definieren, wie z.B. die Vorgabe eines
Proxy-Servers zur Filterung des Internetzugriffs, die Einschränkung den Zugriffs
auf USB-Speicher und andere Wechselmedien oder auch die Sperrung bestimmter
Programme. Einsatzmöglichkeiten für Gruppenrichtlinien werden in
:ref:`school-exam-gpo` beispielhaft beschrieben.

.. toctree::

   concept
   configuration
   examples-gpos
