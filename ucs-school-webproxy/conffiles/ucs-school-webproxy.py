#!/usr/bin/python2.4
#
# Univention Config Registry
#  enable/disable internet access in squidguard config
#
# Copyright (C) 2007-2009 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

#
# proxy/filter/redirecttarget
# proxy/filter/hostgroup/blacklisted/*
# proxy/filter/{url,domain}/{blacklisted,whitelisted}/*
#
# Examples:
# proxy/filter/domain/blacklisted/1: www.gmx.de
# proxy/filter/domain/whitelisted/1: www.erlaubt.de
# proxy/filter/url/blacklisted/1: http://www.gesperrt.de/gesperrt.html
# proxy/filter/url/whitelisted/1: http://www.inhalt.de/interessanter-inhalt.html
# proxy/filter/hostgroup/blacklisted/RaumA: 10.200.18.199,10.200.18.195,10.200.18.197
# proxy/filter/redirecttarget: http://dc712.somewhere.de/blocked-by-squid.html
# proxy/filter/usergroup/308-1B: michael3,daniel7,klara4,meike2
# proxy/filter/groupdefault/308-1B: myprofile
# proxy/filter/setting/myprofile/domain/blacklisted/1: www.porno.de
# proxy/filter/setting/myprofile/domain/whitelisted/1: www.alleswirdgut.de
# proxy/filter/setting/myprofile/url/whitelisted/1: http://www.allessupi.de/toll.html
# proxy/filter/setting/myprofile/filtertype: whitelist-block ODER blacklist-pass ODER whitelist-blacklist-pass

import os
import re

conf_squidguard = '/etc/squid/squidGuard.conf'
confdir_squidguard = '/var/lib/ucs-school-webproxy'

def preinst(configRegistry, changes):
	pass

def postinst(configRegistry, changes):
	pass

def handler(configRegistry, changes):
	rewrite_squidguard_config = False
	rewrite_squidguard_proxy_settings = False
	rewrite_squidguard_blacklist = False
	rewrite_squidguard_NTLMuserlist = False
	windows_domain_changed = False

	def groupdefault_is_set_for(usergroupname):
		return configRegistry.has_key('proxy/filter/groupdefault/%s' % usergroupname)

	for key in changes.keys():
		if key.startswith('proxy/filter/hostgroup/blacklisted/') or key == 'proxy/filter/redirecttarget' or key.startswith('proxy/filter/groupdefault'):
			rewrite_squidguard_config = True
		elif key.startswith('proxy/filter/usergroup/'):
			rewrite_squidguard_config = True
			rewrite_squidguard_NTLMuserlist = True
		elif key.startswith('proxy/filter/setting/'):
			rewrite_squidguard_config = True
			rewrite_squidguard_proxy_settings = True
		elif key.startswith('proxy/filter/'):
			rewrite_squidguard_blacklist = True
		elif key == 'windows/domain':
			rewrite_squidguard_NTLMuserlist = True
			windows_domain_changed = True

	if rewrite_squidguard_config:
		default_redirect = 'http://%s.%s/blocked-by-squid.html' % (configRegistry['hostname'], configRegistry['domainname'])
		if configRegistry.has_key('proxy/filter/redirecttarget'):
			default_redirect = configRegistry['proxy/filter/redirecttarget']

		f = open(conf_squidguard, "w")

		f.write('logdir /var/log/squid\n')
		f.write('dbhome %s/\n\n' % confdir_squidguard)

		keylist = configRegistry.keys()

		proxy_settinglist = []
		for key in keylist:
			regex = re.compile('^proxy/filter/setting/([^/]+)/.*$')
			match = regex.match(key)
			if match:
				if match.group(1) not in proxy_settinglist:
					proxy_settinglist.append(match.group(1))

		roomlist = []
		usergrouplist = []
		for key in keylist:
			if key.startswith('proxy/filter/hostgroup/blacklisted/'):
				room = key[ len('proxy/filter/hostgroup/blacklisted/') : ]
				if room[0].isdigit():
					room = 'univention-%s' % room
				roomlist.append(room)
				f.write('src %s {\n' % room )
				ipaddrs = configRegistry[key].split(' ')
				for ipaddr in ipaddrs:
					f.write('    ip %s\n' % ipaddr)
				f.write('}\n\n')
			if key.startswith('proxy/filter/usergroup/'):
				usergroupname=key.rsplit('/', 1)[1]
				if groupdefault_is_set_for(usergroupname):
					usergrouplist.append(usergroupname)
					f.write('src usergroup-%s {\n' % usergroupname )
					f.write('    userlist usergroup-%s\n' % usergroupname )
					f.write('}\n\n')

		f.write('dest blacklist {\n')
		f.write('    domainlist blacklisted-domain\n')
		f.write('    urllist    blacklisted-url\n')
		f.write('}\n\n')

		f.write('dest whitelist {\n')
		f.write('    domainlist whitelisted-domain\n')
		f.write('    urllist    whitelisted-url\n')
		f.write('}\n\n')

		for proxy_setting in proxy_settinglist:
			f.write('dest blacklist-%s {\n' % proxy_setting)
			f.write('    domainlist blacklisted-domain-%s\n' % proxy_setting)
			f.write('    urllist    blacklisted-url-%s\n' % proxy_setting)
			f.write('}\n\n')
			f.write('dest whitelist-%s {\n' % proxy_setting)
			f.write('    domainlist whitelisted-domain-%s\n' % proxy_setting)
			f.write('    urllist    whitelisted-url-%s\n' % proxy_setting)
			f.write('}\n\n')

		f.write('acl {\n')
		for room in roomlist:
			f.write('    %s {\n' % room)
			f.write('        pass none\n')
			f.write('        redirect %s\n' % default_redirect)
			f.write('    }\n\n')

		for usergroupname in usergrouplist:
			proxy_setting_key_for_group='proxy/filter/groupdefault/%s' % usergroupname
			if configRegistry[proxy_setting_key_for_group] in proxy_settinglist:
				proxy_setting=configRegistry[proxy_setting_key_for_group]

				filtertype = configRegistry.get('proxy/filter/setting/%s/filtertype' % proxy_setting, 'whitelist-blacklist-pass')
				if filtertype == 'whitelist-blacklist-pass':
					f.write('    usergroup-%s {\n' % usergroupname)
					f.write('        pass whitelist-%s !blacklist-%s all\n' % (proxy_setting, proxy_setting) )
					f.write('        redirect %s\n' % default_redirect)
					f.write('    }\n\n')
				elif filtertype == 'whitelist-block':
					f.write('    usergroup-%s {\n' % usergroupname)
					f.write('        pass whitelist-%s none\n' % proxy_setting )
					f.write('        redirect %s\n' % default_redirect)
					f.write('    }\n\n')
				elif filtertype == 'blacklist-pass':
					f.write('    usergroup-%s {\n' % usergroupname)
					f.write('        pass !blacklist-%s all\n' % proxy_setting )
					f.write('        redirect %s\n' % default_redirect)
					f.write('    }\n\n')

		f.write('    default {\n')
		f.write('         pass whitelist !blacklist all\n')
		f.write('         redirect %s\n' % default_redirect)
		f.write('    }\n')
		f.write('}\n')

		f.close()

	if rewrite_squidguard_NTLMuserlist:
		if not windows_domain_changed:
			keylist = changes.keys()
		else:
			keylist = configRegistry.keys()
		domain=configRegistry['windows/domain']
		for key in keylist:
			if key.startswith('proxy/filter/usergroup/'):
				usergroupname=key.rsplit('/', 1)[1]
				filename='usergroup-%s' % usergroupname
				dbfn = '%s/%s' % (confdir_squidguard, filename)
				f = open(dbfn, "w")
				for memberUid in configRegistry[key].split(','):
					f.write('%s\n' % (memberUid) )
					f.write('%s\\%s\n' % (domain, memberUid) )

				f.close()
				os.system('squidGuard -C %s' % filename)
				os.system('chmod ug+rw %s %s.db 2> /dev/null' % (dbfn, dbfn))
				os.system('chown root:proxy %s %s.db  2> /dev/null' % (dbfn, dbfn))

	if rewrite_squidguard_blacklist:
		keylist = configRegistry.keys()
		for filtertype in [ 'domain', 'url' ]:
			for itemtype in [ 'blacklisted', 'whitelisted' ]:
				filename='%s-%s' % (itemtype, filtertype)
				dbfn = '%s/%s' % (confdir_squidguard, filename)
				f = open(dbfn, "w")

				for key in keylist:
					if key.startswith('proxy/filter/%s/%s/' % (filtertype, itemtype)):
						value = configRegistry[ key ]
						if value.startswith('http://'):
							value = value[ len('http://') : ]
						if value.startswith('https://'):
							value = value[ len('https://') : ]
						if value.startswith('ftp://'):
							value = value[ len('ftp://') : ]

						if filtertype == 'url':
							if value.startswith('www.'):
								value = value[ len('www.') : ]

						f.write('%s\n' % value)

				f.close()
				os.system('squidGuard -C %s' % filename)
				os.system('chmod ug+rw %s %s.db 2> /dev/null' % (dbfn, dbfn))
				os.system('chown root:proxy %s %s.db  2> /dev/null' % (dbfn, dbfn))

	if rewrite_squidguard_proxy_settings:
		proxy_settinglist = []
		changeskeylist = changes.keys()
		for key in changeskeylist:
			regex = re.compile('^proxy/filter/setting/([^/]+)/.*$')
			match = regex.match(key)
			if match:
				if match.group(1) not in proxy_settinglist:
					proxy_settinglist.append(match.group(1))

		keylist = configRegistry.keys()
		for proxy_setting in proxy_settinglist:
			for filtertype in [ 'domain', 'url' ]:
				for itemtype in [ 'blacklisted', 'whitelisted' ]:
					filename='%s-%s-%s' % (itemtype, filtertype, proxy_setting)
					dbfn = '%s/%s' % (confdir_squidguard, filename)
					f = open(dbfn, "w")

					for key in keylist:
						if key.startswith('proxy/filter/setting/%s/%s/%s/' % (proxy_setting, filtertype, itemtype)):
							value = configRegistry[ key ]
							if value.startswith('http://'):
								value = value[ len('http://') : ]
							if value.startswith('https://'):
								value = value[ len('https://') : ]
							if value.startswith('ftp://'):
								value = value[ len('ftp://') : ]

							if filtertype == 'url':
								if value.startswith('www.'):
									value = value[ len('www.') : ]

							f.write('%s\n' % value)

					f.close()
					os.system('squidGuard -C %s' % filename)
					os.system('chmod ug+rw %s %s.db 2> /dev/null' % (dbfn, dbfn))
					os.system('chown root:proxy %s %s.db  2> /dev/null' % (dbfn, dbfn))

	# and finally
#	os.system('kill -HUP `cat /var/run/squid.pid`')
	os.system('/etc/init.d/squid reload')
