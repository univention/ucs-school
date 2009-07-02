#!/usr/bin/python2.4
# -*- coding: iso-8859-15 -*-
#
# Univention Management Console
#  module: Distribution Module
#
# Copyright (C) 2007 Univention GmbH
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

import univention.management.console as umc
import univention.management.console.categories as umcc
import univention.management.console.protocol as umcp
import univention.management.console.handlers as umch
import univention.management.console.dialog as umcd
import univention.management.console.tools as umct
import univention.admin.modules
import univention.admin.objects

import univention.debug as ud
import univention.config_registry
import univention.uldap

import notifier
import notifier.popen

import os, re, fnmatch, pickle, shutil, tempfile, time

import _revamp
import _types
import _schoolldap

DISTRIBUTION_DATA_PATH = '/var/lib/univention-management-console-distribution'
DISTRIBUTION_CMD = '/usr/lib/univention-management-console-distribution/umc-distribution'

_ = umc.Translation( 'univention.management.console.handlers.distribution' ).translate

icon = 'distribution/module'
short_description = _( 'Data Distribution' )
long_description = _( 'Teaching Material Distribution' )
categories = [ 'all' ]

command_description = {
	'distribution/project/search': umch.command(
		short_description = _( 'Search Distribution Projects' ),
		long_description = _( 'Search Distribution Projects' ),
		method = 'distribution_project_search',
		values = { 'key' : _types.searchkey,
				   'filter' : _types.sfilter,
				   'ou': _types.ou,
				   },
		startup = True,
		priority = 90
	),
	'distribution/project/distribute': umch.command(
		short_description = _( 'distribute teaching material' ),
		long_description = _( 'distribute teaching material' ),
		method = 'distribution_project_distribute',
		values = {  'ou': _types.ou,
					'description': _types.description,
					'projectname': _types.projectname,
					'groupdn': _types.groupdn,
					'userdnlist': _types.userdnlist,
					'deadline': _types.deadline,
					'fileupload': _types.fileupload,
					},
		priority = 80
	),
	'distribution/project/show': umch.command(
		short_description = _( 'show selected project' ),
		long_description = _( 'show selected project' ),
		method = 'distribution_project_show',
		values = {  'projectname': _types.projectname,
					},
		priority = 80
	),
	'distribution/project/collect': umch.command(
		short_description = _( 'collect teaching material' ),
		long_description = _( 'collect teaching material' ),
		method = 'distribution_project_collect',
		values = {  'projectname': _types.projectname,
					},
		priority = 80
	),
}


import inspect
def debugmsg( component, level, msg ):
	info = inspect.getframeinfo(inspect.currentframe().f_back)[0:3]
	printInfo = []
	if len(info[0])>28:
		printInfo.append('...'+info[0][-25:])
	else:
		printInfo.append(info[0])
	printInfo.extend(info[1:3])
	ud.debug(component, level, "%s:%s: %s" % (printInfo[0], printInfo[1], msg))


class handler( umch.simpleHandler, _revamp.Web  ):
	def __init__( self ):
		global command_description
		umch.simpleHandler.__init__( self, command_description )
		_revamp.Web.__init__( self )

		try:
			if not os.path.exists( DISTRIBUTION_DATA_PATH ):
				os.makedirs( DISTRIBUTION_DATA_PATH, 0700 )
		except:
			debugmsg( ud.ADMIN, ud.ERROR, 'error occured while creating %s' % DISTRIBUTION_DATA_PATH )
		try:
			os.chmod( DISTRIBUTION_DATA_PATH, 0700 )
			os.chown( DISTRIBUTION_DATA_PATH, 0, 0 )
		except:
			debugmsg( ud.ADMIN, ud.ERROR, 'error occured while fixing permissions of %s' % DISTRIBUTION_DATA_PATH )


		# generate config objects
		self.configRegistry = univention.config_registry.ConfigRegistry()
		self.configRegistry.load()

		self.ldap_anon = _schoolldap.SchoolLDAPConnection()
		self.ldap_master = _schoolldap.SchoolLDAPConnection( ldapserver = self.configRegistry['ldap/master'] )

		debugmsg( ud.ADMIN, ud.INFO, 'availableOU=%s' % self.ldap_anon.availableOU )

##################################################

	def _generate_grouplist ( self, sorted_list = False ):
		grouplist = []

		groupresult = univention.admin.modules.lookup( self.ldap_anon.groupmodule, self.ldap_anon.co, self.ldap_anon.lo,
													   scope = 'sub', superordinate = None,
													   base = self.ldap_anon.searchbaseExtGroups, filter = None)
		for gr in groupresult:
			grouplist.append( { 'name': gr['name'],
								'dn': gr.dn } )
		if sorted_list:
			grouplist = sorted( grouplist, cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'name' ] )

		return grouplist

##################################################

	def _get_user( self, uid ):
	#	try:
		userresult = univention.admin.modules.lookup( self.ldap_anon.usermodule, self.ldap_anon.co, self.ldap_anon.lo,
													  scope = 'sub', superordinate = None,
													  base = self.configRegistry['ldap/base'], filter = ('uid=%s' % uid) )
		if userresult and userresult[0]:
			user = userresult[0]
			user.open()
			return user
#		except:
		debugmsg( ud.ADMIN, ud.ERROR, '_get_user: error while searching user object of uid=%s' % uid )

		debugmsg( ud.ADMIN, ud.INFO, '_get_user: unable to find user object of uid=%s' % uid )
		return None

##################################################


	def _create_dir( self, targetdir, homedir=None, permissions=0700, owner=0, group=0 ):
		# does target dir already exist?
		if not os.path.exists( targetdir ):
			# create targetdir
			os.makedirs( targetdir, permissions )

			# if homedir is not set, then only chown target dir
			if homedir:
				tmpdir = homedir
				targetdir = '/%s' % targetdir.strip('/')
				if len(targetdir[ len(homedir) : ].strip('/')) > 0:
					for dirpart in targetdir[ len(homedir) : ].strip('/').split('/'):
						tmpdir = os.path.join( tmpdir, dirpart )
						os.chown( tmpdir, owner, group )
				os.chown( homedir, owner, group )

		# chown target dir
		if os.path.exists( targetdir ):
			os.chown( targetdir, owner, group )
		else:
			debugmsg( ud.ADMIN, ud.ERROR, '%s does not exist - creation failed' % (targetdir) )

##################################################

	def distribution_project_search( self, umcobject ):
		debugmsg( ud.ADMIN, ud.INFO, 'distribution_search: incomplete=%s options=%s' % (umcobject.incomplete, umcobject.options ) )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		projectlist = []

		if not umcobject.incomplete:
			fn_projectlist = os.listdir( DISTRIBUTION_DATA_PATH )
			debugmsg( ud.ADMIN, ud.INFO, 'distribution_search: WALK = %s' % fn_projectlist )
			for fn_project in fn_projectlist:
				if os.path.isfile( os.path.join(DISTRIBUTION_DATA_PATH, fn_project) ):
					fd_project = open( os.path.join(DISTRIBUTION_DATA_PATH, fn_project), 'r' )
					project = pickle.load( fd_project )
					fd_project.close()

					skey = umcobject.options.get('key','name')
					sfilter = umcobject.options.get('filter','*')

					if fnmatch.fnmatch( project[skey], sfilter ):
						projectlist.append(project)

			projectlist = sorted( projectlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ), key = lambda x: x[ 'name' ] )

		self.finished( umcobject.id(), { 'availableOU': self.ldap_anon.availableOU,
									  'projectlist': projectlist,
									  } )

##################################################

	def distribution_project_distribute( self, umcobject ):
		debugmsg( ud.ADMIN, ud.INFO, 'distribution_distribute: incomplete=%s options=%s' % ( umcobject.incomplete, umcobject.options ) )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		try:
			msg = []
			cmdexitcode = None

			groupdn = umcobject.options.get('groupdn')
			userfilter = ''

			self.ldap_anon.switch_ou( umcobject.options.get('ou', self.ldap_anon.availableOU[0]) )
			grouplist = self._generate_grouplist( sorted_list = True )

			if not groupdn and grouplist:
				groupdn = grouplist[0]['dn']

			groupresult = univention.admin.modules.lookup( self.ldap_anon.groupmodule, self.ldap_anon.co, self.ldap_anon.lo,
														   scope = 'sub', superordinate = None, base = groupdn, filter = '')
			if groupresult and groupresult[0]:
				grp = groupresult[0]
				grp.open()
				debugmsg( ud.ADMIN, ud.INFO, 'group members=%s' % grp['users'] )
				for user in grp['users']:
					userfilter += '(%s)' % user.split(',', 1)[0]
				if userfilter:
					userfilter = '(|%s)' % userfilter
				debugmsg( ud.ADMIN, ud.INFO, 'userfilter = %s' % userfilter )

			project = { 'name': umcobject.options.get('projectname',''),
						'description': umcobject.options.get('description',''),
						'cachedir': None,
						'files': [],
						'starttime': None,
						'deadline': None,
						'atjob': None,
						'collectFiles': True,
						'sender': {},
						'sender_uid': None,
						'recipients': [],
						'recipients_dn': [],
						}

			# test if files have been uploaded
			if not umcobject.options.get('fileupload',[]) and umcobject.options.get('complete','0') == '1':
				umcobject.options['complete'] = '0'
				msg.append( _('No files have been uploaded!') )
				debugmsg( ud.ADMIN, ud.WARN, 'no files have been uploaded')

			# test if projectname is already in use
			fn_project = os.path.join( DISTRIBUTION_DATA_PATH, project['name'] )
			if os.path.exists( fn_project )	and umcobject.options.get('complete','0') == '1':
				umcobject.options['complete'] = '0'
				msg.append( _('projectname "%(projectname)s" is already in use!') % { 'projectname': project['name'] } )
				debugmsg( ud.ADMIN, ud.WARN, 'project name "%s" already in use' % project['name'])

			if umcobject.options.get('complete','0') == '1':
				debugmsg( ud.ADMIN, ud.INFO, 'project "%s" is complete' % project['name'])

				deadline_str = umcobject.options.get('deadline', '')
				if deadline_str:
					deadline_struct = time.strptime( deadline_str.strip(), _('%m/%d/%Y %H:%M') )
					deadline_time = time.mktime( deadline_struct )
					project['deadline'] = deadline_time
				files = []
				for fileitem in umcobject.options.get('fileupload',[]):
					files.append( [ fileitem['filename'], fileitem['tmpfname'] ] )

				project['sender_uid'] = self._username
				project['recipients_dn'] = umcobject.options.get('userdnlist', [])
				project['files'] = umcobject.options.get('fileupload',[])

				# save user info
				fd_project = open(fn_project, 'w')
				pickle.dump( project, fd_project )
				fd_project.close()

				debugmsg( ud.ADMIN, ud.INFO, 'project "%s" has been saved' % project['name'])

				cmdexitcode = 'success'
			else:
				project['sender']['obj'] = self._get_user( self._username )

			cmddata = { 'availableOU': self.ldap_anon.availableOU,
						'grouplist': grouplist,
						'userfilter': userfilter,
						'msg': msg,
						'cmdexitcode': cmdexitcode,
						'project': project,
						}

			if cmddata['cmdexitcode'] == 'success':
				cmd = '%s --init %s' % (DISTRIBUTION_CMD, os.path.join(DISTRIBUTION_DATA_PATH, project['name']))
				debugmsg( ud.ADMIN, ud.INFO, 'calling "%s"' % cmd )
				proc = notifier.popen.RunIt( cmd, stderr = True )
				cb = notifier.Callback( self._distribution_project_distribute_return, umcobject, cmddata )
				proc.signal_connect( 'finished', cb )
				proc.start()
			else:
				self.finished( umcobject.id(), cmddata )
		except Exception, e:
			debugmsg( ud.ADMIN, ud.ERROR, 'EXCEPTION2: %s' % str(e))

#####

	def _distribution_project_distribute_return( self, pid, status, stdout, stderr, umcobject, cmddata ):
		if status != 0:
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_distribute_return: umc-distribute command returned exitcode %s' % status )
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_distribute_return: umc-distribute command returned (stdout):\n %s' % stdout )
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_distribute_return: umc-distribute command returned (stderr):\n %s' % stderr )
			cmddata['msg'].append( _('Error occurred while distributing files (status=%s)') % status )
			cmddata['cmdexitcode'] = 'failure'

		self.finished( umcobject.id(), cmddata )

##################################################

	def distribution_project_show( self, umcobject ):
		debugmsg( ud.ADMIN, ud.INFO, 'distribution_collect: incomplete=%s options=%s' % ( umcobject.incomplete, umcobject.options ) )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		project = None
		report = ''

		projectname = umcobject.options.get('projectname', None)
		if not projectname:
			debugmsg( ud.ADMIN, ud.ERROR, 'no projectname given' )
			report = _('no projectname given')
		else:
			if not os.path.isfile( os.path.join(DISTRIBUTION_DATA_PATH, projectname) ):
				debugmsg( ud.ADMIN, ud.ERROR, 'project "%(projectname)s": file %(fn)s does not exist' % { 'projectname': projectname, 'fn': os.path.join(DISTRIBUTION_DATA_PATH, projectname)  } )
				report = _('project "%(projectname)s": file %(fn)s does not exist' ) % { 'projectname': projectname, 'fn': os.path.join(DISTRIBUTION_DATA_PATH, projectname)  }
			else:
				fd_project = open( os.path.join(DISTRIBUTION_DATA_PATH, projectname), 'r' )
				project = pickle.load( fd_project )
				fd_project.close()

		self.finished( umcobject.id(), { 'availableOU': self.ldap_anon.availableOU,
										 'project': project,
										 }, report = report, success = (len(report) == 0) )


##################################################

	def distribution_project_collect( self, umcobject ):
		debugmsg( ud.ADMIN, ud.INFO, 'distribution_collect: incomplete=%s options=%s' % ( umcobject.incomplete, umcobject.options ) )
		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)

		project = None
		report = ''

		projectname = umcobject.options.get('projectname', None)
		if not projectname:
			debugmsg( ud.ADMIN, ud.ERROR, 'no projectname given' )
			report = _('no projectname given')
		else:
			fn_project = os.path.join(DISTRIBUTION_DATA_PATH, projectname)
			if not os.path.isfile( fn_project ):
				debugmsg( ud.ADMIN, ud.ERROR, 'project "%(projectname)s": file %(fn)s does not exist' % ( projectname, fn_project ) )
				report = _('project "%(projectname)s": file %(fn)s does not exist' ) % { 'projectname': projectname, 'fn': fn_project  }
			else:
				fd_project = open( fn_project, 'r' )
				project = pickle.load( fd_project )
				fd_project.close()

		if report:
			self.finished( umcobject.id(), { 'availableOU': self.ldap_anon.availableOU,
											 'project': project,
											 }, report = report, success = False )
		else:
			cmddata = { 'msg': [],
						'cmdexitcode': 'success',
						'project': project }

			cmd = '%s --collect %s\n' % (DISTRIBUTION_CMD, os.path.join(DISTRIBUTION_DATA_PATH, fn_project))
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd = "%s"' % cmd )
			proc = notifier.popen.RunIt( cmd, stderr = True )
			cb = notifier.Callback( self._distribution_project_collect_return, umcobject, cmddata )
			proc.signal_connect( 'finished', cb )
			proc.start()

	def _distribution_project_collect_return( self, pid, status, stdout, stderr, umcobject, cmddata ):
		if status != 0:
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd umc-distribution-collect returned exitcode %s' % status )
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd umc-distribution-collect returned (stdout):\n %s' % '\n'.join(stdout) )
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd umc-distribution-collect returned (stderr):\n %s' % '\n'.join(stderr) )
			cmddata['msg'].append( _('An error occurred while collecting data (exitcode: %s)') % str(status) )
			cmddata['cmdexitcode'] = 'failure'
		cmddata['msg'].extend( stdout )

		if cmddata['project']['atjob'] == None:
			self.finished( umcobject.id(), cmddata )
		else:
			cmd = '/usr/bin/atrm %s' % cmddata['project']['atjob']
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd = "%s"' % cmd )
			proc = notifier.popen.RunIt( cmd, stderr = True )
			cb = notifier.Callback( self._distribution_project_collect_return2, umcobject, cmddata )
			proc.signal_connect( 'finished', cb )
			proc.start()

	def _distribution_project_collect_return2( self, pid, status, stdout, stderr, umcobject, cmddata ):
		if status != 0:
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return2: cmd atrm returned exitcode %s' % status )
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return2: cmd atrm returned (stdout):\n %s' % '\n'.join(stdout) )
			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return2: cmd atrm returned (stderr):\n %s' % '\n'.join(stderr) )
			cmddata['msg'].append( _('An error occurred while removing automatic deadline (exitcode: %s)') % str(status) )
			cmddata['cmdexitcode'] = 'failure'

		self.finished( umcobject.id(), cmddata )
