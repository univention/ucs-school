.. SPDX-FileCopyrightText: 2021-2024 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _extending:

**********************************
Erweiterung um neue Funktionalität
**********************************

Die |UCSUAS| Importsoftware ist so geschrieben worden, dass ihre Funktionalität
möglichst einfach und gleichzeitig umfangreich veränderbar und erweiterbar ist.
Dazu stehen zwei Methoden zur Verfügung:

* Das Ausführen von Aktionen zu bestimmten Zeitpunkten mit der Hilfe von
  Python-Hooks.

* Die Veränderung der Importsoftware durch das Überschreiben von Teilen des
  Programmcodes.

Setzt eine Erweiterung eine bestimmte Konfiguration voraus, können zusätzliche
Prüfungen registriert werden, die vor dem Start des Importvorganges gestartet
werden.

.. _extending-import-user-class:

Die :py:class:`ImportUser` Klasse
=================================

.. py:class:: ImportUser

   Die Klasse ``ImportUser`` wird verwendet, um Daten von eingelesenen oder zu
   ändernden Benutzern zu speichern. An Objekten der :py:class:`ImportUser`
   Klasse können folgende Attribute gesetzt werden:

   .. py:attribute:: name
      :type: str

      Benutzername


   .. py:attribute:: school
      :type: str

      Primäre Schule des Benutzers (Position des Objektes im LDAP).


   .. py:attribute:: schools
      :type: str, list

      Alle Schulen des Benutzers inkl. der primären Schule, als ein
      kommaseparierter String oder als Liste von Strings.


   .. py:attribute:: firstname
      :type: str

      Vorname


   .. py:attribute:: lastname
      :type: str

      Nachname


   .. py:attribute:: birthday
      :type: str

      Geburtstag im Format ``JJJJ-MM-TT``

   .. py:attribute:: expiration_date

      Ablaufdatum für das Benutzerkonto im Format ``JJJJ-MM-TT``

   .. py:attribute:: email
      :type: str

      E-Mailadresse


   .. py:attribute:: password
      :type: str

      Passwort. Wird für neue Benutzer automatisch erzeugt, wenn nicht in den
      Eingabedaten vorhanden.


   .. py:attribute:: disabled
      :type: bool

      Definiert, ob ein neuer Benutzer deaktiviert erzeugt werden soll.


   .. py:attribute:: school_classes
      :type: str, object

      Klassen in denen der Benutzer ist.

      Als String im Format ``schule1-1A,schule1-2B,schule2-1A`` oder als Python
      Dictionary: ``{"schule1": ["1A", "2B"], "schule2": ["1A"]}``. Bei Nutzung des
      Python Dictionaries wird der Präfix implizit durch die Struktur übernommen.

      .. hint::

         Geben Sie **immer** den Schul-Präfix für Schulklassen an, auch wenn
         der Import Schulklassen ohne den Schul-Präfix in einer CSV-Datei
         erfolgreich importieren kann. Der Import ohne Schul-Präfix kann zu
         undefiniertem Verhalten und erhöhten Support-Aufwänden führen.

      .. warning::

         Wenn Schulklassen keinen Schul-Präfix in der CSV-Datei angeben, dürfen
         die Namen für die Schulklassen **keine** Bindestriche enthalten, weil
         der Import sonst fehlschlägt.


      Es können Klassen aus mehreren Schulen aufgelistet werden; diese Schulen
      müssen alle in :py:attr:`ImportUser.schools` auftauchen.

      Falls die Klassenzuordnung nicht per Import stattfinden soll, weil z.B. die
      Klassenzuordnungen der Lehrkräfte über die UMC-Module *Klassen zuordnen* bzw.
      *Lehrer zuordnen* stattfinden sollen, kann in der Konfiguration
      ``school_classes_keep_if_empty`` auf ``true`` gesetzt werden. Der Import
      verhält sich dann so, dass wenn der Wert für ``school_classes`` leer ist,
      bestehende Klassenzuordnungen nicht verändert werden.


   .. py:attribute:: source_uid
      :type: str

      Kennzeichnung der Datenquelle


   .. py:attribute:: record_uid
      :type: str

      ID des Benutzers in der Datenquelle


   .. py:attribute:: udm_properties
      :type: object

      Alle anderen |UCSUDM| Attribute, die in den Eingabedaten enthalten waren,
      werden in dieses Python Dictionary gespeichert.

      Oben stehende Attribute und ihre |UCSUDM|-Pendants (``name`` →
      ``username``, ``email`` → ``mailPrimaryAddress``) sind hier nicht erlaubt.


Weitere interessante Attribute, die jedoch nur gelesen und nicht modifiziert
werden sollten, sind:

.. py:class:: ImportUser
   :noindex:

   .. py:attribute:: dn
      :type: str

      DN des Benutzer-Objekts im LDAP, wenn es jetzt gespeichert werden würde.


   .. py:attribute:: entry_count
      :type: int

      Zeile in CSV-Datei, aus der Daten des Benutzers stammen. Ist ``0``, wenn
      dies nicht zutrifft.


   .. py:attribute:: input_data
      :type: list

      Unveränderte Eingabedaten aus der CSV-Datei, bereits zu Elementen einer
      Liste aufgeteilt.


   .. py:attribute:: ucr
      :type: object

      Eine |UCSUCR|-Instanz zum Auslesen von |UCSUCR|-Einstellungen.



.. _extending-hooks:

Hooks
=====

`Hooks <https://de.wikipedia.org/wiki/Hook_(Informatik)>`_ sind Stellen im
Programmcode, an die zusätzlicher Code *angehängt* werden kann. Für den
Benutzerimport sind acht Stellen vorgesehen: jeweils vor und nach dem Anlegen,
Ändern, Löschen oder Verschieben von Benutzern.

Zusätzlich gibt es Format-Hooks die vor dem Erstellen eines Attributes aus
anderen Attributen (siehe :ref:`configuration-scheme-formatting`) ausgeführt
werden. Diese werden weiter unten in :ref:`extending-hooks-format-hooks` separat
behandelt.

Zur Nutzung der Hook-Funktionalität muss eine eigene Python-Klasse erstellt
werden, die von :py:class:`ucsschool.importer.utils.user_pyhook.UserPyHook`
ableitet. In der Klasse können Methoden
:py:meth:`~ucsschool.importer.utils.user_pyhook.UserPyHook.pre_create`,
:py:meth:`~ucsschool.importer.utils.user_pyhook.UserPyHook.post_create`, etc.
definiert werden, welche zum jeweiligen Zeitpunkt ausgeführt werden. Der Name
der Datei mit der eigenen Klasse muss auf :file:`.py` enden und im Verzeichnis
:file:`/usr/share/ucs-school-import/pyhooks` abgespeichert werden.

.. note::

   Der Quellcode der Klasse
   :py:class:`~ucsschool.importer.utils.user_pyhook.UserPyHook` ist zu finden in
   :file:`/usr/lib/python3/dist-packages/ucsschool/importer/utils/user_pyhook.py`.

   Dort sind alle Methoden und Signaturen dokumentiert.

Die Methoden der Hook-Klasse bekommen als Argument das Benutzerobjekt übergeben,
das aus dem LDAP geladen wurde bzw. im LDAP gespeichert werden soll.
Veränderungen an diesem Objekt werden bei dessen Abspeicherung direkt ins LDAP
übernommen.

Die Klasse definiert ein Python Dictionary ``priority``, mit dessen Hilfe eine
Reihenfolge definiert werden kann, sollten mehrere Hook-Klassen mit zum Einsatz
kommen, die die gleichen Methoden definieren.

Die Namen der Methoden, die ausgeführt werden sollen, sind die Schlüssel.
Methoden mit höheren Zahlen werden zu erst ausgeführt. Ist der Wert ``None``,
wird die Methode deaktiviert.

Zur Erstellung einer eigenen Hook-Klasse kann das Beispiel in
:file:`/usr/share/doc/ucs-school-import/hook_example.py` kopiert und angepasst
werden. Alle Funktionen die nicht ausgeführt werden sollen, sollten entweder
gelöscht oder deaktiviert werden (indem ihr Wert in ``priority`` auf ``None``
gesetzt wird). Das könnte Beispielsweise so aussehen:

.. code-block:: python

   import datetime
   import shutil

   from ucsschool.importer.utils.user_pyhook import UserPyHook

   class MyHook(UserPyHook):
       supports_dry_run = True  # Hook Klasse wird auch während eines
                                # dry-runs ausgeführt
       priority = {
           "pre_create": 1,
           "post_create": None,  # Funktion ist deaktiviert
           "pre_remove": 1
       }

       def pre_create(self, user):
           if user.birthday:
               bday = datetime.datetime.strptime(user.birthday,
                                                 "%Y-%m-%d").date()
               if bday == datetime.date.today():
                   self.logger.info("%s has birthday.", user)
                   user.udm_properties["description"] = "Herzlichen \
                                                         Glückwunsch"

       def post_create(self, user):
           # Diese Funktion ist deaktiviert.
           self.logger.info("Running a post_create hook for %s.", user)

       def pre_remove(self, user):
           # backup users home directory
           self.logger.info("Backing up home directory of %s.", user)
           user_udm = user.get_udm_object(self.lo)
           homedir = user_udm["unixhome"]
           target = "/var/backup/{}".format(user.name)
           if self.dry_run:
               self.logger.info("Dry-run: would copy %r to %r.", homedir, target)
           else:
               shutil.copy2(homedir, target)


* Da die Variable ``supports_dry_run = True`` gesetzt ist, wird der Hook auch
  während eines ``dry-run`` ausgeführt.

* In :py:meth:`~ucsschool.importer.utils.user_pyhook.UserPyHook.pre_create` wird
  bei einem neuen Benutzer ein Gruß am Benutzerobjekt gespeichert, wenn er
  Geburtstag hat.

* Die :py:meth:`~ucsschool.importer.utils.user_pyhook.UserPyHook.post_create`
  Funktion ist durch das ``None`` in ``priority`` deaktiviert.

* In :py:meth:`~ucsschool.importer.utils.user_pyhook.UserPyHook.pre_remove`
  wird, wenn nicht während eines ``dry-run`` ausgeführt, ein Backup des
  Heimatverzeichnisses des Benutzers gemacht, bevor er gelöscht wird.

In :py:meth:`~ucsschool.importer.utils.user_pyhook.UserPyHook.pre_create` wird
in ``udm_properties`` an den Schlüssel ``description`` der Wert ``Herzlichen
Glückwunsch`` geschrieben. Das explizite Abspeichern des ``user`` Objektes ist
in dieser Funktion nicht nötig, da dies ja beim auf den Hook folgenden
``create`` geschieht.

In der Funktion wird außerdem mit ``self.logger.info()`` ein Text zu Protokoll
gegeben. Es handelt sich bei ``self.logger`` um eine Instanz eines
:py:mod:`Python logging <logging>` Objekts.


In :py:meth:`~ucsschool.importer.utils.user_pyhook.UserPyHook.pre_remove` wird
das Heimatverzeichnis des Benutzers benötigt. Da dies nicht eines der direkt am
Objekt stehenden Daten ist (siehe :ref:`extending-import-user-class`), muss
zuerst das gesamte Benutzerobjekt aus dem LDAP geladen werden. Dies macht
``user.get_udm_object()``, welches als Argument ein LDAP-Verbindungsobjekt
erwartet. Dieses ist im Hook-Objekt an ``self.lo`` gespeichert.

.. caution::

   Falls das Benutzerobjekt in einem *post-Hook* geändert werden soll, so ist es
   möglich ``user.modify_without_hooks()`` auszuführen, aber generell sollte ein
   erneutes Modifizieren *nach* dem Speichern vermieden werden.

   Die Methoden ``create()``, ``modify()`` und ``remove()`` des Benutzerobjekts
   sollten von Hook-Methoden nicht ausgeführt werden, da dies zu einer Rekursion
   führen kann.

.. _extending-hooks-format-hooks:

Format-Hooks
------------

Format-Hooks erlauben es, Attribute nur für den Zeitraum ihrer Verwendung als
Daten eines Formatierungsschemas zu modifizieren. Der häufigste Anwendungsfall
ist die Kürzung von Vor- und Nachnamen während der Erzeugung von E-Mailadressen
und Benutzernamen.

Die eckigen Klammern im Formatierungsschema erlauben es zwar die Länge von
Attributen statisch einzuschränken, aber sie erlauben z.B. kein Trennen an
bestimmten Zeichen. Ein Beispiel für einen Format-Hook bei der Erzeugung der
Attribute ``username`` und ``email``, die Attribute ``firstname`` und
``lastname`` an Freizeichen und Bindestrichen trennt, ist in
:file:`/usr/share/doc/ucs-school-import/format_hook_example.py` zu finden.

Ein Format-Hook ist eine Klasse, die von
:py:class:`ucsschool.importer.utils.format_pyhook.FormatPyHook` abgeleitet ist.
Der Name der Datei mit der eigenen Klasse muss, wie bei den regulären
``PyHooks``, auf :file:`.py` enden und im Verzeichnis
:file:`/usr/share/ucs-school-import/pyhooks` abgespeichert werden.

Format-Hooks haben die Methoden :py:meth:`patch_fields_staff`,
:py:meth:`patch_fields_student`, :py:meth:`patch_fields_teacher` und
:py:meth:`patch_fields_teacher_and_staff` von der immer nur diejenige aufgerufen
wird, die zu der Rolle des zu erzeugenden / bearbeitenden Benutzers passt.

``priority`` hat die gleiche Funktion wie bei den regulären ``PyHooks``. Das
Klassenattribut ``properties`` enthält eine Liste von Attributnamen. Der
Format-Hook wird nur für diese Attribute ausgeführt. Das Beispiel würde nur bei
der Erzeugung von ``username`` und ``email`` ausgeführt und bei ``birthday``,
``firstname``, ``school_classes``, usw. nicht. Hier können auch
|UCSUDM|-Attribute aus ``udm_properties`` aufgeführt werden. Aus Gründen der
Performance ist es wichtig hier nur die Attribute aufzuführen, die tatsächlich
geändert werden sollen.

Den Methoden werden die Argumente ``property_name`` und ``fields`` übergeben.
``property_name`` enthält den Namen des Benutzerattributs, das gerade erzeugt
werden soll und ``fields`` ist ein Python Dictionary, welches alle Attribute und
Werte des Benutzerobjekts zu diesem Zeitpunkt enthält, aus denen besagtes
Attribut berechnet werden soll. Durch das Ändern von Werten in ``fields`` wird
Einfluss genommen auf das Ergebnis des darauf folgenden Formatierens.

Im Beispiel werden bei ``staff`` und ``teacher`` Benutzern die Vor- und
Nachnamen getrennt, wenn das ``username`` Attribut erzeugt wird, und bei
``student`` und ``teacher_and_staff`` bei der Erzeugung von ``email``.

Stünde in der Konfiguration z.B. :option:`csv:mapping`\
``:email=<firstname><lastname>@<maildomain>``, so würde bei der Erzeugung des
``email`` Attributs eines *students* ein Vorname ``Hans-Otto`` gekürzt zu
``Hans``. Mit einem Nachnamen ``Mayer`` und einer Domäne ``univention.de`` würde
daraus die E-Mailadresse ``hans.mayer@univention.de`` erzeugt.

Die Modifikationen eines Format-Hooks sind nur während der Erzeugung *eines*
Attributs gültig. Sie haben weder direkte Auswirkung auf das Benutzerobjekt noch
auf die Erzeugung anderer Attribute.

Existieren mehrere Format-Hooks für das *gleiche* Attribut, so werden sie
nacheinander ausgeführt und das von einem Format-Hook modifizierte ``fields``
Python Dictionary dem nächsten Format-Hook übergeben.

.. _extending-subclassing:

Subclassing
===========

Hooks erlauben das Ausführen von neuem Code zu bestimmten Zeitpunkten. Sie
erlauben aber nicht bestehenden Code zu verändern. In einer objektorientierten
Sprache wie Python wird dies üblicherweise getan, indem eine Klasse modifiziert
wird. Soll für einen bestimmten Fall nur ein Teil der Klasse verändert werden,
wird von ihr abgeleitet und nur dieser Teil verändert, der unveränderte Teil
wird geerbt.

Folgendes Beispiel zeigt, wie der Klasse, welche die historisch einmaligen
Benutzernamen erzeugt, eine weitere Variable hinzugefügt werden kann. Ein
weiteres Beispiel ist in
:file:`/usr/share/doc/ucs-school-import/subclassing_example.py` zu finden.

.. code-block:: python

   from ucsschool.importer.utils.username_handler import UsernameHandler

   class MyUsernameHandler(UsernameHandler):
       @property
       def counter_variable_to_function(self):
           name_function_mapping = super(MyUsernameHandler, self).counter_variable_to_function
           name_function_mapping["[ALWAYSWITHZEROS]"] = self.always_counter_with_zeros
           return name_function_mapping

       def always_counter_with_zeros(self, name_base):
           number_str = self.always_counter(name_base)
           number_int = int(number_str)
           new_number_str = "{:04}".format(number_int)
           return new_number_str


In :py:meth:`counter_variable_to_function` wird den existierenden beiden
Variablen eine weitere hinzugefügt und auf die neue Funktion verwiesen.
:py:meth:`always_counter_with_zeros` verwendet :py:meth:`always_counter` zur
Erzeugung der nächsten freien Zahl, schreibt diese aber dann so um, dass sie
immer vier Stellen lang ist und der Anfang mit Nullen aufgefüllt wird.

Wird die Klasse unter
:file:`/usr/lib/python3/dist-packages/usernames_with_zeros.py` abgespeichert, so
kann sie unter Python als :py:class:`usernames_with_zeros.MyUsernameHandler`
verwendet werden.

Ob Python die Klasse findet, lässt sich testen mit:

.. code-block:: console

   $ python3 -c 'from usernames_with_zeros import MyUsernameHandler'


Es sollte keine Ausgabe geben.

Die neue Funktionalität lässt sich testen mit:

.. code-block:: pycon

   # python3
   >>> from usernames_with_zeros import MyUsernameHandler
   >>> print(MyUsernameHandler(15).format_username("Anton[ALWAYSCOUNTER]"))
   Anton1
   >>> print(MyUsernameHandler(15).format_username("Anton[ALWAYSWITHZEROS]"))
   Anton0002
   >>> print(MyUsernameHandler(15).format_username("Anton[ALWAYSWITHZEROS]"))
   Anton0003
   >>> exit()


Es gibt jetzt eine neue Klasse mit der neuen Funktionalität. Die Importsoftware
muss nun noch dazu gebracht werden, diese neue, ihr nicht bekannte Klasse zu
verwenden.

.. _extending-subclassing-abstract-factory:

Abstract Factory
----------------

Die Architektur der Importsoftware ist als `Abstrakte Fabrik (*Abstract
Factory*) <https://de.wikipedia.org/wiki/Abstrakte_Fabrik>`_ implementiert. In
ihr wird die Erzeugung von Objekten zentralisiert. Sie zeichnet sich u.a.
dadurch aus, dass sie erlaubt, das Austauschen mehrerer Komponenten einer
Software konsistent zu halten. Im Fall der Importsoftware ist die *abstract
factory* jedoch nicht Abstrakt, alle Methoden wurden implementiert.

An allen Stellen der Importsoftware die z.B. mit dem Einlesen von CSV-Dateien zu
tun haben, wird nicht die Klasse
:py:class:`ucsschool.importer.reader.csv_reader.CsvReader` direkt instanziiert,
sondern es wird von der eingesetzten ``factory`` eine Instanz verlangt
(``factory.make_reader()``) und verwendet. Welche Klasse dem verwendeten Objekt
zugrunde liegt, ist nicht bekannt, sie muss nur die Methoden der ersetzten
Klasse mit der gleichen Signatur implementieren. Auf diese Art könnte z.B. der
:py:class:`~ucsschool.importer.reader.csv_reader.CsvReader` durch einen
:py:class:`JSON-Reader` ersetzt werden. Alles was dann zu tun bleibt, ist, die
``factory`` zu verändern. Dies kann auf zwei Arten geschehen:

* Überschreiben einzelner Methoden der :py:class:`DefaultUserImportFactory` Klasse.

* Ersetzen von :py:class:`DefaultUserImportFactory` durch eine eigene Klasse.

Welche Methode gewählt wird, hängt davon ab,ob die Anpassungen nur punktuell
sind, oder ob es sich um ein größeres Umschreiben der Importsoftware handelt.

.. _extending-subclassing-overwriting-factory-method:

Überschreiben einer Methode
---------------------------

Es ist möglich die Methoden der :py:class:`DefaultUserImportFactory` Klasse
einzeln zu überschreiben, ohne ihren Code zu ändern. Damit die ``factory``
Objekte der ``MyUsernameHandler`` Klasse aus dem obigen Beispiel beim Aufruf von
:py:meth:`make_username_handler` liefert, muss in die Konfiguration folgendes
eingetragen werden (siehe Konfigurationsoption :option:`classes`):

.. code-block:: json

   {
       "classes": {
           "username_handler": "usernames_with_zeros.MyUsernameHandler"
       }
   }


.. _extending-subclassing-replacing-factory-class:

Ersetzen durch eigene Klasse
----------------------------

Sollen umfangreichere Änderungen an der Importsoftware durchgeführt werden, kann
von
:py:class:`ucsschool.importer.default_user_import_factory.DefaultUserImportFactory`
abgeleitet und ihre Methoden ersetzt werden. In der Konfigurationsdatei kann die
zu nutzende ``factory``-Klasse über den Schlüssel :option:`factory` als voller
Python-Pfad angegeben werden.

Obiges Beispiel lässt sich anstatt in der Konfiguration :option:`classes`\
``:username_handler`` zu setzen auch so lösen:

.. code-block:: python

   from ucsschool.importer.default_user_import_factory import DefaultUserImportFactory
   from usernames_with_zeros import MyUsernameHandler

   class MyUserImportFactory(DefaultUserImportFactory):
       def make_username_handler(self, max_length):
           return MyUsernameHandler(max_length)


Wird diese Datei nun als
:file:`/usr/lib/python3/dist-packages/my_userimport_factory.py` abgespeichert,
so kann sie in der Konfiguration zur Verwendung als :option:`factory` für die
Importsoftware folgendermaßen aktiviert werden:

.. code-block:: json

   {
       "factory": "my_userimport_factory.MyUserImportFactory"
   }


Der nächste Importvorgang lädt nun anstelle der
:py:class:`DefaultUserImportFactory`` die :py:class:`MyUserImportFactory` und
wenn in der Importsoftware ein Objekt zur Erzeugung von Benutzernamen
angefordert wird, so wird die neue Klasse entscheiden, das eines vom Typ
``MyUsernameHandler`` geliefert wird.

.. _extending-conf-checks:

Prüfung der Konfiguration
=========================

Nach dem Einlesen der Konfigurationsdateien und vor dem eigentlichen Start des
Importvorgangs, laufen Tests, die die Korrektheit und Konsistenz der
Konfiguration prüfen. Der Code für die Tests wird aus Python Modulen im
Verzeichnis :file:`/usr/share/ucs-school-import/checks/` geladen. Damit ein
Modul aus diesem Verzeichnis ausgeführt wird, muss sein Name (ohne :file:`.py`)
in der JSON-Konfigurationsdatei in der Liste unter dem Schlüssel
``configuration_checks`` vorkommen:

.. code-block:: json

   {
       "configuration_checks": ["defaults", "mychecks"]
   }


Das Modul :file:`defaults` führt die Standardprüfungen durch. Es sollte
normalerweise Teil der Liste sein.

Um eigene Prüfungen hinzuzufügen, muss eine Klasse geschrieben werden, die von
:py:class:`ucsschool.importer.utils.configuration_checks.ConfigurationChecks`
abgeleitet wurde. Alle Methoden, deren Namen mit ``test_`` anfangen, werden in
alphanumerischer Reihenfolge ausgeführt. Beispiel, zu speichern in
:file:`/usr/share/ucs-school-import/checks/mychecks.py`:

.. code-block:: python

   from ucsschool.importer.exceptions import InitialisationError
   from ucsschool.importer.utils.configuration_checks import ConfigurationChecks

   class MyConfigurationChecks(ConfigurationChecks):
       def test_nonzero_deactivation_grace(self):
           if self.config.get('deletion_grace_period', {}).get('deactivation', 0) == 0:
               raise InitialisationError('Value of "deletion_grace_period:deactivation" must not be zero.')
