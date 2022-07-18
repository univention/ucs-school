#!/bin/bash

phase="$1"
version="$2"
school_version="ucsschool_20201208103021"

if [ "x$phase" = "xpost" ] && [ "x$version" = "x5.0-0" ]; then
	[ -f /etc/apt/preferences.d/99ucsschool500.pref ] ||
		cat >/etc/apt/preferences.d/99ucsschool500.pref <<__PREF__
Package: *
Pin: release v=$school_version,o=Univention,n=$school_version/all,l=Univention
Pin-Priority: 1002
__PREF__

fi

exit 0
