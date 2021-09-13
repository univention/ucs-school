#!/bin/bash

set -e
set -x

exe="${0##*/}"

component="ucsschool_20201208103021"
version="5.0/ucsschool=5.0 b3"

# priv key for selfservice
key="$HOME/ec2/keys/tech.pem"
# repo path on selfservice
repo="/var/lib/univention-appcenter-selfservice/appcenter/univention-repository/5.0/maintained/component/$component"

usage () {
	cat <<__TEXT__
Usage: $exe release|postup|preup
  updates release or postup or preup files for ucs@school ($version component:$component)
Examples:
  $exe release
  $exe preup
  $exe postup
__TEXT__
	exit "${1:-2}"
}

sync_app () {
	ssh -i "$key" root@selfservice "univention-app selfservice-sync '$version'"
}

update_release () {
	local tmp
	tmp="$(ssh omar mktemp -d)"
	for arch in amd64 all i386; do
		[ ! -d "$arch" ] && mkdir "$arch"
		# create release file
		ssh -i "$key" root@selfservice "apt-ftparchive release \
			-o APT::FTPArchive::Release::Origin='Univention' \
			-o APT::FTPArchive::Release::Label='ucs@school' \
			-o APT::FTPArchive::Release::Codename='$component/$arch' \
			-o APT::FTPArchive::Release::Version='$component' \
			-o APT::FTPArchive::Release::Suite='apt'  $repo/$arch > $repo/$arch/Release"
		# copy to omar (and here) and sign it
		scp -i "$key" root@selfservice:"$repo/$arch/Release" "$arch/"
		# shellcheck disable=SC2029
		ssh omar "mkdir -p $tmp/$arch"
		scp "$arch/Release" omar:"$tmp/$arch"
		# shellcheck disable=SC2029
		ssh omar "repo-ng-sign-release-file -i $tmp/$arch/Release -o $tmp/$arch/Release.gpg -k 8321745BB32A82C75BBD4BC2D293E501A055F562 -p /etc/archive-keys/ucs5.0.txt"
		# copy pgp file to selfservive (and here)
		scp omar:"$tmp/$arch/Release.gpg" "$arch/"
		scp -i "$key" "$arch/Release.gpg" root@selfservice:"$repo/$arch/Release.gpg"
		# shellcheck disable=SC2029
		ssh omar "rm $tmp/$arch/Release $tmp/$arch/Release.gpg; rmdir $tmp/$arch"
	done
	# shellcheck disable=SC2029
	ssh omar "rmdir $tmp"
}

update_updater_script () {
	local action tmp
	action=$1
	tmp="$(ssh omar mktemp -d)"
	# copy to omar and sign
	scp "./$action.sh" omar:"$tmp"
	# shellcheck disable=SC2029
	ssh omar "repo-ng-sign-release-file -i '$tmp/$action.sh' -o '$tmp/$action.sh.gpg' -k 8321745BB32A82C75BBD4BC2D293E501A055F562 -p /etc/archive-keys/ucs5.0.txt"
	# copy to selfservice
	scp omar:"$tmp/$action.sh.gpg" .
	scp -i "$key" "./$action.sh" "./$action.sh.gpg" root@selfservice:"$repo/all"
	# shellcheck disable=SC2029
	ssh omar "rm $tmp/$action.sh.gpg $tmp/$action.sh; rmdir $tmp"
}

# main
[ -n "${1:-}" ] || usage 2 >&2
case "$1" in
	release)
		update_release
		sync_app
		;;
	postup)
		update_updater_script "postup"
		sync_app
		;;
	preup)
		update_updater_script "preup"
		sync_app
		;;
	*)
		usage 2 >&2
		;;
esac

exit 0
