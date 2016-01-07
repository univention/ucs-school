#!/usr/bin/python2.7
#
# Univention Config Registry
#  enable/disable internet access in squidguard config
#
# Copyright 2007-2015 Univention GmbH
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
import subprocess
import tempfile
import time
import shutil

PATH_LOG = '/var/log/univention/ucs-school-webproxy.log'
DIR_ETC = '/etc/squidguard'
FN_CONFIG = 'squidGuard.conf'
DIR_DATA = '/var/lib/ucs-school-webproxy'
FN_GLOBAL_BLACKLIST_PREFIX = 'global-blacklist'
TXT_GLOBAL_BLACKLIST_COMMENT = '###GLOBAL-BLACKLIST-COMMENT###'
UCR_FORCED_GLOBAL_BLACKLIST = 'proxy/filter/global/blacklists/forced'

def logerror(msg):
	logfd = open( PATH_LOG, 'a+')
	print >> logfd, '%s [%s] %s' % (time.strftime('%Y-%m-%d %H:%M:%S'), os.getpid(), msg)

def move_file(fnsrc, fndst):
	if os.path.isfile( fnsrc ):
		try:
			shutil.move( fnsrc, fndst )
		except Exception, e:
			logerror('cannot move %s to %s: Exception %s' % (fnsrc, fndst, e))
			raise

def quote(string):
	'Replace every unsafe byte with hex value'
	if type(string) is unicode:
		string = string.encode('utf-8')
	newstring = ''
	for byte in string:
		if byte in quote.safeBytes:
			newstring += byte
		else:
			newstring += '-' + byte.encode('hex')
	return newstring
quote.safeBytes = set('abcdefghijklmnopqrstuvwxyz012345679ABCDEFGHIJKLMNOPQRSTUVWXYZ')

def preinst(configRegistry, changes):
	pass

def postinst(configRegistry, changes):
	pass

def handler(configRegistry, changes):
	# create temporary directory
	DIR_TEMP = tempfile.mkdtemp(dir=DIR_DATA)

	fn_config = os.path.join(DIR_ETC, FN_CONFIG)
	(fno, fn_temp_config) = tempfile.mkstemp(dir=DIR_ETC)
	os.close(fno)

	checkGlobalBlacklist(configRegistry, DIR_DATA, changes)
	createTemporaryConfig(fn_temp_config, configRegistry, DIR_TEMP, changes)
	writeGlobalBlacklist(configRegistry, DIR_TEMP, changes)
	writeUsergroupMemberLists(configRegistry, DIR_TEMP)
	writeBlackWhiteLists(configRegistry, DIR_TEMP)
	writeSettinglist(configRegistry, DIR_TEMP)
	finalizeConfig(fn_temp_config, DIR_TEMP, DIR_DATA)
	moveConfig(fn_temp_config, fn_config, FN_CONFIG, DIR_TEMP, DIR_DATA)
	removeTempDirectory(DIR_TEMP)
	subprocess.call(('/etc/init.d/squid3', 'reload', ))

def createTemporaryConfig(fn_temp_config, configRegistry, DIR_TEMP, changes):
	# create config in temporary directory with temporary "dbhome" setting
	touchfnlist = []
	if 'proxy/filter/redirecttarget' in configRegistry:
		default_redirect = configRegistry['proxy/filter/redirecttarget']
	else:
		default_redirect = 'http://%s.%s/blocked-by-squid.html' % (configRegistry['hostname'], configRegistry['domainname'])

	f = open( fn_temp_config, "w")

	f.write('logdir /var/log/squidguard\n')
	f.write('dbhome %s/\n\n' % DIR_TEMP)

	keylist = configRegistry.keys()

	proxy_settinglist = set()
	regex = re.compile('^proxy/filter/setting/([^/]+)/.*$')
	for key in keylist:
		match = regex.match(key)
		if match:
			proxy_settinglist.add(match.group(1))
	proxy_settinglist = list(proxy_settinglist)

	roomIPs = {} # { 'theBigRoom': ['127.0.0.1', '127.4.5.7'], 'otherRoom': ['127.2.3.4'] }
	roomRule = {} # { 'kmiyagi': ['theBigRoom', 'otherRoom'] }
	roomRules = [] # [ 'kmiyagi' ]
	for key in keylist:
		if key.startswith('proxy/filter/room/'):
			parts = key.split('/')
			if len(parts) == 5:
				room = parts[3]
				if parts[-1] == 'ip':
					roomIPs[room] = configRegistry[key].split()
				elif parts[-1] == 'rule':
					roomRule.setdefault(configRegistry[key], []).append(room)
					if room not in roomIPs:
						roomIPs[room] = []
		elif key.startswith('proxy/filter/setting-user/'):
			roomRules.append(key.split('/')[3])

	for (room, IPs, ) in roomIPs.items():
		f.write('src room-%s {\n' % (quote(room), ))
		for IP in IPs:
			f.write('	ip	%s\n' % (IP, ))
		f.write('}\n')

	roomlist = []
	usergroupSetting = [] # [ (priority, usergroupname, proxy_setting, ) ] # for sorting by priority
	for key in keylist:
		if key.startswith('proxy/filter/hostgroup/blacklisted/'):
			room = key[ len('proxy/filter/hostgroup/blacklisted/') : ]
			if room[0].isdigit():
				room = 'univention-%s' % room
			roomlist.append(room)
			f.write('src %s {\n' % quote(room) )
			ipaddrs = configRegistry[key].split(' ')
			for ipaddr in ipaddrs:
				f.write('	 ip %s\n' % ipaddr)
			f.write('}\n\n')
		# usergroup
		if key.startswith('proxy/filter/usergroup/'):
			usergroupname=key.rsplit('/', 1)[1]
			default = configRegistry.get('proxy/filter/groupdefault/%s' % usergroupname)
			if default and default in proxy_settinglist:
				priority = configRegistry.get('proxy/filter/setting/%s/priority' % default)
				if priority and priority.isdigit():
					priority = int(priority)
				else:
					priority = 0
				usergroupSetting.append((priority, usergroupname, default))

	# src usergroup
	for (priority, usergroupname, proxy_setting) in reversed(sorted(usergroupSetting)):
		f.write('src usergroup-%s {\n' % quote(usergroupname) )
		f.write('        userlist usergroup-%s\n' % quote(usergroupname) )
		f.write('}\n\n')
		touchfnlist.append( 'usergroup-%s' % quote(usergroupname) )

	f.write('dest blacklist {\n')
	f.write('	 domainlist blacklisted-domain\n')
	f.write('	 urllist	blacklisted-url\n')
	f.write('}\n\n')
	touchfnlist.extend( ['blacklisted-domain', 'blacklisted-url'] )

	f.write('dest whitelist {\n')
	f.write('	 domainlist whitelisted-domain\n')
	f.write('	 urllist	whitelisted-url\n')
	f.write('}\n\n')
	touchfnlist.extend( ['whitelisted-domain', 'whitelisted-url'] )

	for proxy_setting in map(quote, proxy_settinglist) + [quote(username) + '-user' for username in roomRule]:
		f.write('dest blacklist-%s {\n' % proxy_setting)
		f.write('	 domainlist blacklisted-domain-%s\n' % proxy_setting)
		f.write('	 urllist	blacklisted-url-%s\n' % proxy_setting)
		f.write('}\n\n')
		f.write('dest whitelist-%s {\n' % proxy_setting)
		f.write('	 domainlist whitelisted-domain-%s\n' % proxy_setting)
		f.write('	 urllist	whitelisted-url-%s\n' % proxy_setting)
		f.write('}\n\n')
		touchfnlist.extend( ['blacklisted-domain-%s' % proxy_setting,
							 'blacklisted-url-%s' % proxy_setting,
							 'whitelisted-domain-%s' % proxy_setting,
							 'whitelisted-url-%s' % proxy_setting,
							 ] )

	# disable the domainlist/urllist within the temporary config file - processing the global blacklists
	# may take several seconds (depending on their size). The entry is reenabled when copied to target
	# config directory.
	f.write('dest global-blacklist {\n')
	if not 'proxy/filter/global/blacklists/domains' in changes:
		f.write(TXT_GLOBAL_BLACKLIST_COMMENT)
	f.write(' 	 domainlist %s-domains\n' % (FN_GLOBAL_BLACKLIST_PREFIX,))
	if not 'proxy/filter/global/blacklists/urls' in changes:
		f.write(TXT_GLOBAL_BLACKLIST_COMMENT)
	f.write(' 	 urllist    %s-urls\n' % (FN_GLOBAL_BLACKLIST_PREFIX,))
	f.write('}\n\n')

	f.write('acl {\n')
	for room in roomlist:
		f.write('	 %s {\n' % quote(room))
		f.write('		 pass none\n')
		f.write('		 redirect %s\n' % default_redirect)
		f.write('	 }\n\n')

	forced_blacklist = ''
	normal_blacklist = '!global-blacklist '
	if configRegistry.is_true(UCR_FORCED_GLOBAL_BLACKLIST, False):
		forced_blacklist = '!global-blacklist '
		normal_blacklist = ''

	RULES = {
		'whitelist-blacklist-pass':
			'%swhitelist-%%(username)s !blacklist-%%(username)s %sall\n' % (forced_blacklist, normal_blacklist),
		'whitelist-block':
			'%swhitelist-%%(username)s none\n' % (forced_blacklist,),
		'blacklist-pass':
			'!blacklist-%(username)s !global-blacklist all\n',
		}

	for (username, rooms, ) in roomRule.items():
		for room in rooms:
			if username in roomRules:
				filtertype = configRegistry.get('proxy/filter/setting-user/%s/filtertype' % (username, ), 'whitelist-blacklist-pass')
				quoted_username = quote(username) + '-user'
			elif username in proxy_settinglist:
				filtertype = configRegistry.get('proxy/filter/setting/%s/filtertype' % (username, ), 'whitelist-blacklist-pass')
				quoted_username = quote(username)
			else:
				continue
			if filtertype in RULES:
				f.write('	room-%s {\n' % (quote(room), ))
				f.write('		pass %s\n' % (RULES[filtertype] % {'username': quoted_username, },))
				f.write('		redirect %s\n' % default_redirect)
				f.write('	}\n')

	# acl usergroup
	for (priority, usergroupname, proxy_setting, ) in reversed(sorted(usergroupSetting)):
		filtertype = configRegistry.get('proxy/filter/setting/%s/filtertype' % proxy_setting, 'whitelist-blacklist-pass')
		if filtertype == 'whitelist-blacklist-pass':
			f.write('	 usergroup-%s {\n' % quote(usergroupname))
			f.write('		 pass %swhitelist-%s !blacklist-%s %sall\n' % (forced_blacklist, quote(proxy_setting), quote(proxy_setting), normal_blacklist))
			f.write('		 redirect %s\n' % default_redirect)
			f.write('	 }\n\n')
		elif filtertype == 'whitelist-block':
			f.write('	 usergroup-%s {\n' % quote(usergroupname))
			f.write('		 pass %swhitelist-%s none\n' % (forced_blacklist, quote(proxy_setting),))
			f.write('		 redirect %s\n' % (default_redirect,))
			f.write('	 }\n\n')
		elif filtertype == 'blacklist-pass':
			f.write('	 usergroup-%s {\n' % quote(usergroupname))
			f.write('		 pass !global-blacklist !blacklist-%s all\n' % (quote(proxy_setting),))
			f.write('		 redirect %s\n' % (default_redirect,))
			f.write('	 }\n\n')

	f.write('	 default {\n')
	f.write('		  pass %swhitelist !blacklist %sall\n' % (forced_blacklist, normal_blacklist))
	f.write('		  redirect %s\n' % (default_redirect,))
	f.write('	 }\n')
	f.write('}\n')

	f.close()

	# NOTE: touch all referenced database files to prevent squidguard
	#       from shutting down due to missing files
	for fn in touchfnlist:
		tmp = open( os.path.join(DIR_TEMP, fn), 'a+')


def checkGlobalBlacklist(configRegistry, DIR_DATA, changes):
	for listtype in ('domains', 'urls'):
		dst_fn = os.path.join(DIR_DATA, '%s-%s' % (FN_GLOBAL_BLACKLIST_PREFIX, listtype))
		if not 'proxy/filter/global/blacklists/%s' % (listtype,) in changes:
			if not os.path.exists(dst_fn):
				# the database file does not exist in final data directory, so a recreation is triggered
				changes['proxy/filter/global/blacklists/%s' % (listtype,)] = ''


def writeGlobalBlacklist(configRegistry, DIR_TEMP, changes):
	for listtype in ('domains', 'urls'):
		dst_fn = os.path.join(DIR_TEMP, '%s-%s' % (FN_GLOBAL_BLACKLIST_PREFIX, listtype))
		# recreate the blacklist db file only if the corresponding UCR variable has been changed/set
		# larger blacklists take several seconds to be converted into a db file
		if not 'proxy/filter/global/blacklists/%s' % (listtype,) in changes:
			continue
		with open(dst_fn, 'w') as fout:
			for fn in set([name.strip() for name in configRegistry.get('proxy/filter/global/blacklists/%s' % (listtype,), '').split(' ') if name.strip()]):
				src_fn = os.path.join(DIR_DATA, fn)
				if os.path.exists(src_fn):
					# merge all given sub-blacklist files into one global blacklist file
					try:
						content = open(src_fn, 'r').read().strip()
					except (IOError, OSError) as ex:
						logerror('Cannot read %r: %s' % (src_fn, ex))
						continue
					fout.write(content)

def writeSettinglist(configRegistry, DIR_TEMP):
	proxy_settinglist = set()
	regex = re.compile('^proxy/filter/setting((?:-user)?)/([^/]+)/.*$')
	for key in configRegistry:
		match = regex.match(key)
		if match:
			proxy_settinglist.add(match.groups())
	for (userpart, proxy_setting, ) in proxy_settinglist:
		for filtertype in [ 'domain', 'url' ]:
			for itemtype in [ 'blacklisted', 'whitelisted' ]:
				filename='%s-%s-%s%s' % (itemtype, filtertype, quote(proxy_setting), userpart)
				dbfn = '%s/%s' % (DIR_TEMP, filename)
				f = open(dbfn, "w")
				for key in configRegistry:
					if key.startswith('proxy/filter/setting%s/%s/%s/%s/' % (userpart, proxy_setting, filtertype, itemtype)):
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

def writeBlackWhiteLists(configRegistry, DIR_TEMP):
	for filtertype in [ 'domain', 'url' ]:
		for itemtype in [ 'blacklisted', 'whitelisted' ]:
			filename='%s-%s' % (itemtype, filtertype)
			dbfn = '%s/%s' % (DIR_TEMP, filename)
			f = open(dbfn, "w")
			for key in configRegistry:
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

def writeUsergroupMemberLists(configRegistry, DIR_TEMP):
	domain=configRegistry['windows/domain']
	for key in configRegistry:
		if key.startswith('proxy/filter/usergroup/'):
			usergroupname=key.rsplit('/', 1)[1]
			filename='usergroup-%s' % quote(usergroupname)
			dbfn = '%s/%s' % (DIR_TEMP, filename)
			f = open(dbfn, "w")
			for memberUid in configRegistry[key].split(','):
				f.write('%s\n' % (memberUid) )
				f.write('%s\\%s\n' % (domain, memberUid) )
			f.close()

def finalizeConfig(fn_temp_config, DIR_TEMP, DIR_DATA):
	# create all db files
	subprocess.call(('squidGuard', '-c', fn_temp_config, '-C', 'all', ))
	# fix permissions
	subprocess.call(('chmod', '-R', 'a=,ug+rw',   DIR_TEMP, fn_temp_config, ))
	subprocess.call(('chown', '-R', 'root:proxy', DIR_TEMP, fn_temp_config, ))
	# fix squidguard config (replace DIR_TEMP with DIR_DATA)
	content = open( fn_temp_config, "r").read()
	content = content.replace('\ndbhome %s/\n' % DIR_TEMP, '\ndbhome %s/\n' % DIR_DATA)
	content = content.replace(TXT_GLOBAL_BLACKLIST_COMMENT, '')  # reenable global blacklist entries
	tempConfig = open(fn_temp_config, "w")
	tempConfig.write(content)
	tempConfig.close()

def moveConfig(fn_temp_config, fn_config, FN_CONFIG, DIR_TEMP, DIR_DATA):
	# move all files from DIR_TEMP to DIR_DATA (should be atomic)
	for fn in os.listdir(DIR_TEMP):
		if fn == FN_CONFIG:
			continue
		fnsrc = os.path.join(DIR_TEMP, fn)
		fndst = os.path.join(DIR_DATA, fn)
		move_file(fnsrc, fndst)
	# move fixed config file to /etc/squidguard
	move_file(fn_temp_config, fn_config)

def removeTempDirectory(DIR_TEMP):
	try:
		os.rmdir(DIR_TEMP)
	except Exception, e:
		logerror('cannot remove temp directory %s: Exception %s' % (DIR_TEMP, e))
		raise
