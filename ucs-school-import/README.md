# HTTP-API

# Installation

*TODO*

## Test data

To create test data run:

	/usr/share/ucs-school-import/scripts/ucs-school-testuser-import \
	--httpapi \
	--teachers 10 \
	--classes 3 \
	--create-email-addresses \
	--verbose \
	SchuleEinz

It will create a file with a name similar to   `test_users_2017-09-07_16:09:46.csv`.

That file can be used as input data for the HTTP-API or on the command line with:

	/usr/share/ucs-school-import/scripts/ucs-school-user-import \
	--conffile /usr/share/ucs-school-import/configs/user_import_http-api.json \
	--user_role student \
	--school SchuleEinz \
	--infile test_users_2017-09-07_16:09:46.csv \
	--sourceUID SchuleEinz-student \
	--verbose


# nachfolgend evtl. veraltete Infos

**TODO: überprüfe Aktualität**
---

# Ziel:

Die in diesem Paket enthaltenen Skripte dienen der spezifischen Administration
einer UCS@school-Domäne, genauer dem import von Benutzern (Schüler/Lehrer),
Netzwerken und Rechnern.

# Skripte:

Alle Skripte liegen unter /usr/share/ucs-school-import/scripts. Ausgangspunkt ist das Skript 
"ucs-school-import", alle anderen Skripte sind nur symbolische links auf diese Datei.

Alle Skripte legen automatisch eine Schule (also deren ou-Baum im LDAP) an, sobald
ein Element in dieser Schule angelegt werden soll (entspricht der Funktionalität von
create_ou).

## Schule anlegen:
Um eine Schule anzulegen kann das Skript "create_ou" aufgerufen werden, als Option 
wird dabei die Schulnummer übergeben (z.B. "create_ou 308"). Das sollte besonders
_vor_ der Installation eines Schulservers erfolgen, ansonsten wird dieser an falscher
Stelle im LDAP angelegt.

## Benutzer importieren:
Das Importieren von neuen oder geänderten Benutzern erfolgt durch den Aufruf des 
Skriptes "ucs-school-import" oder "import_user" mit dem Dateinamen als Option.

## Netzwerk importieren:
Netzwerke können in einer Datei zeilenweise einer Schule zugeordnet werden, Trennzeichen
ist ein Semikolon:

<Schul-Nr>;<Netzwerk>

z.B.:

308;10.101.69.0

Das Netzwerk wird mit Maske 255.255.255.0 angelegt, dementsprechend sollte der Eintrag auf
".0" enden. Mittels dieser Netzwerke werden entpsrechende DNS und DHCP-Zonen voreingestellt.
Der Import erfolgt dann durch import_networks mit dem Dateinamen als Option.
Per Default wird ein Bereich von IPs .10 bis .250 für die freie vergabe (siehe unten) 
voreingestellt. 

## Computer importieren
Computer werden in einer Datei zeilenweise mit Tab als Trennzeichen definiert und über 
import_computer mit dem Dateinamen als Option angelegt. Format der Datei ist:

<computertyp>;<computername>;<MAC>;<Schul-Nr>;<IP oder Netzwerk>

z.B.:

windows;winrechner;00:11:22:33:44:56;10;10.0.101.0

Wird der Rechner einem bereits angelegtem Netzwerk zugeordnet (IP endet auf .0), wird die 
IP automatisch vergeben, der Computer bekommt einen DHCP und einen DNS-Eintrag.
