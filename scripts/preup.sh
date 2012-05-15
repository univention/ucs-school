#!/bin/bash
#
# Copyright (C) 2012 Univention GmbH
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

echo "Running ucsschool 3.0 preup.sh script" >&3
date >&3

# preup post 3.0-0 (after 3.0-0 preup)
if [ "$UPDATE_STATE" = "post" -a "$UPDATE_NEXT_VERSION" = "3.0-0" ]; then

	# squidGuard needs existing files for each domainlist|urllist declaration in 
	# /etc/squid/squidGuard.conf, otherwise update-squidguard goes to emergency mode
	# and never returns
	if [ -e /etc/squid/squidGuard.conf -a -d /var/lib/ucs-school-webproxy ]; then
		fileList=$(cat /etc/squid/squidGuard.conf | grep 'domainlist\|urllist' | sed -e 's/ *urllist *//' -e 's/ *domainlist *//')
		for i in $fileList; do 
			touch "/var/lib/ucs-school-webproxy/$i"
		done
	fi
fi

echo "ucsschool 3.0 preup.sh script finished" >&3
date >&3

exit 0

