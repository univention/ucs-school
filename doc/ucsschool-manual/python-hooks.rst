.. SPDX-FileCopyrightText: 2021-2023 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _pyhooks:

************
Python-Hooks
************

.. versionadded:: 4.4v9

   Ab |UCSUAS| 4.4 v9 kann vor und nach dem Anlegen, Ändern, Verschieben und
   Löschen von |UCSUAS| Objekten Python-Code ausgeführt werden. Dies kann z.B.
   im Rahmen des |UCSUAS| Imports von eingesetzt werden, um in Abhängigkeit von
   der jeweiligen Umgebung weitere Einstellungen vorzunehmen.

Python-Hooks, im folgenden Abschnitt abgekürzt mit *Hooks*, erlauben es
Objekttypen zu unterscheiden (z.B. Schulklasse und Arbeitsgruppe oder Schüler
und Lehrer) und haben Zugriff auf alle Attribute der Objekte.

Die Hooks werden für alle Klassen, von denen Objekte erzeugt werden können und
die von ``ucsschool.lib.models.base.UCSSchoolHelperAbstractClass`` ableiten,
ausgeführt. Diese Klassen finden sich in im Python Paket
``ucsschool.lib.models`` (z.B. ``Student``, ``SchoolClass``, ``Workgroup``).

.. caution::

   Hooks werden nur auf dem System ausgeführt, auf dem sie installiert sind. In
   der Regel ist das der |UCSPRIMARYDN|, sowie alle |UCSBACKUPDN| Server. Sollen
   Hooks auch auf |UCSREPLICADN| Servern ausgeführt werden, so müssen sie auch
   dort installiert werden. Eine automatische Verteilung der Hook Dateien findet
   nicht statt.

Hooks für |UCSUAS| Objekte ähneln den bekannten Hooks für den Benutzerimport
(siehe :cite:t:`ucsschool-import`), werden jedoch auch ohne den Import
zu verwenden ausgeführt und haben einige andere Attribute.

Zur Nutzung der Hook-Funktionalität muss eine eigene Python-Klasse erstellt
werden, die von :py:class:`ucsschool.lib.models.hook.Hook` ableitet. In der
Klasse können Methoden :py:meth:`~ucsschool.lib.models.hook.Hook.pre_create`,
:py:meth:`~ucsschool.lib.models.hook.Hook.post_create`, etc. definiert werden,
welche zum jeweiligen Zeitpunkt ausgeführt werden. Der Name der Datei mit der
abgeleiteten Klasse muss auf :file:`.py` enden und im Verzeichnis
:file:`/var/lib/ucs-school-lib/hooks` abgespeichert werden.

Zwei Beispiele finden sich auf Servern der Rolle |UCSPRIMARYDN| in
:file:`hook_example1.py` und :file:`hook_example2.py` unter
:file:`/usr/share/doc/ucs-school-lib-common/` bzw. online auf
`https://github.com/.../hook_example1.py <gh-ucsschool-hook-example1_>`_ und
`https://github.com/.../hook_example2.py <gh-ucsschool-hook-example2_>`_.

Im Folgenden wird anhand des Beispiels in :file:`hook_example2.py` erklärt, wie
mit Hilfe eines Hooks jeder Schulklasse eine E-Mailadresse zugeordnet werden
kann.

.. warning::

   Das Beispiel ist lauffähig, aber nicht für den Produktivbetrieb geeignet.
   Dafür bräuchte es u.a. zusätzlichen Code, um robust mit existierenden
   E-Mailadressen umzugehen.

Ein Python-Hook ist eine Klasse, die von
:py:class:`ucsschool.lib.models.hook.Hook` ableitet und einige Attribute und
Methoden definiert.

.. py:class:: MailForSchoolClass

   .. code-block:: python

      from ucsschool.lib.models.group import SchoolClass
      from ucsschool.lib.models.hook import Hook

      class MailForSchoolClass(Hook):
          model = SchoolClass
          priority = {
              "post_create": 10,
              "post_modify": 10,
          }

          def post_create(self, obj):  # type: (SchoolClass) -> None
              ...

          def post_modify(self, obj):  # type: (SchoolClass) -> None
              ...

.. py:class:: ucsschool.lib.models.hook.Hook

   .. py:attribute:: model

      Das Klassenattribut ``model`` bestimmt, für welche Objekte welchen Typs
      der Hook ausgeführt wird. Der Hook wird auch für Objekte von Klassen
      ausgeführt, die von der angegebenen ableiten. Wäre ``model = Teacher``
      (aus :py:mod:`ucsschool.lib.models`), so würde der Hook auch für Objekte
      der Klasse ``TeachersAndStaff`` ausgeführt, nicht aber für solche vom Typ
      ``Staff`` oder ``Student``.

   .. py:attribute:: priority

      Das Klassenattribut ``priority`` bestimmt die Reihenfolge in der Methoden
      von Hooks des gleichen Typs (gleiches :py:attr:`model`) ausgeführt werden
      bzw. deaktiviert sie.

      Methoden mit höheren Zahlen werden zuerst ausgeführt. Ist der Wert
      ``None`` oder die Methode nicht aufgeführt, wird sie deaktiviert.

      Angenommen es gäbe eine weitere Klasse mit einem Hook mit ``model =
      SchoolClass`` und diese würde ``priority = {"post_create": 20}``
      definieren, so würde deren :py:meth:`post_create` Methode **vor**
      :py:meth:`MailForSchoolClass.post_create` ausgeführt.

   .. py:method:: pre_create

      Alle Methoden der Klasse, z.B. :py:meth:`pre_create` oder
      :py:meth:`post_create`, empfangen ein Objekt vom Typ, bzw. des davon
      abgeleiteten Typs, der in :py:attr:`model` definiert wurde, als Argument ``obj``
      und geben nichts zurück.

   .. py:method:: post_create

      Siehe :py:meth:`pre_create`

Die :py:meth:`~ucsschool.lib.models.hook.Hook.post_create` Methode sieht wie folgt aus:

.. code-block:: python

   def post_create(self, obj):  # type: (SchoolClass) -> None
   """
   Create an email address for the new school class.

   :param SchoolClass obj: the SchoolClass instance, that was just created.
   :return: None
   """
       ml_name = self.name_for_mailinglist(obj)
       self.logger.info("Setting email address %r on school class %r...", ml_name, obj.name)
       udm_obj = obj.get_udm_object(self.lo)  # access the underlying UDM object
       udm_obj["mailAddress"] = ml_name
       udm_obj.modify()


Die Klasse ``SchoolClass`` bietet kein Attribut an, um eine E-Mailadresse
anzugeben. Die Klassen in :py:mod:`ucsschool.lib.models` sind jedoch tatsächlich
eine Abstraktion regulärer |UCSUDM| Objekte. Um auf die darunter liegenden
Objekte zuzugreifen, wird die Methode :py:meth:`get_udm_object` verwendet. Als
Argument muss ihr ein sogenanntes LDAP Verbindungsobjekt (``lo``) mitgegeben
werden.

Die Instanzvariablen :py:attr:`self.lo`, :py:attr:`self.logger` und
:py:attr:`self.ucr` sind nach der Ausführung von :py:meth:`__init__` verfügbar.
Es handelt sich bei ihnen um die Instanz eines LDAP Verbindungsobjekts, einer
Instanz von Python :py:class:`~logging.Logger` und einer Instanz von |UCSUCR|.

Soll eigener Code zur Initialisierung ausgeführt werden, so sollte
:py:meth:`__init__` folgendermaßen implementiert werden:

.. code-block:: python

   class MailForSchoolClass(Hook):
       def __init__(self, lo, *args, **kwargs):
           super(MailForSchoolClass, self).__init__(lo, *args, **kwargs)
           # From here on self.lo, self.logger and self.ucr are available.
           # You code here.


Zwei Funktionen helfen dabei, aus dem Namen der Schulklasse und einem
Domänennamen, eine E-Mailadresse zu erzeugen:

.. code-block:: python

   def name_for_mailinglist(self, obj):  # type: (SchoolClass) -> str
       return "{}@{}".format(obj.name, self.domainname).lower()

   @property
   def domainname(self):  # type: () -> str
       try:
           return self.ucr["mail/hosteddomains"].split()[0]
       except (AttributeError, IndexError):
           return self.ucr["domainname"]


Um E-Mailadresse auch für umbenannte Schulklassen zu ändern, wird
:py:meth:`post_modify` implementiert:

.. code-block:: python

   def post_modify(self, obj):  # type: (SchoolClass) -> None
       """
       Change the email address of an existing school class.

       :param SchoolClass obj: the SchoolClass instance, that was just modified.
       :return: None
       """
       udm_obj = obj.get_udm_object(self.lo)
       ml_name = self.name_for_mailinglist(obj)
       if udm_obj["mailAddress"] != ml_name:
           self.logger.info(
               "Changing the email address of school class %r from %r to %r...",
               obj.name,
               udm_obj["mailAddress"],
               ml_name,
           )
           udm_obj["mailAddress"] = ml_name
           udm_obj.modify()


Die Datei mit obigem Python Code kann nun im Verzeichnis
:file:`/var/lib/ucs-school-lib/hooks` abgespeichert werden. Soll der Hook von
einem UMC-Modul verwendet werden, muss zuerst der UMC-Server neu gestartet
werden:

.. code-block:: console

   $ service univention-management-console-server restart


Um den Hook zu testen, kann eine interaktive Python Shell verwendet werden.
Einige Ausgaben wurden im folgenden Beispiel zur Verbesserung der Lesbarkeit
gekürzt:

.. code-block:: pycon

   >>> import logging
   >>> from ucsschool.lib.models.group import SchoolClass
   >>> from univention.admin.uldap import getAdminConnection

   >>> logging.basicConfig(level=logging.DEBUG, format="%(message)s", handlers=[logging.StreamHandler()])
   >>> lo, _ = getAdminConnection()

   >>> sc = SchoolClass(name="DEMOSCHOOL-igel", school="DEMOSCHOOL")
   >>> sc.create(lo)

   Starting SchoolClass.call_hooks('pre', 'create', lo('cn=admin,dc=exam,dc=ple')) for SchoolClass(
       name='DEMOSCHOOL-igel', school='DEMOSCHOOL', dn='cn=DEMOSCHOOL-igel,cn=klassen,cn=schueler,
       cn=groups,ou=DEMOSCHOOL,dc=exam,dc=ple').
   Searching for hooks of type 'Hook' in: /var/lib/ucs-school-lib/hooks...
   Found hook classes: MailForSchoolClass
   Loaded hooks: {'post_modify': ['MailForSchoolClass.post_modify'], 'post_create': [
       'MailForSchoolClass.post_create']}.
   Creating SchoolClass(name='DEMOSCHOOL-igel', school='DEMOSCHOOL', dn='...')
   SchoolClass(name='DEMOSCHOOL-igel', school='DEMOSCHOOL', dn='...') successfully created
   Starting SchoolClass.call_hooks('post', 'create', lo('cn=admin,dc=uni,dc=dtr')) for SchoolClass(
       name='DEMOSCHOOL-igel', school='DEMOSCHOOL', dn='...').
   Running post_create hook MailForSchoolClass.post_create for SchoolClass(name='DEMOSCHOOL-igel',
       school='DEMOSCHOOL', dn='...')...
   Setting email address 'demoschool-igel@uni.dtr' on SchoolClass(name='DEMOSCHOOL-igel',
       school='DEMOSCHOOL', dn='...')...
   True

   >>> sc.name = "DEMOSCHOOL-hase"
   >>> sc.modify(lo)

   Starting SchoolClass.call_hooks('pre', 'modify', lo('cn=admin,dc=exam,dc=ple')) for SchoolClass(
       name='DEMOSCHOOL-hase', school='DEMOSCHOOL', dn='cn=DEMOSCHOOL-hase,...', old_dn='cn=DEMOSCHOOL-igel,...').
   Modifying SchoolClass(name='DEMOSCHOOL-hase', school='DEMOSCHOOL', dn='cn=DEMOSCHOOL-hase,...',
       old_dn='cn=DEMOSCHOOL-igel,...')
   SchoolClass(name='DEMOSCHOOL-hase', school='DEMOSCHOOL', dn='cn=DEMOSCHOOL-hase,...') successfully modified
   Starting SchoolClass.call_hooks('post', 'modify', lo('cn=admin,dc=exam,dc=ple')) for SchoolClass(
       name='DEMOSCHOOL-hase', school='DEMOSCHOOL', dn='cn=DEMOSCHOOL-hase,...').
   Running post_modify hook MailForSchoolClass.post_modify for SchoolClass(name='DEMOSCHOOL-hase',
       school='DEMOSCHOOL', dn='cn=DEMOSCHOOL-hase,...')...
   Changing the email address of SchoolClass(name='DEMOSCHOOL-hase', school='DEMOSCHOOL', ...)
       from 'demoschool-igel@example.com' to 'demoschool-hase@example.com'...
   True


Im Verzeichnis :file:`/var/lib/ucs-school-lib/hooks/` wird nach Python-Hooks
gesucht und die Klasse :py:class:`MailForSchoolClass` gefunden. Nach dem Laden
aller Hooks wird angezeigt, in welcher Reihenfolge welche Methoden für welche
Phase ausgeführt werden. Da es keine
:py:meth:`~ucsschool.lib.models.hook.Hook.pre_create` Hooks gibt, wird nun das
Objekt angelegt. Anschließend werden
:py:meth:`~ucsschool.lib.models.hook.Hook.post_create` Hooks ausgeführt. Erneut
wird zuerst nach Hook-Skripten gesucht. Anschließend wird
:py:class:`MailForSchoolClass`\ .\
:py:meth:`~ucsschool.lib.models.hook.Hook.post_create` ausgeführt. Beim
``sc.modify(lo)`` passiert das Gleiche.
