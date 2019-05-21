# UCS@school Knowledge Collection

## DISCLAIMER

1. Die Inhalte in diesem Dokument stellen eine **Best-Effort-Doku** dar, die für den **internen Gebrauch** gedacht ist.
1. Ziel ist der **Knowhow-Transfer** und nicht Optik oder sprachliche Brillianz.
1. Aus den Inhalten ergeben sich **keine Ansprüche**. Jede Schnittstelle, Funktion, Klasse usw. kann morgen ggf. nicht mehr da sein oder anders funktionieren!
1. Die Inhalte erheben **keinen Anspruch auf Vollständigkeit**! Ggf. sind nur Teilaspekte dokumentiert worden.
1. Die Inhalte erheben **keinen Anspruch auf Richtigkeit**! Es wird keine gezielte QA für dieses Dokument gemacht. Wem ein Fehler auffällt, möge ihn bitte korrigieren. Das Dokument ist mit der Zeit ggf. auch out-of-sync mit dem Code.
1. ...

## Selektive Replikation

Generell wird versucht, auf Schulserver nur das replizieren, was auf ihnen auch benötigt wird. So werden z.B. nur (schulübergreifende) Benutzer auf einen Schulserver repliziert, wenn diese auch Mitglied/Teil der Schule sind.

### Gruppen

Gruppen, die direkt in `cn=groups,ou=SCHULE,dc=example,dc=com` liegen, werden auf alle Schulserver repliziert.
Das hängt damit zusammen, dass die primäre Gruppe der Benutzer in der Standardkonfiguration die Gruppe `Domain Users $OU` ist, und das AD die primäre Gruppe benötigt/kennen muss, um einen Benutzer anlegen zu können. Relevant wird dies bei schulübergreifenden Benutzern:

- Der Benutzer `uid=anton` liegt unterhalb von `ou=schule1` und hat als primäre Gruppe `cn=Domain Users schule1,cn=groups,ou=schule1,dc=example,dc=com`. Zusätzlich ist der Benutzer ein schulübergreifender Benutzer an den Schulen 1 und 2.
- Für den Schulserver1 der Schule1 ist das kein Problem.
- Der Schulserver2 der Schule2 kann alle Benutzer aus dem LDAP des Masters replizieren, die auch Mitglied von Schule2 sind (in diesem Fall auch `uid=anton`).
- Der S4-Connector, der auf Schulserver2 aktiv ist, versucht jetzt, `uid=anton` ins lokale AD zu synchronisieren, benötigt dafür aber die primäre Gruppe aus der anderen Schule.

Container unterhalb von `cn=groups,ou=SCHULE,dc=example,dc=com` sowie darin enthaltene Gruppen sollten laut ACL nicht auf "fremde" Schulserver syncronisiert werden. D.h. Klassen und Arbeitsgruppen sind nur auf "ihrem" Schulserver vorhanden.


## Squid / Squidguard

Ganz grobes Konzept:
1. Eine Änderung der Internetregeln in der UMC für einen Computerraum/Gruppe erstellt UCR-Variablen auf dem Schulserver.
1. Das Mapping von Gruppen zu Gruppenmitgliedern wird von einem Listenermodul ebenfalls in UCR-Variablen überführt.
1. Die Änderung der UCR-Variablen für squidguard triggert automatisch ein UCR-Modul.
1. Das UCR-Modul schreibt die Daten der UCR-Variablen in Text-Dateien für Squidguard und ruft ein Tool zum Konvertieren der Text-Datei in eine Squidguard-Datenbank auf.
1. Abschließend triggert das UCR-Modul einen Reload über einen speziellen Daemon, der dafür sorgt, dass der Squid (**Achtung**: squid, nicht squidguard! squidguard ist ein Helperprozess von squid) max. 1x pro 15 Sekunden neugestartet wird.


## Samba

### LDB-Modul

Für UCS@school haben wir ein LDB-Modul für Samba entwickelt, welches dafür sorgt, dass a) beim Joinvorgang eines Windows-Clients das entsprechende Rechnerobjekt vom UDM angelegt wird (nicht vom AD selbst!) und b) dieses Rechnerobjekt unterhalb der "richtigen" OU und *nicht* im zentralen Container angelegt wird.
Das LDB-Modul wird auf folgenden Systemen vom Metapaket installiert und aktiviert:

- Multiserver-Umgebung:
  - Schulserver (edukativ UND Verwaltung)
- Singleserver-Umgebung:
  - DC Master
  - DC Backup

Auf allen anderen Rollen ist das Modul nicht aktiv und joinende Windowsclients legen dann Rechnerobjekte direkt in den zentralen Containern und nicht unterhalb der Schul-OUs an.
