#!/bin/bash

phase="$1"
version="$2"
school_version="ucsschool_20201208103021"
UPDATER_LOG="/var/log/univention/updater.log"
VERSION="50"

# shellcheck source=/dev/null
. /usr/share/univention-lib/ucr.sh || exit $?

ignore_check () {
	local var="$1"
	is_ucr_true "$var" ||
		return 1
	echo -n "Ignoring test as requested by $var " 1>&2
	return 0
}

update_check_python_ucsschool_import_hook_compatibility() {
	local var="update$VERSION/ignore-python3-compatiblity-ucsschool-import-hooks"
	ignore_check "$var" && return 100

	/usr/bin/python2.7 - <<EOF
#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import atexit
import shutil
import tempfile
import subprocess


def dpkg(files):
	etc = {}
	cmd_dpkg = ["dpkg", "-S"] + files
	proc = subprocess.Popen(cmd_dpkg, stdout=subprocess.PIPE)
	for line in proc.stdout:
		pkg, fn = line.decode('UTF-8', 'replace').strip().split(': ')
		etc[fn] = pkg
	return etc


def uninstalled(package):
	try:
		out = subprocess.check_output(['dpkg-query', '-W', '-f', '\${Status}', package], env={'LANG': 'C'})
	except subprocess.CalledProcessError:
		return False
	return out.decode('UTF-8', 'replace').startswith('deinstall ')


def get_registered_files():
	for dir in ('/usr/share/ucs-school-import/checks/', '/usr/share/ucs-school-import/pyhooks/'):
		for path, directories, files in os.walk(dir):
			for file in files:
				if not file.endswith('.py'):
					continue
				yield os.path.join(path, file)


registered_files = list(get_registered_files())
failed = []
for hook in registered_files:
	ret = subprocess.call(('/usr/bin/python3', '-m', 'py_compile', hook), stdout=open('/dev/null', 'a'), stderr=subprocess.STDOUT, close_fds=True)
	if ret:
		failed.append(hook)

if failed:
	packages = dpkg(failed)
failed = [p for p in failed if not packages.get(p) or not uninstalled(packages[p])]
if failed:
	print('The following UCS@school Import Hooks are not compatible with Python 3:')
for failed_hook in failed:
	print('\\t', failed_hook, end='')
	if failed_hook in packages:
		print(' (package: %s)' % (packages[failed_hook], ), end='')
	print('')
if failed:
	exit(1)
EOF
}

checks () {
	# stderr to log
	exec 2>>"$UPDATER_LOG"

	local f name stat stdout ret key success=true
	declare -A messages
	for f in $(declare -F)
	do
		if [[ "$f" =~ update_check_.* ]]
		then
			name=${f#update_check_}
			stat="OK"
			printf "%-50s" "Checking $name ... "
			stdout=$($f)
			ret=$?
			if [ $ret -ne 0 ]
			then
				if [ $ret -eq 100 ]
				then
					stat="IGNORED"
				else
					stat="FAIL"
					success=false
					messages["$name"]="$stdout"
				fi
			fi
			echo "$stat"
		fi
	done

	# summary
	ret=0
	if ! $success
	then
		echo
		echo "The system can not be updated to UCS $VERSION_NAME due to the following reasons:"
		for key in "${!messages[@]}"
		do
			echo
			echo "$key:"
			echo "${messages[$key]}" # | fmt --uniform-spacing --width="${COLUMNS:-80}"
		done
		echo
		ret=1
	fi
	[ "$ret" -gt 0 ] &&
		exit "$ret"
}

if [ "x$phase" = "xpre" ] && [ "x$version" = "x5.0-0" ]; then
	checks
fi

if [ "x$phase" = "xpost" ] && [ "x$version" = "x5.0-0" ]; then
	[ -f /etc/apt/preferences.d/99ucsschool500.pref ] ||
		cat >/etc/apt/preferences.d/99ucsschool500.pref <<__PREF__
Package: *
Pin: release ucs@school, o=Univention, l=ucs@school, v=$school_version
Pin-Priority: 1002
__PREF__

fi

exit 0
