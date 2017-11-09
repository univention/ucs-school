# HTTP-API

# Installation

## Prerelease

	ucr set repository/online/server=http://updates-test.software-univention.de/ \
	repository/app_center/server=appcenter-test.software-univention.de \
	appcenter/index/verify=no \
	update/secure_apt=no \
	repository/online/unmaintained=yes

	univention-upgrade --ignoreterm --ignoressh

	univention-install univention-appcenter-dev
	univention-app dev-use-test-appcenter

	univention-install ucs-school-import-http-api

	# should also install "ucs-school-umc-import" as it's in "recommends"

	# update to latest version
	wget -r -np -A "ucs-school-import*.deb,ucs-school-umc-import*.deb" "http://192.168.0.10/build2/ucs_4.2-0-ucs-school-4.2/all/"
	dpkg -i 192.168.0.10/build2/ucs_4.2-0-ucs-school-4.2/all/ucs-school-*.deb
	systemctl restart celery-worker-ucsschool-import.service
	systemctl restart gunicorn.service
	systemctl restart univention-management-console-server.service

$BROWSER: https://10.200.3.90/api/v1/ --> exists? ok :)

## Test data

To create test data run:

	/usr/share/ucs-school-import/scripts/ucs-school-testuser-import \
	--httpapi \
	--teachers 10 \
	--classes 3 \
	--create-email-addresses \
	--verbose \
	SchuleEinz

It will create a file with a name similar to   `test_users_2017-09-07_16:09:46.csv`. You can configure a filename with `--csvfile`.

That file can be used as input data for the HTTP-API or on the command line with:

	/usr/share/ucs-school-import/scripts/ucs-school-user-import \
	--conffile /usr/share/ucs-school-import/configs/user_import_http-api.json \
	--user_role student \
	--school SchuleEinz \
	--infile test_users_2017-09-07_16:09:46.csv \
	--sourceUID SchuleEinz-student \
	--verbose

## Configuration

To use the produced CSV with the HTTP-API service, the configuration file must be used:

	cp /usr/share/ucs-school-import/configs/user_import_http-api.json /var/lib/ucs-school-import/configs/user_import.json
	# or to /var/lib/ucs-school-import/configs/<OU>.json

## Use UMC module for import

* $BROWSER: login as 'Administrator'
* open 'schoolimport' module
	* → "The permissions to perform a user import are not sufficient enough."

### create a UMC policy

	eval "$(ucr shell)"
	OU=<your ou>
	udm policies/umc create \
	--set name=umc-schoolimport-all \
	--position "cn=UMC,cn=policies,$ldap_base" \
	--append allow="cn=schoolimport-all,cn=operations,cn=UMC,cn=univention,$ldap_base"
	udm groups/group modify \
	--dn "cn=$OU-import-all,cn=groups,ou=$OU,$ldap_base" \
	--policy-reference "cn=umc-schoolimport-all,cn=UMC,cn=policies,$ldap_base"

### add user to group with required permissions on school and user role:

	# create school staff user 'uid=astaff' in UMC school wizard...

	udm groups/group modify \
	--dn cn="$OU-import-all,cn=groups,ou=$OU,$ldap_base" \
	--append users="uid=astaff,cn=mitarbeiter,cn=users,ou=$OU,$ldap_base"

### workaround group missing option "ucsschoolImportGroup"

Until http://forge.univention.org/bugzilla/show_bug.cgi?id=45023#c8 is fixed:

	udm groups/group modify \
	--dn cn=$OU-import-all,cn=groups,ou=$OU,$ldap_base \
	--append-option ucsschoolImportGroup \
	--append ucsschoolImportSchool=$OU \
	--append ucsschoolImportRole=staff \
	--append ucsschoolImportRole=student \
	--append ucsschoolImportRole=teacher \
	--append ucsschoolImportRole=teacher_and_staff

## success

$BROWSER
* login as 'astaff'
* open 'schoolimport' module
	* $OU + "Staff"
	* → UserImportJob #1 (dryrun) ended successfully.
	* Press "Start Import"
		* Overview User Imports
		* → "A new import of Staff users at school $OU has been started. The import has the ID 2."
		* Liste leer...
			* Switch to german language and all is fine :)
			* → reopen #45023
		* Very nice!



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
