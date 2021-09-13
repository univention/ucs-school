version="ucsschool_20201208103021"
repo="/var/univention/buildsystem2/mirror/appcenter.test/univention-repository/5.0/maintained/component/$version"

for arch in amd64 all i386; do
	ssh omar "apt-ftparchive release \
		-o APT::FTPArchive::Release::Origin='Univention' \
		-o APT::FTPArchive::Release::Label='ucs@school' \
		-o APT::FTPArchive::Release::Codename='$version/$arch' \
		-o APT::FTPArchive::Release::Version='$version' \
		-o APT::FTPArchive::Release::Suite='apt'  $repo/$arch > $repo/$arch/Release"
	ssh omar "repo-ng-sign-release-file -i $repo/$arch/Release -o $repo/$arch/Release.gpg -k 8321745BB32A82C75BBD4BC2D293E501A055F562 -p /etc/archive-keys/ucs5.0.txt"
	mkdir -p "$arch"
	scp omar:$repo/$arch/Release* "$arch/"
done

tmp="$(ssh omar mktemp -d)"
scp preup.sh omar:"$tmp"
scp postup.sh omar:"$tmp"
ssh omar "repo-ng-sign-release-file -i '$tmp/preup.sh' -o '$tmp/preup.sh.gpg' -k 8321745BB32A82C75BBD4BC2D293E501A055F562 -p /etc/archive-keys/ucs5.0.txt"
ssh omar "repo-ng-sign-release-file -i '$tmp/postup.sh' -o '$tmp/postup.sh.gpg' -k 8321745BB32A82C75BBD4BC2D293E501A055F562 -p /etc/archive-keys/ucs5.0.txt"
scp omar:"$tmp/postup.sh*" .
scp omar:"$tmp/preup.sh*" .
