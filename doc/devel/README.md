# UCS@school Knowledge Collection

[TOC]

## DISCLAIMER

1. Die Inhalte in diesem Dokument stellen eine **Best-Effort-Doku** dar, die für den **internen Gebrauch** gedacht ist.
1. Ziel ist der **Knowhow-Transfer** und nicht Optik oder sprachliche Brillianz.
1. Aus den Inhalten ergeben sich **keine Ansprüche**. Jede Schnittstelle, Funktion, Klasse usw. kann morgen ggf. nicht mehr da sein oder anders funktionieren!
1. Die Inhalte erheben **keinen Anspruch auf Vollständigkeit**! Ggf. sind nur Teilaspekte dokumentiert worden.
1. Die Inhalte erheben **keinen Anspruch auf Richtigkeit**! Es wird keine gezielte QA für dieses Dokument gemacht. Wem ein Fehler auffällt, möge ihn bitte korrigieren. Das Dokument ist mit der Zeit ggf. auch out-of-sync mit dem Code.
1. ...

## User objects

**Question:** why does the diagnostic check demands that a OU-spanning teacher who is admin on 1 school also needs the same admin rights on other schools?

```
##################### Start 911_ucsschool_consistency ######################
## Check failed: 911_ucsschool_consistency - UCS@school Consistency Check ##
UCS@school requires its LDAP objects to follow certain rules.
Inconsistencies in these objects can trigger erratic behaviour.

~~~ The following issues concern users ~~~

  uid=a.mueller,cn=lehrer,cn=users,ou=SchuleA,dc=training,dc=ucs
&nbsp;&nbsp;&nbsp;- User does not have UCS@school Role school_admin:school:SchuleB
&nbsp;&nbsp;&nbsp;- Not member of group cn=admins-schuleb,cn=ouadmins,cn=groups,dc=training,dc=ucs

For help please visit https://help.univention.com/t/how-a-ucs-school-user-should-look-like/15630
###################### End 911_ucsschool_consistency #######################
```

**Answer:** At least the LDAP ACLs currently are still using the LDAP object class `ucsschoolAdministrator` to decide if a user is an UCS@school admin. If the user is not member of the admin group of each school, there is an inconsistant state, which might cause other problems.

## Selektive Replikation

Generell wird versucht, auf Schulserver nur das replizieren, was auf ihnen auch benötigt wird. So werden z.B. nur (schulübergreifende) Benutzer auf einen Schulserver repliziert, wenn diese auch Mitglied/Teil der Schule sind.

### Gruppen

Gruppen, die direkt in `cn=groups,ou=SCHULE,dc=example,dc=com` liegen, werden auf alle Schulserver repliziert.
Das hängt damit zusammen, dass die primäre Gruppe der Benutzer in der Standardkonfiguration die Gruppe `Domain Users $OU` ist, und das AD die primäre Gruppe benötigt/kennen muss, um einen Benutzer anlegen zu können. Relevant wird dies bei schulübergreifenden Benutzern:

- Der Benutzer `uid=anton` liegt unterhalb von `ou=schule1` und hat als primäre Gruppe `cn=Domain Users schule1,cn=groups,ou=schule1,dc=example,dc=com`. Zusätzlich ist der Benutzer ein schulübergreifender Benutzer an den Schulen 1 und 2.
- Für den Schulserver1 der Schule1 ist das kein Problem.
- Der Schulserver2 der Schule2 kann alle Benutzer aus dem LDAP des Primary Directory Node replizieren, die auch Mitglied von Schule2 sind (in diesem Fall auch `uid=anton`).
- Der S4-Connector, der auf Schulserver2 aktiv ist, versucht jetzt, `uid=anton` ins lokale AD zu synchronisieren, benötigt dafür aber die primäre Gruppe aus der anderen Schule.

Container unterhalb von `cn=groups,ou=SCHULE,dc=example,dc=com` sowie darin enthaltene Gruppen sollten laut ACL nicht auf "fremde" Schulserver syncronisiert werden. D.h. Klassen und Arbeitsgruppen sind nur auf "ihrem" Schulserver vorhanden.


#### Hat es einen technischen Grund, dass UCS@school User nicht direktes Mitglied von Domain Users sind?
Bei 30k-60k User in einer Gruppe dauert eine einzelne LDAP-Änderung an einer Gruppe (nur *einen* User aufnehmen oder entfernen) gerne mal 5 Sekunden. Dadurch dauert dann z.B. die Aufnahme von 5.000 neuen Usern zum Schuljahreswechsel viel zu lange.

#### Leere Arbeitsgruppen/Klassengruppen finden bzw. löschen (funktioniert erst ab UCS@school 4.4)

Leere Klassen finden:

    univention-ldapsearch -LLL -o ldif-wrap=no '(&(ucsschoolRole=school_class:school:*)(!(uniqueMember=*)))' dn | sed -nre 's/dn: //p'

Leere Klassen alle automatisch löschen lassen:

    univention-ldapsearch -LLL -o ldif-wrap=no '(&(ucsschoolRole=school_class:school:*)(!(uniqueMember=*)))' dn | sed -nre 's/dn: //p' | ldapdelete -D "cn=admin,$(ucr get ldap/base)" -y /etc/ldap.secret -f /dev/stdin

Leere Arbeitsgruppen finden:

    univention-ldapsearch -LLL -o ldif-wrap=no '(&(ucsschoolRole=workgroup:school:*)(!(uniqueMember=*)))' dn | sed -nre 's/dn: //p'

Leere Arbeitsgruppen alle automatisch löschen lassen:

    univention-ldapsearch -LLL -o ldif-wrap=no '(&(ucsschoolRole=workgroup:school:*)(!(uniqueMember=*)))' dn | sed -nre 's/dn: //p' | ldapdelete -D "cn=admin,$(ucr get ldap/base)" -y /etc/ldap.secret -f /dev/stdin



## Squid / Squidguard

Ganz grobes Konzept:
1. Eine Änderung der Internetregeln in der UMC für einen Computerraum/Gruppe erstellt UCR-Variablen auf dem Schulserver.
1. Das Mapping von Gruppen zu Gruppenmitgliedern wird von einem Listenermodul ebenfalls in UCR-Variablen überführt.
1. Die Änderung der UCR-Variablen für squidguard triggert automatisch ein UCR-Modul.
1. Das UCR-Modul schreibt die Daten der UCR-Variablen in Text-Dateien für Squidguard und ruft ein Tool zum Konvertieren der Text-Datei in eine Squidguard-Datenbank auf.
1. Abschließend triggert das UCR-Modul einen Reload über einen speziellen Daemon, der dafür sorgt, dass der Squid (**Achtung**: squid, nicht squidguard! squidguard ist ein Helperprozess von squid) max. 1x pro 15 Sekunden neugestartet wird.

## Meta-Netlogon-Skript

An den Usern wird von UCS@school automatisch im Sambaattribut `sambaNetlogonPath` ein Meta-Netlogon-Skript eingetragen, welches dann auf dem Windows-Client ausgeführt wird und dann mindestens ein anderes Netlogon-Skript ausführt.
Welche Skripte ausgeführt werden, kann über `ucsschool/netlogon/.*` konfiguriert werden. Im Standardfall wird ein userspezifisches Logonskript ausführt, welches für das Laufwerksmapping zuständig ist:

    ucsschool/netlogon/ucs-school-netlogon-user-logonscripts/script: user\%USERNAME%.vbs

Kunden und Univention-Komponenten können auch eigene Skripte dort eintragen:

    ucsschool/netlogon/EINDEUTIGERNAME/script: pfad\zum\Skript\relativ\zur\netlogon\share\wurzel\myscript.bat

Das Meta-Netlogon-Skript ist für alle User identisch. D.h. man muss in den konfigurierten Skripten entsprechend reagieren, falls sie nicht für alle User ausgeführt werden sollen.

## Netlogon-Skripte: Laufwerksmapping auf Windows-Clients

An welcher Stelle werden die automatischen Laufwerksmappings für Windowsclients (K: für Klassenfreigaben, M: für Marktplatz) definiert?

Das passiert über das Paket `ucs-school-netlogon-user-logonscripts`, was ein Listener-Modul und einen Daemon mitbringt, der für alle User userspezifische Netlogon-Skripte erzeugt. Siehe dazu die diversen UCR-Variablen `ucsschool/userlogon/.*`

Für UCS@school ist vorgesehen, dass jeder Schüler nur einer Klasse zugeordnet ist. Die Klassenfreigabe dieser Klasse wird im userspezifischen Netlogon-Skript automatisch auf einen Laufwerksbuchstaben gemappt, der über die UCR-Variable
`ucsschool/userlogon/classshareletter` definiert ist.

Freigaben, die allen Usern zugeordnet werden sollen, wie z.B. dem Marktplatz, können ebenfalls über UCR-Variablen konfiguriert werden. Der Marktplatz wird über folgende UCR-Settings verknüpft:

    ucsschool/userlogon/commonshares/letter/Unterrichtsmaterial: U
    ucsschool/userlogon/commonshares/server/Unterrichtsmaterial: replica213
    ucsschool/userlogon/commonshares/letter/Marktplatz: M
    ucsschool/userlogon/commonshares/server/Marktplatz: replica213
    ucsschool/userlogon/commonshares: Marktplatz,Unterrichtsmaterial

"Marktplatz" und "Unterrichtsmaterial" sind hier jeweils die Namen der Freigabeen. `ucsschool/userlogon/commonshares` ist eine kommaseparierte Liste aller Freigaben, die für alle User verknüpft werden sollen.

## Samba

### LDB-Modul

Für UCS@school haben wir ein LDB-Modul für Samba entwickelt, welches dafür sorgt, dass a) beim Joinvorgang eines Windows-Clients das entsprechende Rechnerobjekt vom UDM angelegt wird (nicht vom AD selbst!) und b) dieses Rechnerobjekt unterhalb der "richtigen" OU und *nicht* im zentralen Container angelegt wird.
Das LDB-Modul wird auf folgenden Systemen vom Metapaket installiert und aktiviert:

- Multiserver-Umgebung:
  - Schulserver (edukativ UND Verwaltung)
- Singleserver-Umgebung:
  - Primary Directory Node
  - Backup Directory Node

Auf allen anderen Rollen ist das Modul nicht aktiv und joinende Windowsclients legen dann Rechnerobjekte direkt in den zentralen Containern und nicht unterhalb der Schul-OUs an.

## LDAP-ACLs

### Soll-Status prüfen

In ucs-test-ucsschool gibt es das Skript `75_ldap_acls_specific_tests`, welches Tests enthält, die den Soll-Zustand überprüfen: kann der Schuladmin von Schule A nur die Schüler/Lehrer/Staff-Passwörter seiner Schule zurücksetzen, aber nicht die Passwörter von Schuladmins oder anderen Schule usw. Das Skript wird/soll nach und nach erweitert werden. Es erstellt automatisch 3 Schulen mit allen (schulübergreifenden) Benutzertypen, allen Rechnertypen, Klassen, Arbeitsgruppen und Räumen.

### Auswirkungen von ACL-Änderungen überprüfen

In ucs-test-ucsschool gibt es außerdem das Skript `78_ldap_acls_dump`. Es erstellt automatisch 3 Schulen mit allen (schulübergreifenden) Benutzertypen, allen Rechnertypen, Klassen, Arbeitsgruppen und Räumen. Anschließend wird für alle 29 Objekttypen (cn=admin, Primary Directory Node, Backup Directory Node, ..., Lehrer, Schüler, Mitarbeiter, Schuladmins, Windows-Clients, SchulDC) eine via `slapacl` eine Abfrage für alle Objekte im LDAP und in den drei TestOUs gemacht und die Zugriffsberechtigungen für die Attribute in jeweils eine Datei geschrieben (`/var/log/univention/78_ldap_acls_dump.TIMESTAMP/dn??.ldif`). In dem Verzeichnis liegt auch eine Datei `dn.txt` wo das Mapping der zwischen DN und Datei wieder aufgelöst wird.

#### Welchen Mehrwert hat man dadurch?
Man kann den Dump der Zugriffsberechtigungen jetzt **VOR** und **NACH** einer LDAP-ACL-Änderung erstellen und sich die Änderungen zwischen den beiden Dumps über das Skript `78_ldap_acls_dump.diff` (auch in ucs-test-ucsschool) anzeigen lassen. Dabei wird für jede Datei, die verglichen wird, ein `less` gestartet.

    # cd /usr/share/ucs-test/90_ucsschool/
	# ./78_ldap_acls_dump -vf
	<LDAP-ACL-Änderungen durchführen und slapd neustarten>
	# ./78_ldap_acls_dump -vf
    # ./78_ldap_acls_dump.diff /var/log/univention/78_ldap_acls_dump.1558281264/ /var/log/univention/78_ldap_acls_dump.1558282573/

**Hinweis:** Für `78_ldap_acls_dump.diff` werden die Tools `HLdiff` und `diff-ldif` aus dem Toolshed benötigt. Einfach vorher nach `/usr/bin/` der Testinstanz kopieren.

**WARNUNG: `slapacl` scheint nicht immer den korrekten Output zu liefern! Im Test hat sich gezeigt, dass `slapacl` `read`-Permissions vermeldet hat, der User aber trotzdem ein `write` machen konnte!**

Die Ausgabe des Diff-Tools sieht wie folgt aus:

    /var/log/univention/78_ldap_acls_dump.1558281264/dn20.ldif
	/var/log/univention/78_ldap_acls_dump.1558282573/dn20.ldif

     dn: uid=staffA,cn=mitarbeiter,cn=users,ou=schoolA,dc=nstx,dc=local
    +userPassword: =wrscxd
    -userPassword: =rscxd
     univentionObjectType: =rscxd
     uidNumber: =rscxd
     uid: =rscxd
     ucsschoolSchool: =rscxd
     ucsschoolRole: =rscxd
     structuralObjectClass: =rscxd
     sn: =rscxd
     sambaSID: =rscxd
    +sambaPwdLastSet: =wrscxd
    -sambaPwdLastSet: =rscxd
     sambaPrimaryGroupSID: =rscxd
    +sambaPasswordHistory: =wrscxd
    -sambaPasswordHistory: =rscxd
    +sambaNTPassword: =wrscxd
    -sambaNTPassword: =rscxd
     sambaBadPasswordTime: =rscxd
    +sambaBadPasswordCount: =wrscxd
    -sambaBadPasswordCount: =rscxd
    +sambaAcctFlags: =wrscxd
    -sambaAcctFlags: =rscxd
     objectClass: =rscxd
     modifyTimestamp: =rscxd
     modifiersName: =rscxd
     memberOf: =rscxd
    [...]

## RADIUS

`ucs-school-radius-802.1x` erweitert das Paket `univention-radius` (aus UCS) um die Möglichkeit, über UCS@school-Internetregeln den Zugriff auf das WLAN zu steuern. Da die UCS@school-Internetregeln in UCR gespeichert werden, funktioniert das UCS@school-Paket nur sinnvoll auf dem Schulserver, wo die Regeln auch gepflegt werden. Man könnte es zwar auf einem zentralen System installieren, fällt dann mangels UCR-Daten aber auf den Funktionsumfang von `univention-radius` zurück.

## /etc/ucsschool/

### /etc/ucsschool/logging.yaml

Logging settings for CLI output format, file output format and colors (`utils.CMDLINE_LOG_FORMATS`, `utils.FILE_LOG_FORMATS`, `utils.LOG_DATETIME_FORMAT`, `utils.LOG_COLORS`).

Used by `utils.get_stream_handler()` and `utils.get_file_handler()`.

Use `models.utils._write_logging_config()` to update it.

### /etc/ucsschool/demoschool.secret

The password of the demoschool users is stored in this file.

## /etc/ucsschool-import/

* `django_key.secret`: _A secret key for a particular Django installation. This is used to provide cryptographic signing, and should be set to a unique, unpredictable value._: https://docs.djangoproject.com/en/1.10/ref/settings/#std:setting-SECRET_KEY
* `ldap_unprivileged.secret`: userDN and password used to open an unprivileged read-write LDAP connection with `ucsschool.importer.utils.ldap_connection.get_unprivileged_connection()`
* `postgres.secret`: password of user `importhttpapi` to access the PostgreSQL database `importhttpapi`
* `rabbitmq.secret`: password Celery uses to access rabbitMQ
* `settings.py`: Django configuration file for HTTP-API for CSV import

## UCS@school-Import-Zählerobjekte

Um fehlende Zählerobjekte für Benutzernamen-Präfixe zu erzeugen, kann folgender Schnippsel verwendet werden:

    python3 -c "from ucsschool.importer.utils.username_handler import LdapStorageBackend; b = LdapStorageBackend('usernames'); b.create('${USERNAMEPREFIX}', ${NEXTNUMBER})"

# Klassenarbeitsmodus / Exam-Mode

#### Kann man, nachdem man eine Klasenarbeit erfolgreich beendet hat, sofort eine neue starten? Mit der gleichen Klasse?
Ja, das sollte gehen. (Wir gehen mal davon aus, dass sich die Klassenarbeit ordentlich wieder beendet hat. Falls da noch Überbleibsel in der Config übrig geblieben sind￼, kann es natürlich zu Folgefehlern kommen).

#### Kann das Starten einer Klassenarbeit scheitern, wenn die Replikation zwischen Primary Directory Node und Replica Directory Node zu träge ist?
Ganz klares `Jein`. Das Exam-Modul auf dem Replica Directory Node wendet sich an den Primary Directory Node, um dort die Exam-User anzulegen bzw. später wieder zu löschen. Nach dem Anlegen der Exam-User auf dem Primary Directory Node wartet das Exam-Modul auf dem Replica Directory Node bis zu 30 Minuten, dass die Exam-User auch auf den Replica Directory Node repliziert wurden. Wenn die Replikation so langsam ist, dass der 30min-Timeout gerissen wird, dann lautet die Antwort eindeutig `Ja`, aber dann kann man den Exam-Modus auch nicht mehr kurzfristig sinnvoll einsetzen.

#### Was macht einen ExamUser aus?
* Das Objekt liegt im LDAP unter der primären OU des originalen Nutzers
* Der ExamUser befindet sich nur in den Schulen, in denen er aktuell eine Klassenarbeit schreibt
* Der ExamUser hat die Rolle exam_user:school:$OU für jede $OU in der er aktuell eine Klassenarbeit schreibt.

# Import
## UMC-Modul "Benutzer-Import" / HTTP-API "Newton"
*Aktuell noch nicht im Handbuch:* Beim Import über das UMC-Modul "Benutzer-Import" bzw. direkt über die Newton-HTTP-API (Massenimport via CSV-Datei) ist es möglich, additiv zur vorhandenen Konfiguration eine OU-spezifische Konfiguration hinzuzuladen. Diese muss pro OU in der Datei `/var/lib/ucs-school-import/configs/$OU.json` abgelegt werden.


## Schulübergreifende Benutzerkonten

### Darf ein schulübergreifender Benutzer eigentlich in beiden "Domain Users $OU"-Gruppen sein? Oder muss er?
- Er muss in allen `Domain Users $OU`-Gruppen enthalten sein.
- Er muss für alle OUs Einträge in den Attributen `ucsschoolSchool` und `ucsschoolRole` haben.
- Er muss z.B. als Schüler in beiden Gruppen `schueler-$OU` enthalten sein.


