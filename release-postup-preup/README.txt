Warum?

Wir brauchen einige UCS Pakete im UCS@school repo für ein sauberes Update von UCS 4.4 auf UCS 5.0.

Idee:

Wir stecken diese Pakete (https://forge.univention.org/bugzilla/show_bug.cgi?id=53782#c2) in das UCS@school repo.

Problem:

Das UCS Update Pinned (apt pinning) das UCS Repo, so dass Pakete nur von dort installiert werden, auch wenn
es in anderen Repo's neuere Versionen gibt.

Lösung:

Das UCS@school repo wird auch gepinned. Dafür brauchen wir Release Dateien und post/preup für die Konfiguration des pinnings.

Release (Dateien) aktualisieren:
--------------------------------

Release Dateien müssen immer aktualisiert werden, wenn Pakete in der App geändert werden (mod, add, rm).
Benötigt wird der (ssh) tech key ($HOME/ec2/keys/tech.pem):

-> cd ~/git/ucsschool/release-postup-preup
-> ./update-release-preup-postup.sh release

Danach ggf git commit.

preup/postup aktualisieren:
---------------------------

Nur bei Änderungen an den Dateien (momentan wird im preup das pinning für
UCS@school aktiviert und im postup wieder deaktiviert).

-> cd ~/git/ucsschool/release-postup-preup
-> ./update-release-preup-postup.sh postup
oder
-> ./update-release-preup-postup.sh preup

Danach ggf git commit.
