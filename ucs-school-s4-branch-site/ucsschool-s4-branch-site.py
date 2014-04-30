#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention S4 Connector
#  Univention Directory Listener script for the s4 connector
#
# Copyright 2004-2013 Univention GmbH
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

__package__='' 	# workaround for PEP 366
import listener
import univention.debug as ud
import univention.admin.uexceptions as udm_errors
import univention.uldap
import univention.config_registry

## import s4-connector listener module code, but don't generate pyc file
import sys
sys.dont_write_bytecode = True
import imp
s4_connector_listener_path = '/usr/lib/univention-directory-listener/system/s4-connector.py'
s4_connector_listener = imp.load_source('s4_connector', s4_connector_listener_path)
from ucsschool.lib.schoolldap import LDAP_Connection, MACHINE_READ

name='ucsschool-s4-branch-site'
description='UCS@school S4 branch site module'
filter='(&(objectClass=univentionDomainController)(univentionService=Samba 4)(univentionService=UCS@school))'
attributes=[]

# use the modrdn listener extension
modrdn="1"

ldap_hostdn = listener.configRegistry.get('ldap/hostdn')
local_schoolDN = None
local_school = None
_char_index = ldap_hostdn.find('ou=')	## this the school detection used in scholldap.SearchBase.getOU
if _char_index < 0:
	local_schoolDN = ldap_hostdn[_char_index:]
	local_school = univention.uldap.explodeDn( local_schoolDN, 1 )[0]

record_type = "srv_record"

STD_SRV_PRIO = 0
STD_SRV_WEIGHT = 100
KDC_PORT = 88
KPASSWD_PORT = 464
S4_LDAP_PORT = 389
GC_LDAP_PORT = 3268

STD_SRV_PRIO_WEIGHT_PORT = {
	'kdc': " ".join((str(STD_SRV_PRIO), str(STD_SRV_WEIGHT), str(KDC_PORT))),
	'kpasswd': " ".join((str(STD_SRV_PRIO), str(STD_SRV_WEIGHT), str(KPASSWD_PORT))),
	's4_ldap': " ".join((str(STD_SRV_PRIO), str(STD_SRV_WEIGHT), str(S4_LDAP_PORT))),
	'gc_ldap': " ".join((str(STD_SRV_PRIO), str(STD_SRV_WEIGHT), str(GC_LDAP_PORT))),
}

STD_S4_SRV_RECORDS = {
	"_ldap._tcp": STD_SRV_PRIO_WEIGHT_PORT['s4_ldap'],
	"_ldap._tcp.pdc._msdcs": STD_SRV_PRIO_WEIGHT_PORT['s4_ldap'],
	"_ldap._tcp.dc._msdcs": STD_SRV_PRIO_WEIGHT_PORT['s4_ldap'],
	"_ldap._tcp.gc._msdcs": STD_SRV_PRIO_WEIGHT_PORT['gc_ldap'],
	"_gc._tcp": STD_SRV_PRIO_WEIGHT_PORT['gc_ldap'],
	"_kerberos._tcp": STD_SRV_PRIO_WEIGHT_PORT['kdc'],
	"_kerberos._udp": STD_SRV_PRIO_WEIGHT_PORT['kdc'],
	"_kerberos-adm._tcp": STD_SRV_PRIO_WEIGHT_PORT['kdc'],
	"_kerberos._tcp.dc._msdcs": STD_SRV_PRIO_WEIGHT_PORT['kdc'],
	"_kpasswd._tcp": STD_SRV_PRIO_WEIGHT_PORT['kpasswd'],
	"_kpasswd._udp": STD_SRV_PRIO_WEIGHT_PORT['kpasswd'],
	"_kerberos._tcp.default-first-site-name._sites.dc._msdcs": STD_SRV_PRIO_WEIGHT_PORT['kdc'],
	"_kerberos._tcp.default-first-site-name._sites.gc._msdcs": STD_SRV_PRIO_WEIGHT_PORT['kdc'],
	"_kerberos._tcp.default-first-site-name._sites": STD_SRV_PRIO_WEIGHT_PORT['kdc'],
	"_ldap._tcp.default-first-site-name._sites.dc._msdcs": STD_SRV_PRIO_WEIGHT_PORT['s4_ldap'],
	"_ldap._tcp.default-first-site-name._sites.gc._msdcs": STD_SRV_PRIO_WEIGHT_PORT['gc_ldap'],
	"_ldap._tcp.default-first-site-name._sites": STD_SRV_PRIO_WEIGHT_PORT['s4_ldap'],
	"_gc._tcp.default-first-site-name._sites": STD_SRV_PRIO_WEIGHT_PORT['gc_ldap'],
}
## _kerberos._tcp.default-first-site-name._sites.gc._msdcs only on ucs-school-master ?
## _ldap._tcp.default-first-site-name._sites.gc._msdcs only on ucs-school-slave ?

@LDAP_Connection(MACHINE_READ)
def visible_samba4_school_dcs(ldap_machine_read=None, ldap_position=None, search_base=None):
	_visible_samba4_school_dcs = []
	filter = '(&(objectClass=univentionDomainController)(univentionService=Samba 4)(univentionService=UCS@school))'
	try:
		res = ldap_machine_read.search(base=ldap_position.getDn(), filter=filter, attr=['cn', 'associatedDomain'])
		for (record_dn, obj) in res:
			if search_base.getOU(record_dn): # select only school branches
				_visible_samba4_school_dcs.append('.'.join((obj['cn'][0], obj['associatedDomain'][0])))
	except udm_errors.ldapError, e:
		ud.debug(ud.LISTENER, ud.ERROR, '%s: Error accessing LDAP: %s' % (name, e))

	return _visible_samba4_school_dcs


@LDAP_Connection(MACHINE_READ)
def update_records(ldap_machine_read=None, ldap_position=None, search_base=None):
	ud.debug(ud.LISTENER, ud.ERROR, '%s: update_records' % (name,))
	global STD_S4_SRV_RECORDS
	global record_type

	domain = listener.configRegistry.get('domainname')

	server_fqdn_list = visible_samba4_school_dcs()

	ucr = univention.config_registry.ConfigRegistry()
	ucr.load()

	ucr_key_value_list = []
	rdn_list = []
	for (relativeDomainName, prio_weight_port) in STD_S4_SRV_RECORDS.items():
		## construct ucr key name
		record_fqdn = ".".join((relativeDomainName, domain))
		key = 'connector/s4/mapping/dns/%s/%s/location' % (record_type, record_fqdn)
		ud.debug(ud.LISTENER, ud.ERROR, '%s: update_records check: %s' % (name, key))

		## check old value
		old_value = ucr.get(key)
		if not old_value or old_value == 'ignore':
			continue	## don't touch if unset or ignored

		## create new value
		value = ""
		for server_fqdn in server_fqdn_list:
			if value:
				value += " "
			value += "%s %s." % (prio_weight_port, server_fqdn)

		## set new value
		ucr_key_value = "=".join((key, value))
		ud.debug(ud.LISTENER, ud.PROCESS, '%s: update_records set: %s' % (name, value))
		ucr_key_value_list.append(ucr_key_value)
		rdn_list.append(relativeDomainName)
	
	if ucr_key_value_list:
		univention.config_registry.handler_set(ucr_key_value_list)

	for relativeDomainName in rdn_list:
		### trigger S4 Connector
		filter = '(&(univentionObjectType=dns/%s)(zoneName=%s)(relativeDomainName=%s))' % (record_type, domain, relativeDomainName)
		try:
			ud.debug(ud.LISTENER, ud.PROCESS, '%s: update_records trigger s4 connector: %s' % (name, relativeDomainName))
			res = ldap_machine_read.search(base=ldap_position.getDn(), filter=filter)
			for (record_dn, obj) in res:
				s4_connector_listener.handler(record_dn, obj, obj, 'm')
		except udm_errors.ldapError, e:
			ud.debug(ud.LISTENER, ud.ERROR, '%s: Error accessing LDAP: %s' % (name, e))


def add(dn, new):
	cn = new.get('cn')[0]
	associatedDomain = new.get('associatedDomain')[0]
	fqdn = ('.'.join((cn, associatedDomain)))
	## TODO
	update_records()

def modify(dn, new, old, old_dn=None):
	## TODO
	update_records()

def delete(old_dn, old):
	## TODO
	update_records()

def handler(dn, new, old, command):
	if dn.find('ou=') < 0:	## only handle DCs in school branch sites
		return

	listener.setuid(0)
	try:
		if new:
			if old:
				modify(dn, new, old)
			else:
				add(dn, new)
		else:
			## TODO: command == 'r'
			if old:
				delete(dn, new, old)
			else:
				pass
	finally:
		listener.unsetuid()
