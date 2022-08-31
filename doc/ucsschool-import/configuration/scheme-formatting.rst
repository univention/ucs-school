.. _configuration-scheme-formatting:

Formatierungsschema
===================

Es kann wünschenswert, oder wie im Fall von Benutzername und E-Mailadresse
notwendig, sein, Attribute aus den Werten anderer Attribute zu erzeugen. Zum
Beispiel speichern und exportieren Schulverwaltungssoftwares häufig keine
Benutzernamen und E-Mailadressen, die zur eingesetzten Infrastruktur passen.

Aus diesem Grund unterstützt die Importsoftware die Erzeugung von Attributen mit
Hilfe von konfigurierbaren Schemata. Das Format ist das gleiche wie das bei den
:ref:`users-templates` in :cite:t:`ucs-manual` eingesetzte. Es existieren
dedizierte Konfigurationsschlüssel für die Attribute ``email``, ``record_uid``
und ``username``. Darüber hinaus können Schemata für beliebige |UCSUDM|
Attribute (mit dem Namen des Attributs als Schlüssel) hinterlegt werden.

Im folgenden Beispiel werden die E-Mail-Adresse aus Vor- und Nachname berechnet
und die ``email`` wird als ``record_uid`` gesetzt:

.. code-block:: json

   {
       "scheme": {
           "email": "<firstname>[0].<lastname>@<maildomain>",
           "record_uid": "<email>"
       }
   }


Die Verwendung von selbst referenzierenden Attributen, z.B. zur Voranstellung
von Ländervorwahlen ist nicht möglich. Um dies zu erreichen, sowie wenn
Attribute in modifizierter Form für die Erzeugung weiterer Attribute verwendet
werden sollen (z.B. nur der erste Teil eines Doppelnamens für eine
E-Mailadresse), können Format-Hooks geschrieben werden. Ihre Erstellung und
Verwendung wird in :ref:`extending-hooks-format-hooks` beschrieben.

Zur Illustration wird gezeigt, wie aus den oben angeführten Schemata für
``email`` und ``record_uid`` der entsprechende Wert berechnet wird, wenn
folgende Beispiel CSV-Datei als Eingabe verwendet wird:

.. code-block::

   "Schulen","Vorname","Nachname","Klassen","Telefonnumer"
   "schule1","Bea","Schmidt","schule1-1A","0421-1234567890"


.. code-block::

   2020-07-09 15:28:34 INFO  user_import.create_and_modify_users:141  ------ Creating / modifying users... ------
   [..]
   2020-07-09 15:28:34 INFO  user_import.create_and_modify_users:186  Adding ImportStudent(name='B.Schmidt',
   school='schule1', dn='uid=B.Schmidt,cn=schueler,cn=users,ou=schule1,dc=uni,dc=dtr', old_dn=None) (source_uid:NewDB
   record_uid:b.schmidt@schule.local) attributes={'$dn$': 'uid=B.Schmidt,cn=schueler,cn=users,ou=schule1,dc=uni,dc=dtr',
   'display_name': 'Bea Schmidt', ``'record_uid'``: u'b.schmidt@schule.local', 'firstname': 'Bea',
   'lastname': 'Schmidt', 'type_name': 'Student', 'school': 'schule1', ``'name'``: 'B.Schmidt',
   'disabled': '0', 'email': u'b.schmidt@schule.local', 'birthday': None, 'type': 'importStudent', 'schools': ['schule1'],
   'password': 'xxxxxxxxxx', 'source_uid': u'NewDB', ``'school_classes'``: {'schule1': ['schule1-2B']},
               'objectType': 'users/user'} ``udm_properties</property>={u@@property@@>'phone'``: [u'0421-1234567890'],
   'overridePWHistory': '1', 'overridePWLength': '1'}...


