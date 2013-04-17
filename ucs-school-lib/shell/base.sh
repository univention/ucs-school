# UCS@School Common Shell Library
#
# Copyright 2011-2013 Univention GmbH
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


#
# determine the school OU from ldap/hostdn
#

school_ou() {
	eval "$(/usr/sbin/univention-config-registry shell \
				ldap/hostdn)"

	IFS0="$IFS"
	IFS=','
	set -- "$ldap_hostdn"
	for rdn in $@; do
		key=$(echo "${rdn%=*}" | tr a-z A-Z)
		if [ "$key" = "OU" ]; then
			echo "${rdn#*=}"
			break
		fi
	done
	IFS="$IFS0"
}

school_dn() {
	local district_mode
	if is_ucr_true 'ucsschool/ldap/district/enable'; then
		district_mode='true'
	else
		district_mode='false'
	fi

	eval "$(/usr/sbin/univention-config-registry shell \
				ldap/hostdn)"

	IFS0="$IFS"
	IFS=','
	skipped_rdns=''
	set -- "${ldap_hostdn%",$ldap_hostdn"}"
	for rdn in $@; do
		key=$(echo "${rdn%=*}" | tr a-z A-Z)
		if [ "$key" = "OU" ]; then
			IFS="$IFS0"
			echo ${ldap_hostdn#${skipped_rdns}}
			break
		fi
		skipped_rdns="${rdn},${skipped_rdns}"
	done
}

