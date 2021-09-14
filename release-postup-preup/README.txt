Warum?

Wir brauchen einige UCS Pakete im UCS@school repo für ein sauberes Update von UCS 4.4 auf UCS 5.0.

Idee:

Wir stecken diese Pakete (https://forge.univention.org/bugzilla/show_bug.cgi?id=53782#c2) in das UCS@school repo.

Problem:

Das UCS Update Pinned (apt pinning) das UCS Repo, so dass Pakete nur von dort installiert werden, auch wenn
es in anderen Repo's neuere Versionen gibt.

Lösung:

Das UCS@school repo wird auch gepinned. Dafür brauchen wir Release Dateien und post/preup für die Konfiguration des pinnings.

Release (Dateien) / preup und postup
------------------------------------

1. auf omar das UCS@school repo aktualisieren
@omar /var/univention/buildsystem2/mirror/appcenter.test/tools/sync.sh 5.0

2. Release Dateien erstellen und signieren (und pre/postup)
@here bash -x update-release-pup.sh

3a. Release Dateien auf das Test-AppCenter kopieren
@here        scp -r amd64/ i386/ all/ selfservice:/tmp
@selfservice mv amd64/Release* /var/lib/univention-appcenter-selfservice/appcenter/univention-repository/5.0/maintained/component/ucsschool_20201208103021/amd64/
@selfservice mv all/Release* /var/lib/univention-appcenter-selfservice/appcenter/univention-repository/5.0/maintained/component/ucsschool_20201208103021/all/
@selfservice mv i386/Release* /var/lib/univention-appcenter-selfservice/appcenter/univention-repository/5.0/maintained/component/ucsschool_20201208103021/i386/

3b. post/preup auf Test-AppCenter kopieren
@here        scp postup.sh* selfservice:/tmp/
@here        scp preup.sh* selfservice:/tmp/
@selfservice mv postup.sh* preup.sh* /var/lib/univention-appcenter-selfservice/appcenter/univention-repository/5.0/maintained/component/ucsschool_20201208103021/all/

4. Sync nach Test-AppCenter anstoßen
@selfservice univention-app selfservice-sync "5.0/ucsschool=5.0 b3"
