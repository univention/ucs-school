.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _audience:
.. _introduction:

#########################################################
UCS\@school - Handbuch für den grafischen Benutzer-Import
#########################################################

Dieses Dokument richtet sich an:

* Mitarbeiter, die den grafischen Import von Benutzern durchführen

* ab Abschnitt :ref:`install-conf-format` an Administratoren, die ihn
  installieren und konfigurieren.


.. versionadded:: 4.2v6

   |UCSUAS| bringt seit der Version 4.2 v6 ein UMC-Modul mit, das es ermöglicht,
   sicher und komfortabel Benutzerdaten aus CSV-Dateien zu importieren.

Über ein flexibles Sicherheitskonzept kann einzelnen Benutzern oder ganzen
Gruppen die Berechtigung gegeben werden, Importe für bestimmte Schulen
durchführen und deren Ergebnisse einsehen zu können.

Technisch basiert das UMC-Modul *Benutzerimport* auf Komponenten der Software,
die in :external+uv-ucsschool-import:doc:`UCS@school-Handbuch zur
CLI-Import-Schnittstelle <index>` beschrieben sind. Die Konfiguration dieser
Komponenten ist nicht Teil dieses Dokuments.

.. toctree::
   :numbered:

   import
   install
   test
   single-source
