# UCS@school Common Shell Library
#
# SPDX-FileCopyrightText: 2011-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

#
# determine the school OU from ldap/hostdn
#

school_ou() {
	# syntax: school_ou [hostdn]
	#
	# Tries to determine the LDAP name of the host's OU.
	# The OU name is derived from the given host DN. If no DN has been passed to
	# the function, the hostdn of the system is used as fallback.
	# PLEASE NOTE: This function works only on Replica Directory Nodes!
	#              Other systems will return an empty value!
	#
	# example:
	# $ ucr get ldap/hostdn
	# cn=myreplica,cn=dc,cn=server,cn=computers,ou=gymmitte,dc=example,dc=com
	# $ school_ou
	# gymmitte
	# $ school_ou cn=myreplica,cn=dc,cn=server,cn=computers,ou=foobar,dc=example,dc=com
	# foobar
	# $ school_ou cn=myreplica,cn=dc,cn=server,cn=computers,ou=foo,ou=bar,dc=example,dc=com
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
	# PLEASE NOTE: This function works only on Replica Directory Nodes!
	#              Other systems will return an empty value!
	#
	# example:
	# $ ucr get ldap/hostdn
	# cn=myreplica,cn=dc,cn=server,cn=computers,ou=gymmitte,dc=example,dc=com
	# $ school_dn
	# ou=gymmitte,dc=example,dc=com
	# $ school_dn cn=myreplica,cn=dc,cn=server,cn=computers,ou=foobar,dc=example,dc=com
	# ou=foobar,dc=example,dc=com
	# $ school_dn cn=myreplica,cn=dc,cn=server,cn=computers,ou=foo,ou=bar,dc=example,dc=com
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
	# syntax: servers_school_ous [-d hostdn] [-H ldap_uri]
	#
	# Tries to determine all LDAP DNs of the OUs this host is responsible for.
	# The OU DN is retrieved from the local LDAP. If no DN has been passed to
	# the function, the hostdn of the system is used as fallback.
	# PLEASE NOTE: This function works only on Replica Directory Nodes!
	#              Other systems will return an empty value!
	#
	# example:
	# $ servers_school_ous
	# ou=bar,dc=example,dc=com
	#
	# $ servers_school_ous -d cn=myreplica,cn=dc,cn=server,cn=computers,ou=bar,dc=example,dc=com
	# ou=bar,dc=example,dc=com
	# ou=foo,dc=example,dc=com
	#
	# $ servers_school_ous -H ldap://primary.example.com:7389
	# ou=bar,dc=example,dc=com
	local ldap_hostdn ldap_base ldap_uri
	. /usr/share/univention-lib/ucr.sh

	ldap_base="$(/usr/sbin/univention-config-registry get ldap/base)"
	ldap_hostdn="$(/usr/sbin/univention-config-registry get ldap/hostdn)"
	ldap_uri=""

	while [ "$#" -gt 1 ]; do
		if [ "$1" = "-d" ]; then
			ldap_hostdn="$2"
		elif [ "$1" = "-H" ] ; then
			ldap_uri="-H $2"
		else
			echo "Unknown argument \"$1\"."
			echo "Usage: servers_school_ous [-d hostdn] [-H ldap_uri]"
			return 1
		fi
		shift 2
	done

	res=""
	for oudn in $(univention-ldapsearch $ldap_uri -LLL -b "$ldap_base" 'objectClass=ucsschoolOrganizationalUnit' dn | ldapsearch-wrapper | sed -nre 's/^dn: //p') ; do
		ouname="$(school_ou "$oudn")"
		if is_ucr_true ucsschool/singlemaster; then
			search_str="(|(cn=OU${ouname}-DC-Edukativnetz)(cn=OU${ouname}-DC-Verwaltungsnetz))"
		else
			search_str="(&(|(cn=OU${ouname}-DC-Edukativnetz)(cn=OU${ouname}-DC-Verwaltungsnetz))(uniqueMember=${ldap_hostdn}))"
		fi
		if univention-ldapsearch $ldap_uri -LLL "$search_str" dn | grep -q "^dn: "; then
			res="$res
$oudn"
		fi
	done
	echo -n "${res}" | egrep -v "^\s*$"
}
