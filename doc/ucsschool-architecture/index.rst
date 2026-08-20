.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _architecture:

#############################
|UCSUAS| - Architektur-Sicht
#############################

Dieses Dokument beschreibt |UCSUAS| als fachliche Erweiterung auf UCS/Nubus. Es
gibt Partnern und anderen Interessierten eine gemeinsame, weiterentwickelbare
Architektursicht auf die Plattform.

.. note::

   Dieses Dokument befindet sich im Entwurfsstadium. Inhalte, Abgrenzungen und
   Begriffe können sich noch ändern.

|UCSUCS| (UCS) beziehungsweise Nubus bildet die generische Basis für
Identitätsmanagement, Verzeichnisdienst, Management-Oberflächen,
Authentifizierung, Provisionierung und Domänenbetrieb. Die Dokumentation trennt
bewusst zwischen dieser UCS/Nubus-Basis und den |UCSUAS|-Erweiterungen.

.. _architecture-target-picture:

Zielbild
========

|UCSUAS| ist keine separate Plattform neben UCS/Nubus, sondern baut auf dessen
IAM-, Management-, Verzeichnis- und Domänenfunktionen auf. |UCSUAS| ergänzt
schulische Rollen, Objekte, Prozesse, APIs und Standortlogik. Die Schichten,
in die sich diese Aufteilung gliedert, zeigt :numref:`arch-layers-fig`.

.. _architecture-audience:

Zielgruppen
===========

Dieses Dokument richtet sich an:

* Partner und Integratoren

* technische Entscheider

* Solution Architects

* Betreiber und Administratoren

* Entwickler mit Bezug zu |UCSUAS|-Integrationen

Für die Verwaltung und den Betrieb einer |UCSUAS|-Umgebung steht
:cite:t:`ucsschool-admin` bereit. Dieses Dokument ersetzt die dort beschriebenen
Abläufe nicht, sondern ordnet sie architektonisch ein.

.. toctree::
   :caption: Inhalt
   :numbered:

   goals-context
   overview
   layers
   components
   data-model
   interfaces
   integrations
   deployment
   data-flows
   operations-scaling
   sources
   changelog

.. toctree::
   :hidden:

   bibliography
