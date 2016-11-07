#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention S4 Connector
#  Univention Directory Listener script for the s4 connector
#
# Copyright 2014-2016 Univention GmbH
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

__package__ = ''		# workaround for PEP 366
import listener
import univention.debug as ud
import univention.admin.uexceptions as udm_errors
import univention.uldap
import univention.config_registry

## import s4-connector listener module code, but don't generate pyc file
import os
import sys
import ldap
sys.dont_write_bytecode = True
import imp
s4_connector_listener_path = '/usr/lib/univention-directory-listener/system/s4-connector.py'
s4_connector_listener = imp.load_source('s4_connector', s4_connector_listener_path)
from ucsschool.lib.schoolldap import LDAP_Connection, MACHINE_READ, SchoolSearchBase
import traceback
import subprocess

### Listener registration data
name = 'ucsschool-s4-branch-site'
description = 'UCS@school S4 branch site module'

################ <Hooks handling> ###############
HOOKS_BASEDIR = "/usr/lib/univention-directory-listener/hooks"
LISTENER_HOOKS_BASEDIR = os.path.join(HOOKS_BASEDIR, "%s.d" % (name,))


def load_hooks():
	hooks = []
	if not os.path.isdir(LISTENER_HOOKS_BASEDIR):
		return hooks

	filenames = os.listdir(LISTENER_HOOKS_BASEDIR)
	filenames.sort()
	for filename in filenames:
		if not filename.endswith('.py') or filename.startswith('__'):
			continue
		file_path = os.path.join(LISTENER_HOOKS_BASEDIR, filename)

		modulename = '.'.join((name.replace('-', '_'), filename[:-3].replace('-', '_')))
		ud.debug(ud.LISTENER, ud.ALL, "%s: importing '%s'" % (name, modulename))
		try:
			hook = imp.load_source(modulename, file_path)
		except Exception as ex:
			ud.debug(ud.LISTENER, ud.ERROR, "Error importing %s as %s:" % (file_path, modulename))
			ud.debug(ud.LISTENER, ud.ERROR, traceback.format_exc())
		hooks.append(hook)

	return hooks


def run_hooks(fname, *args):
	global _hooks
	for hook in _hooks:
		if hasattr(hook, fname):
			try:
				hook_func = getattr(hook, fname)
				hook_func(*args)
			except Exception as ex:
				ud.debug(ud.LISTENER, ud.ERROR, "Error running %s.%s():" % (hook.__name__, fname))
				ud.debug(ud.LISTENER, ud.ERROR, traceback.format_exc())
################ </Hooks handling> ##############


### Global variables
_ucsschool_service_specialization_filter = ''
_relativeDomainName_trigger_set = set()
_s4_connector_restart = False
_local_domainname = listener.configRegistry.get('domainname')
_ldap_hostdn = listener.configRegistry.get('ldap/hostdn')
_hooks = []


@LDAP_Connection(MACHINE_READ)
def on_load(ldap_machine_read=None, ldap_position=None):
	global _ldap_hostdn
	global _hooks
	_hooks = load_hooks()

	global _ucsschool_service_specialization_filter
	try:
		res = ldap_machine_read.search(base=_ldap_hostdn, scope='base', attr=('univentionService',))
	except udm_errors.ldapError, e:
		ud.debug(ud.LISTENER, ud.ERROR, '%s: Error accessing LDAP: %s' % (name, e))
		return

	services = []
	if res:
		(record_dn, obj) = res[0]
		if 'univentionService' in obj:
			services = obj['univentionService']

	for service_id in ('UCS@school Education', 'UCS@school Administration'):
		if service_id in services:
			_ucsschool_service_specialization_filter = "(univentionService=%s)" % service_id
			break

### Initialization of global variables
listener.setuid(0)
try:
	on_load()
except ldap.INVALID_CREDENTIALS as ex:
	raise ImportError("Error accessing LDAP via machine account: %s" % (ex,))
finally:
	listener.unsetuid()

### Listener registration data
filter = '(&(univentionService=S4 SlavePDC)%s)' % (_ucsschool_service_specialization_filter,)
attributes = ['cn', 'associatedDomain', 'description']  # support retrigger via description
modrdn = "1"  # use the modrdn listener extension

### Contants
_record_type = "srv_record"
STD_SRV_PRIO = 0
STD_SRV_WEIGHT = 100
KDC_PORT = 88
KPASSWD_PORT = 464
S4_LDAP_PORT = 389
GC_LDAP_PORT = 3268

STD_SRV_PRIO_WEIGHT_PORT = {
	'kdc': (STD_SRV_PRIO, STD_SRV_WEIGHT, KDC_PORT),
	'kpasswd': (STD_SRV_PRIO, STD_SRV_WEIGHT, KPASSWD_PORT),
	's4_ldap': (STD_SRV_PRIO, STD_SRV_WEIGHT, S4_LDAP_PORT),
	'gc_ldap': (STD_SRV_PRIO, STD_SRV_WEIGHT, GC_LDAP_PORT),
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

### Listener code


@LDAP_Connection(MACHINE_READ)
def visible_samba4_school_dcs(excludeDN=None, ldap_machine_read=None, ldap_position=None):
	global filter
	_visible_samba4_school_dcs = []
	try:
		res = ldap_machine_read.search(base=ldap_position.getDn(),
			filter=filter,
			attr=['cn', 'associatedDomain'])
		for (record_dn, obj) in res:
			## select only school branches and exclude a modrdn 'r' phase DN which still exists
			if SchoolSearchBase.getOU(record_dn) and record_dn != excludeDN:
				if 'associatedDomain' in obj:
					domainname = obj['associatedDomain'][0]
				else:
					domainname = _local_domainname
				_visible_samba4_school_dcs.append('.'.join((obj['cn'][0], domainname)))
	except udm_errors.ldapError, e:
		ud.debug(ud.LISTENER, ud.ERROR, '%s: Error accessing LDAP: %s' % (name, e))

	return _visible_samba4_school_dcs


def update_ucr_overrides(excludeDN=None):
	global STD_S4_SRV_RECORDS
	global _record_type
	global _local_domainname
	global _s4_connector_restart
	global _relativeDomainName_trigger_set

	server_fqdn_list = visible_samba4_school_dcs(excludeDN=excludeDN)
	server_fqdn_list.sort()

	ucr = univention.config_registry.ConfigRegistry()
	ucr.load()    # dynamic reload

	ucr_key_value_list = []
	for (relativeDomainName, prio_weight_port) in STD_S4_SRV_RECORDS.items():
		## construct ucr key name
		record_fqdn = ".".join((relativeDomainName, _local_domainname))
		key = 'connector/s4/mapping/dns/%s/%s/location' % (_record_type, record_fqdn)
		ud.debug(ud.LISTENER, ud.ALL, '%s: UCR check: %s' % (name, key))

		## check old value
		old_ucr_locations = ucr.get(key)
		if old_ucr_locations is None or old_ucr_locations == 'ignore':
			continue  # don't touch if unset or ignored
		## Extract current prio/weight/port
		old_server_fqdn_list = []
		old_prio_weight_port = {}
		priority = None
		weight = None
		port = None
		target = None
		for v in old_ucr_locations.split(' '):
			try:
				## Check explicit for None, because the int values may be 0
				if priority is None:
					priority = int(v)
				elif weight is None:
					weight = int(v)
				elif port is None:
					port = int(v)
				elif not target:
					target = v.rstrip('.')
				if priority is not None and weight is not None and port is not None and target:
					old_server_fqdn_list.append(target)
					old_prio_weight_port[target] = (priority, weight, port)
					priority = None
					weight = None
					port = None
					target = None
			except ValueError as ex:
				ud.debug(ud.LISTENER, ud.ERROR, '%s: Error parsing UCR variable %s: %s' % (name, key, ex))
				priority = None
				weight = None
				port = None
				target = None

		## create new value
		ucr_locations_list = []
		## add the old ones in ucr given order, if they are still visible
		done_list = []
		for server_fqdn in old_server_fqdn_list:
			if server_fqdn in server_fqdn_list:
				_prio_weight_port_str = " ".join(map(str, old_prio_weight_port[server_fqdn]))
				ucr_locations_list.append("%s %s." % (_prio_weight_port_str, server_fqdn))
				done_list.append(server_fqdn)
			else:
				ud.debug(ud.LISTENER, ud.ALL, '%s: server in UCR not visible in LDAP: %s' % (name, server_fqdn))
		## append the ones visible in LDAP but not yet in UCR:
		for server_fqdn in server_fqdn_list:
			if server_fqdn not in done_list:
				_prio_weight_port_str = " ".join(map(str, prio_weight_port))
				ucr_locations_list.append("%s %s." % (_prio_weight_port_str, server_fqdn))
		ucr_locations = " ".join(ucr_locations_list)

		## set new value
		if ucr_locations == old_ucr_locations:
			ud.debug(ud.LISTENER, ud.ALL, '%s: UCR skip: %s' % (name, ucr_locations))
		else:
			ucr_key_value = "=".join((key, ucr_locations))
			ud.debug(ud.LISTENER, ud.PROCESS, '%s: UCR set: %s="%s"' % (name, key, ucr_locations))
			ucr_key_value_list.append(ucr_key_value)

		## always trigger S4 Connector
		_relativeDomainName_trigger_set.add(relativeDomainName)

	if ucr_key_value_list:
		univention.config_registry.handler_set(ucr_key_value_list)
		_s4_connector_restart = True


@LDAP_Connection(MACHINE_READ)
def trigger_sync_ucs_to_s4(ldap_machine_read=None, ldap_position=None):
	global _record_type
	global _local_domainname
	global _relativeDomainName_trigger_set

	for relativeDomainName in list(_relativeDomainName_trigger_set):
		### trigger S4 Connector
		ldap_filter = '(&(univentionObjectType=dns/%s)(zoneName=%s)(relativeDomainName=%s))' % (_record_type, _local_domainname, relativeDomainName)
		try:
			ud.debug(ud.LISTENER, ud.PROCESS, '%s: trigger s4 connector: %s' % (name, relativeDomainName))
			res = ldap_machine_read.search(base=ldap_position.getDn(), filter=ldap_filter, attr=['*', '+'])
			for (record_dn, obj) in res:
				s4_connector_listener.handler(record_dn, obj, obj, 'm')
				_relativeDomainName_trigger_set.remove(relativeDomainName)
		except udm_errors.ldapError, e:
			ud.debug(ud.LISTENER, ud.ERROR, '%s: Error accessing LDAP: %s' % (name, e))


def add(dn, new):
	listener.setuid(0)
	try:
		update_ucr_overrides()
	finally:
		listener.unsetuid()


def modify(dn, new, old):
	listener.setuid(0)
	try:
		update_ucr_overrides()
	finally:
		listener.unsetuid()


def delete(old_dn, old, command):
	## this is also called on modrdn (command == 'r').
	listener.setuid(0)
	try:
		## in modrdn phase 'r' the DN is still present in local LDAP, so we explicitly exclude it
		update_ucr_overrides(excludeDN=old_dn)
	finally:
		listener.unsetuid()


def handler(dn, new, old, command):
	if not _ucsschool_service_specialization_filter:
		univention.debug.debug(univention.debug.LISTENER, univention.debug.INFO, '%s: Local UCS@school server type still unknown, ignoring.' % (name,))
		return

	univention.debug.debug(univention.debug.LISTENER, univention.debug.ALL, '%s: command: %s, dn: %s, new? %s, old? %s' % (name, command, dn, bool(new), bool(old)))

	if new:
		if ',ou=' not in dn.lower():  # only handle DCs in school branch sites
			return

		if old:
			modify(dn, new, old)
		else:
			add(dn, new)
	else:
		if old:
			## this is also called on modrdn (command == 'r').
			delete(dn, old, command)
		else:
			pass

	run_hooks("handler", dn, new, old, command)


def postrun():
	global _s4_connector_restart
	global _relativeDomainName_trigger_set

	if not listener.configRegistry.is_true('connector/s4/autostart', True):
		univention.debug.debug(univention.debug.LISTENER, univention.debug.PROCESS, '%s: S4 Connector restart skipped, disabled via connector/s4/autostart.' % (name,))
		return

	if os.path.isfile('/etc/init.d/univention-s4-connector'):
		if _s4_connector_restart:
			univention.debug.debug(univention.debug.LISTENER, univention.debug.PROCESS, '%s: Restarting S4 Connector' % (name,))
			listener.setuid(0)
			try:
				p = subprocess.Popen(["/etc/init.d/univention-s4-connector", "restart"], close_fds=True)
				p.wait()
				if p.returncode != 0:
					ud.debug(ud.LISTENER, ud.ERROR, '%s: S4 Connector restart returned %s.' % (name, p.returncode))
				_s4_connector_restart = False
			finally:
				listener.unsetuid()

		if _relativeDomainName_trigger_set:
			trigger_sync_ucs_to_s4()

	run_hooks("postrun")
