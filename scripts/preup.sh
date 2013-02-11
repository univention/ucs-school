#!/bin/bash
#
# Copyright (C) 2012-2013 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

UPDATER_LOG="/var/log/univention/updater.log"
UPDATE_STATE="$1"
UPDATE_NEXT_VERSION="$2"
export DEBIAN_FRONTEND=noninteractive
exec 3>>"$UPDATER_LOG"
eval "$(univention-config-registry shell)" >&3 2>&3

echo "Running ucsschool 3.1 preup.sh script" >&3
date >&3

# prevent update on inconsistent system
if [ "$UPDATE_STATE" = "post" ]; then
	SAMBA4_PACKAGES="libdcerpc0 libdcerpc-server0 libgensec0 libndr0 libndr-standard0 libregistry0 libsamba-credentials0 libsamba-hostconfig0 libsamba-policy0 libsamba-util0 libsamdb0 libsmbclient-raw0 python-samba4 samba-dsdb-modules"

	echo "Testing for inconsistent package state..." >&3
	if ! dpkg-query -W -f '${Package} ${Status}\n' univention-samba4 2>&3 | grep "ok installed" >&3 ; then
		if dpkg-query -W -f '${Package} ${Status}\n' ${SAMBA4_PACKAGES} 2>&3 | grep "ok installed" >&3 ; then
			echo "Found samba4 packages but univention-samba4 is not installed. Trying to clean up..." >&3
			dpkg --remove ${SAMBA4_PACKAGES} 2>&3 >&3
			RET="$?"
			if [ ! $RET = 0 ] ; then
				echo "ERROR: exit code of dpkg: $RET" >&3
				echo "ERROR: inconsistent state: univention-samba4 is not installed but other samba4 packages are."
				echo "ERROR: continuing update would break update path - stopping update here"
				exit 1
			fi
		fi
	fi
	echo "OK" >&3
fi

echo "ucsschool 3.1 preup.sh script finished" >&3
date >&3

exit 0
