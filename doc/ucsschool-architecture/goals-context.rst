.. SPDX-FileCopyrightText: 2025-2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _arch-goals:

****************
Ziel und Kontext
****************

.. _arch-goals-goal:

Ziel
====

Dieses Dokument bietet eine Architektur-Sicht auf |UCSUAS|. Der Schwerpunkt
liegt auf der Trennung zwischen der generischen UCS/Nubus-Plattform und den
schulischen Erweiterungen von |UCSUAS|.

.. _arch-goals-context:

Kontext
=======

UCS/Nubus liefert die Basis für Identitätsmanagement, Verzeichnisdienst,
Management-Oberfläche, Authentifizierung, Provisionierung und Domänenbetrieb.
|UCSUAS| nutzt diese Basis und erweitert sie für Schulen und Schulträger.

.. _arch-goals-questions:

Leitfragen
==========

Das Dokument beantwortet die folgenden Fragen:

* Welche Fähigkeiten bringt UCS/Nubus bereits mit?

* Welche fachlichen und technischen Erweiterungen liefert |UCSUAS|?

* Wo liegen zentrale Daten und über welche Schnittstellen werden sie verändert?

* Wie werden Schulen, Schulstandorte und Schulserver abgebildet?

* Welche Integrationspunkte gibt es für Partner?

.. _arch-goals-non-goals:

Nicht-Ziele
===========

Die folgenden Punkte sind nicht Gegenstand dieses Dokuments:

* vollständige Installationsanleitung

* Ersatz für die offizielle Univention-Dokumentation

* detaillierte Betriebsdokumentation jeder Komponente

* verbindliche Produktaussagen ohne Quellenprüfung
