# UCS@school Common Shell Library
#
# Copyright 2011-2016 Univention GmbH
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
	# syntax: school_ou [hostdn]
	#
	# Tries to determine the LDAP name of the host's OU.
	# The OU name is derived from the given host DN. If no DN has been passed to
	# the function, the hostdn of the system is used as fallback.
	# PLEASE NOTE: This function works only on domaincontroller_slave systems!
	#              Other systems will return an empty value!
	#
	# example:
	# $ ucr get ldap/hostdn
	# cn=myslave,cn=dc,cn=server,cn=computers,ou=gymmitte,dc=example,dc=com
	# $ school_ou
	# gymmitte
	# $ school_ou cn=myslave,cn=dc,cn=server,cn=computers,ou=foobar,dc=example,dc=com
	# foobar
	# $ school_ou cn=myslave,cn=dc,cn=server,cn=computers,ou=foo,ou=bar,dc=example,dc=com
	# foo

	local ldap_hostdn

	if [ -n "$1" ] ; then
		ldap_hostdn=",$1" # add leading comma, in case only the DN of the OU is given
	else
		ldap_hostdn="$(/usr/sbin/univention-config-registry get ldap/hostdn)"
	fi

	echo "$ldap_hostdn" | grep -oiE ',ou=.*$' | sed -nre 's/^,[oO][uU]=([^,]+),.*/\1/p'
}

school_dn() {
	# syntax: school_dn [hostdn]
	#
	# Tries to determine the LDAP DN of the host's OU.
	# The OU DN is derived from the given host DN. If no DN has been passed to
	# the function, the hostdn of the system is used as fallback.
	# PLEASE NOTE: This function works only on domaincontroller_slave systems!
	#              Other systems will return an empty value!
	#
	# example:
	# $ ucr get ldap/hostdn
	# cn=myslave,cn=dc,cn=server,cn=computers,ou=gymmitte,dc=example,dc=com
	# $ school_dn
	# ou=gymmitte,dc=example,dc=com
	# $ school_dn cn=myslave,cn=dc,cn=server,cn=computers,ou=foobar,dc=example,dc=com
	# ou=foobar,dc=example,dc=com
	# $ school_dn cn=myslave,cn=dc,cn=server,cn=computers,ou=foo,ou=bar,dc=example,dc=com
	# ou=foo,ou=bar,dc=example,dc=com

	local ldap_hostdn

	if [ -n "$1" ] ; then
		ldap_hostdn=",$1" # add leading comma, in case only the DN of the OU is given
	else
		ldap_hostdn="$(/usr/sbin/univention-config-registry get ldap/hostdn)"
	fi

	echo "$ldap_hostdn" | grep -oiE ',ou=.*$' | cut -b2-
}

servers_school_ous() {
	# syntax: servers_school_ous [-d hostdn] [-h ldap server] [-p ldap port]
	#
	# Tries to determine all LDAP DNs of the OUs this host is responsible for.
	# The OU DN is retrieved from the local LDAP. If no DN has been passed to
	# the function, the hostdn of the system is used as fallback.
	# PLEASE NOTE: This function works only on domaincontroller_slave systems!
	#              Other systems will return an empty value!
	#
	# example:
	# $ servers_school_ous
	# ou=bar,dc=example,dc=com
	#
	# $ servers_school_ous -d cn=myslave,cn=dc,cn=server,cn=computers,ou=bar,dc=example,dc=com
	# ou=bar,dc=example,dc=com
	# ou=foo,dc=example,dc=com
	#
	# $ servers_school_ous -h $(ucr get ldap/master) -p $(ucr get ldap/master/port)
	# ou=bar,dc=example,dc=com

	local ldap_hostdn ldap_base ldap_server ldap_port

	ldap_base="$(/usr/sbin/univention-config-registry get ldap/base)"
	ldap_hostdn="$(/usr/sbin/univention-config-registry get ldap/hostdn)"
	ldap_server=""
	ldap_port=""

	while (( "$#" )); do
		if [[ "$1" == "-d" ]]; then
			ldap_hostdn="$2"
		elif [ "$1" == "-h" ] ; then
			ldap_server="-h $2"
		elif [ "$1" == "-p" ] ; then
			ldap_port="-p $2"
		else
			echo "Unknown argument \"$1\"."
			echo "Usage: servers_school_ous [-d hostdn] [-h ldap server] [-p ldap port]"
			return 1
		fi
		shift 2
	done

	res=""
	for oudn in $(univention-ldapsearch $ldap_server $ldap_port -xLLL -b "$ldap_base" 'objectClass=ucsschoolOrganizationalUnit' dn | ldapsearch-wrapper | sed -nre 's/^dn: //p') ; do
		ouname="$(school_ou "$oudn")"
		if univention-ldapsearch $ldap_server $ldap_port -xLLL "(&(|(cn=OU${ouname}-DC-Edukativnetz)(cn=OU${ouname}-DC-Verwaltungsnetz))(uniqueMember=${ldap_hostdn}))" dn | grep -q "^dn: "; then
			res="$res $oudn"
		fi
	done
	echo -n "${res}" | sed -e 's/^[[:space:]]*//'
}
