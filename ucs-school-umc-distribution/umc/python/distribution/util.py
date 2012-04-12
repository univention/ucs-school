#!/usr/bin/python2.6
# -*- coding: iso-8859-15 -*-
#
# Univention Management Console
#  module: Distribution Module
#
# Copyright 2007-2012 Univention GmbH
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

from univention.management.console.config import ucr

from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
import univention.lib.atjobs as atjobs

#import notifier
#import notifier.popen

import os
import shutil
import json

import time

import unicodedata
import string
import re

_ = Translation( 'ucs-school-umc-distribution' ).translate

# projectname = umc.String( _( 'Project Name' ), regex = '^[A-Za-zöäüÖÄÜß0-9_\.\+\-]+$' )
# description = umc.String( _( 'Description' ), required = False )
# groupdn = umc.String( _( 'Group DN' ) )
# userdnlist = umc.ObjectDNList( _( 'Select Attendees:' ) )
# # '^[ ]*(20|21|22|23|[01]\d):[0-5]\d (30|31|[012]\d)\.(10|11|12|0\d)\.20\d\d[ ]*$'
# deadline = umc.String( _( 'Deadline (e.g. 03/24/2008 08:05)' ), required = False, regex = _('^[ ]*(10|11|12|0\d)/(30|31|[012]\d)/20\d\d (20|21|22|23|[01]\d):[0-5]\d[ ]*$') )
# fileupload = umc.FileUploader( _( 'Upload Files' ), required = True )

DISTRIBUTION_CMD = '/usr/lib/ucs-school-umc-distribution/umc-distribution'
DISTRIBUTION_DATA_PATH = ucr.get('ucsschool/datadistribution/cache', '/var/lib/ucs-school-umc-distribution')
POSTFIX_DATADIR_SENDER = ucr.get('ucsschool/datadistribution/datadir/sender', 'Unterrichtsmaterial')
POSTFIX_DATADIR_RECIPIENT = ucr.get('ucsschool/datadistribution/datadir/recipient', 'Unterrichtsmaterial')

class _Dict(object):
	'''Custom dict-like class. The initial set of keyword arguments is stored
	in an internal dict. Entries of this intial set can be accessed directly
	on the object (myDict.myentry = ...).'''

	def __init__(self, **initDict):
		object.__setattr__(self, '_dict', initDict)

	# overwrite __setattr__ such that, e.g., project.cachedir can be called directly
	def __setattr__(self, key, value):
		_dict = object.__getattribute__(self, '_dict')
		if key in _dict:
			# if the key is in the internal dict, update its value
			_dict[key] = value
		object.__setattr__(self, key, value)

	# overwrite __getattribute__ such that, e.g., project.cachedir can be called directly
	def __getattribute__(self, key):
		_dict = object.__getattribute__(self, '_dict')
		if key in _dict:
			# if the key is in the internal dict, return its value
			return _dict[key]
		return object.__getattribute__(self, key)

	def update(self, props):
		'''Update internal dict with the dict given as parameter.'''
		# copy entries from the given dict over to the project properties
		_dict = self.dict
		for k, v in props.iteritems():
			if k in _dict:
				_dict[k] = v

	@property
	def dict(self):
		'''The internal dict.'''
		return self._dict

class _DictEncoder(json.JSONEncoder):
	'''A custom JSONEncoder class that can encode _Dict objects.'''
	def default(self, obj):
		if isinstance(obj, _Dict):
			return obj.dict
		return json.JSONEncoder.default(self, obj)

def jsonEncode(val):
	'''Encode to JSON using the custom _Dict encoder.'''
	return _DictEncoder(indent = 2).encode(val)

def jsonDecode(val):
	'''Decode a JSON string and replace dict types with _Dict.'''
	return json.loads(val, object_hook = lambda x: _Dict(**x))

class User(_Dict):
	def __init__(self, *args, **_props):
		# init empty project dict
		_Dict.__init__(self,
			unixhome = '',
			username = '',
			uidNumber = '',
			gidNumber = '',
			firstname = '',
			lastname = '',
			dn = ''
		)

		# update specified entries
		if len(args):
			self.update(args[0])
		else:
			self.update(_props)

	# shortcut :)
	@property
	def homedir(self):
		return self.unixhome

class Project(_Dict):
	def __init__(self, *args, **_props):
		# init empty project dict
		_Dict.__init__(self,
			name = None,
			description = None,
#			cachedir = None,
			files = [],
			starttime = None,  # seconds
			deadline = None,  # seconds
			atJobNumDistribute = None,  # int
			atJobNumCollect = None,  # int
#			collectFiles = True,
#			keepProject = False,
			sender = None,  # User
#			sender_uid = None,
			recipients = [],  # [User, ...]
#			recipients_dn = [],
		)

		# update specified entries
		if len(args):
			self.update(args[0])
		else:
			self.update(_props)

	@property
	def projectfile(self):
		'''The absolute project path to the project file.'''
		return os.path.join( DISTRIBUTION_DATA_PATH, self.name )

	@property
	def cachedir(self):
		'''The absolute path of the project cache directory.'''
		return os.path.join( DISTRIBUTION_DATA_PATH, '%s.data' % self.name )

	@property
	def sender_projectdir(self):
		'''The absolute path of the project directory in the senders home.'''
		if self.sender and self.sender.homedir:
			return os.path.join( self.sender.homedir, POSTFIX_DATADIR_SENDER, self.name )
		return None

	@property
	def atJobDistribute(self):
		return atjobs.load(self.atJobNumDistribute)

	@property
	def atJobCollect(self):
		return atjobs.load(self.atJobNumCollect)

	def user_projectdir(self, user):
		'''Return the absolute path of the project dir for the specified user.'''
		return os.path.join( user.homedir, POSTFIX_DATADIR_RECIPIENT, self.name )

	@property
	def isDistributed(self):
		'''True if files have already been distributed.'''
		# distributed files can still be found in the internal property 'files',
		# however, upon distribution they are removed from the cache directory;
		# thus, if one of the specified files does not exist, the project has
		# already been distributed
		files = [ ifn for ifn in self.files if os.path.exists(os.path.join(self.cachedir, ifn)) ]
		return len(files) != len(self.files)

	def validate(self):
		'''Validate the project data. In case of any errors with the data,
		a ValueError with a proper error message is raised.'''
		if not (isinstance(self.name, basestring) and self.name):
			raise ValueError(_('The given project directory name must be non-empty.'))
		if self.name.find('/') >= 0:
			raise ValueError(_('The specified project directory may not contain the character "/"'))
		if not (isinstance(self.description, basestring) and self.description):
			raise ValueError(_('The given project description must be non-empty.'))
		if not (isinstance(self.files, list)): # and self.files):
			raise ValueError(_('At least one file must be specified.'))
		if not (isinstance(self.recipients, list)): # and self.recipients):
			raise ValueError(_('At least one recipient must be specified.'))
		if not self.sender or not self.sender.username or not self.sender.homedir:
			raise ValueError(_('A valid project owner needs to be specified.'))
		#TODO: the following checks are necessary to make sure that the project name
		#      has not been used so far:
		# sender_projectdir -> does not exist yet?
		# recipients projectdir -> does not exist yet?
		# date in the future?

	def isNameInUse(self):
		'''Verifies whether the given project name is already in use.'''
		# check for a project with given name
		if os.path.exists(self.projectfile):
			return True

		# check whether a project directory with the given name exists in the
		# recipients' home directories
		l = [ iuser for iuser in self.recipients if os.path.exists(self.user_projectdir(iuser)) ]
		return len(l) > 0

	def save(self):
		'''Save project data to disk and create job. In case of any errors, an IOError is raised.'''
		try:
			# update at-jobs
			self._unregister_at_jobs()
			self._register_at_jobs()

			# save the project file
			fd = open(self.projectfile, 'w')
			fd.write(jsonEncode(self))
			fd.close()

			# create cache directory
			self._createCacheDir()
		except IOError, e:
			raise IOError(_('Could not save project file: %s (%s)') % (self.projectfile, str(e)))

	def _createCacheDir(self):
		'''Create cache directory.'''
		# create project cache directory
		MODULE.info( 'creating project cache dir: %s' % self.cachedir )
		_create_dir( self.cachedir, owner=0, group=0 )

	def _createProjectDir(self):
		'''Create project directory in the sender's home.'''

		# make sure that the sender homedir exists
		if self.sender and self.sender.homedir and not os.path.exists( self.sender.homedir ):
			MODULE.warn( 'recreate homedir: uidNumber=%s  gidNumber=%s' % (self.sender.uidNumber, self.sender.gidNumber) )
			_create_dir( self.sender.homedir, owner=self.sender.uidNumber, group=self.sender.gidNumber )

		# create sender project directory
		if self.sender_projectdir:
			MODULE.info( 'creating project dir in sender\'s home: %s' % self.sender_projectdir )
			_create_dir( self.sender_projectdir, homedir = self.sender.homedir, owner = self.sender.uidNumber, group = self.sender.gidNumber )
		else:
			MODULE.error( 'ERROR: Sender information is not specified, cannot create project dir in the sender\'s home!' )

	def _register_at_jobs(self):
		'''Registers at-jobs for distributing and collecting files. Files are distributed
		directly of no start time is explicitely specified.'''

		# register the starting job
		# if no start time is given, project will be distributed immediately
		# make sure that the startime, if given, lies in the future
		if not self.starttime or self.starttime > time.time():
			MODULE.info( 'register at-jobs: starttime = %s' % time.ctime( self.starttime ) )
			cmd = '%s --distribute %s' % (DISTRIBUTION_CMD, self.projectfile)
			print 'register at-jobs: starttime = %s  cmd = %s' % (time.ctime( self.starttime ), cmd) 
			atJob = atjobs.add(cmd, self.starttime)
			if atJob and self.starttime:
				self.atJobNumDistribute = atJob.nr
			if not atJob:
				MODULE.warn( 'registration of at-job failed' )
				print 'registration of at-job failed'

		# register the collecting job, only if a deadline is given
		if self.deadline and self.deadline > time.time():
			MODULE.info( 'register at-jobs: deadline = %s' % time.ctime( self.deadline ) )
			print 'register at-jobs: deadline = %s' % time.ctime( self.deadline ) 
			cmd = '%s --collect %s' % (DISTRIBUTION_CMD, self.projectfile)
			atJob = atjobs.add(cmd, self.deadline)
			if atJob:
				self.atJobNumCollect = atJob.nr
			else:
				MODULE.warn( 'registration of at-job failed' )
				print 'registration of at-job failed' 

	def _unregister_at_jobs(self):
		# remove at-jobs
		for inr in [ self.atJobNumDistribute, self.atJobNumCollect ]:
			ijob = atjobs.load(inr)
			if ijob:
				ijob.rm()

	def distribute( self, usersFailed = None):
		'''Distribute the project data to all registrated receivers.'''

		usersFailed = usersFailed or []

		# determine which files shall be distributed
		# note: already distributed files will be removed from the cache directory,
		#       yet they are still kept in the internal list of files
		files = [ ifn for ifn in self.files if os.path.exists(os.path.join(self.cachedir, ifn)) ]

		if not files:
			# no files to distribute
			MODULE.info('No new files to distribute in project: %s' % self.name)
			return

		# make sure all necessary directories exist
		self._createProjectDir()

		# iterate over all recipients
		MODULE.info('Distributing project "%s" with files: %s' % (self.name, ", ".join(files)))
		for user in self.recipients + [ self.sender ]:
			# create user project directory
			MODULE.info( 'recipient: uid=%s' % user.username )
			_create_dir( self.user_projectdir(user), homedir = user.homedir, owner = user.uidNumber, group = user.gidNumber )

			# copy files from cache to recipient
			for fn in files:
				src = str( os.path.join( self.cachedir, fn ) )
				target = str( os.path.join( self.user_projectdir(user), fn ) )
				try:
					shutil.copyfile( src, target )
				except Exception, e:
					MODULE.error( 'failed to copy "%s" to "%s": %s' % (src, target, str(e)))
					usersFailed.append(user)
				try:
					os.chown( target, int(user.uidNumber), int(user.gidNumber) )
				except Exception, e:
					MODULE.error( 'failed to chown "%s": %s' % (target, str(e)))
					usersFailed.append(user)

		# remove cached files
		for fn in files:
			try:
				src = str(os.path.join(self.cachedir, fn))
				if os.path.exists(src):
					os.remove(src)
				else:
					MODULE.info( 'file has already been distributed: %s [%s]' % (src, e) )
			except Exception as e:
				MODULE.error( 'failed to remove file: %s [%s]' % (src, e) )

		return len(usersFailed) == 0

	def collect(self, dirsFailed = None):
		dirsFailed = dirsFailed or []

		# make sure all necessary directories exist
		self._createProjectDir()

		# collect data from all recipients
		for recipient in self.recipients:
			# guess a proper directory name (in case with " versionX" suffix)
			dirVersion = 1
			targetdir = os.path.join( self.sender_projectdir, recipient.username )
			while os.path.exists(targetdir):
				dirVersion += 1
				targetdir = os.path.join( self.sender_projectdir, '%s version%d' % (recipient.username, dirVersion) )
			MODULE.info('collecting data from "%s" to: %s' % (recipient.username, targetdir))

			# copy entire directory of the recipient
			srcdir = os.path.join( self.user_projectdir(recipient) )
			try:
				# copy dir
				shutil.copytree( srcdir, targetdir )

				# fix permission
				os.chown(targetdir, int(self.sender.uidNumber), int(self.sender.gidNumber))
				for root, dirs, files in os.walk(targetdir):
					for momo in dirs + files:
						os.chown(os.path.join(root, momo), int(self.sender.uidNumber), int(self.sender.gidNumber))

			except (OSError, ValueError) as ex:
				MODULE.warn('Copy failed: "%s" ->  "%s"' % (srcdir, targetdir))
				dirsFailed.append(srcdir)

		return len(dirsFailed) == 0

	def purge(self):
		'''Remove project's cache directory, project file, and at job registrations.'''
		if not self.projectfile or not os.path.exists( self.projectfile ):
			MODULE.error('cannot remove empty or non existing projectfile: %s' % self.projectfile)
			return

		self._unregister_at_jobs()

		# remove cachedir
		MODULE.info('trying to purge projectfile [%s] and cachedir [%s]' % (self.projectfile, self.cachedir))
		if self.cachedir and os.path.exists( self.cachedir ):
			try:
				shutil.rmtree( self.cachedir )
			except Exception, e:
				MODULE.error('failed to cleanup cache directory: %s [%s]' % (self.cachedir, str(e)))

		# remove projectfile
		try:
			os.remove( self.projectfile )
		except Exception, e:
			MODULE.error('cannot remove projectfile: %s [%s]' % (projectfile, str(e)))

	@staticmethod
	def load(projectfile):
		'''Load the given project file and create a new Project instance.'''
		project = None
		try:
			# load project dictionary from JSON file
			fd = open(os.path.join(DISTRIBUTION_DATA_PATH, projectfile), 'r' )
			tmpDict = jsonDecode(''.join(fd.readlines()))
			project = Project(tmpDict.dict)
			fd.close()

			# convert _Dict instances to User
			project.sender = User(project.sender.dict)
			project.recipients = [ User(i.dict) for i in project.recipients ]
		except IOError as e:
			MODULE.error('Could not open project file: %s [%s]' % (projectfile, str(e)))
			return None
		except ValueError as e:
			MODULE.error('Could not parse project file: %s [%s]' % (projectfile, str(e)))
			return None

		# make sure the filename matches the property 'name'
		project.name = os.path.basename(projectfile)
		return project

	@staticmethod
	def list():
		fn_projectlist = os.listdir( DISTRIBUTION_DATA_PATH )
		MODULE.info( 'distribution_search: WALK = %s' % fn_projectlist )
		projectlist = []
		for fn_project in fn_projectlist:
			# make sure the entry is a file
			fname = os.path.join(DISTRIBUTION_DATA_PATH, fn_project)
			if not os.path.isfile(fname):
				continue

			# load the project and add it to the result list
			project = Project.load(fname)
			if project:
				projectlist.append(project)

		# sort final result
		projectlist.sort( cmp = lambda x, y: cmp( x.name.lower(), y.name.lower()) )
		return projectlist

def initPaths():
	try:
		if not os.path.exists( DISTRIBUTION_DATA_PATH ):
			os.makedirs( DISTRIBUTION_DATA_PATH, 0700 )
	except:
		MODULE.error( 'error occured while creating %s' % DISTRIBUTION_DATA_PATH )
	try:
		os.chmod( DISTRIBUTION_DATA_PATH, 0700 )
		os.chown( DISTRIBUTION_DATA_PATH, 0, 0 )
	except:
		MODULE.error( 'error occured while fixing permissions of %s' % DISTRIBUTION_DATA_PATH )

def _create_dir( targetdir, homedir=None, permissions=0700, owner=0, group=0 ):
	# does target dir already exist?
	try:
		# parse strings
		owner = int(owner)
		group = int(group)

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
			MODULE.error( '%s does not exist - creation failed' % (targetdir) )
			return False
	except Exception, e:
		MODULE.error( 'failed to create/chown "%s": %s' % (targetdir, str(e)))
		return False

	# operation successful
	return True


########## OLD CODE ##############
#class handler( umch.simpleHandler, _revamp.Web  ):
#
##################################################
#
#
#	def distribution_project_distribute( self, umcobject ):
#		debugmsg( ud.ADMIN, ud.INFO, 'distribution_distribute: incomplete=%s options=%s' % ( umcobject.incomplete, umcobject.options ) )
#		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)
#
#		try:
#			msg = []
#			cmdexitcode = None
#
#			groupdn = umcobject.options.get('groupdn')
#			userfilter = ''
#
#			self.ldap_anon.switch_ou( umcobject.options.get('ou', self.ldap_anon.availableOU[0]) )
#			grouplist = self._generate_grouplist( sorted_list = True )
#
#			if not groupdn and grouplist:
#				groupdn = grouplist[0]['dn']
#
#			groupresult = univention.admin.modules.lookup( self.ldap_anon.groupmodule, self.ldap_anon.co, self.ldap_anon.lo,
#														   scope = 'sub', superordinate = None, base = groupdn, filter = '')
#			if groupresult and groupresult[0]:
#				grp = groupresult[0]
#				grp.open()
#				debugmsg( ud.ADMIN, ud.INFO, 'group members=%s' % grp['users'] )
#				for user in grp['users']:
#					userfilter += '(%s)' % user.split(',', 1)[0]
#				if userfilter:
#					userfilter = '(|%s)' % userfilter
#				debugmsg( ud.ADMIN, ud.INFO, 'userfilter = %s' % userfilter )
#
##			if umcobject.options.get('update','0') == '1' and umcobject.options.get('complete','0') == '1':
##				fn_project = os.path.join( DISTRIBUTION_DATA_PATH, umcobject.options.get('projectname','') )
##				if os.path.exists( fn_project ):
##					project = getProject(fn_project)
##				else:
##					umcobject.options['complete'] = '0'
##					msg.append( _('projectname "%(projectname)s" is already in use!') % { 'projectname': project['name'] } )
##					debugmsg( ud.ADMIN, ud.WARN, 'project name "%s" already in use' % project['name'])
##			else:
##				project = getProject ()
##				project['name'] = umcobject.options.get('projectname','')
##				project['description'] = umcobject.options.get('description','')
#
#			# test if files have been uploaded
#			if not umcobject.options.get('fileupload',[]) and umcobject.options.get('complete','0') == '1':
#				umcobject.options['complete'] = '0'
#				msg.append( _('No files have been uploaded!') )
#				debugmsg( ud.ADMIN, ud.WARN, 'no files have been uploaded')
#
##			# test if projectname is already in use
##			fn_project = os.path.join( DISTRIBUTION_DATA_PATH, project['name'] )
##			if os.path.exists( fn_project )	and umcobject.options.get('complete','0') == '1':
##				umcobject.options['complete'] = '0'
##				msg.append( _('projectname "%(projectname)s" is already in use!') % { 'projectname': project['name'] } )
##				debugmsg( ud.ADMIN, ud.WARN, 'project name "%s" already in use' % project['name'])
#
#			if umcobject.options.get('complete','0') == '1':
#				debugmsg( ud.ADMIN, ud.INFO, 'project "%s" is complete' % project['name'])
#
#				deadline_str = umcobject.options.get('deadline', '')
#				if deadline_str:
#					deadline_struct = time.strptime( deadline_str.strip(), _('%m/%d/%Y %H:%M') )
#					deadline_time = time.mktime( deadline_struct )
#					if deadline_time > time.time()+120:
#						project['deadline'] = deadline_time
#				files = []
#				for fileitem in umcobject.options.get('fileupload',[]):
#					files.append( [ fileitem['filename'], fileitem['tmpfname'] ] )
#
#				project['sender_uid'] = self._username
#				project['recipients_dn'] = umcobject.options.get('userdnlist', [])
#				project['files'] = umcobject.options.get('fileupload',[])
#
#				# save user info
#				saveProject(fn_project, project)
#
#				debugmsg( ud.ADMIN, ud.INFO, 'project "%s" has been saved' % project['name'])
#
#				cmdexitcode = 'success'
#			else:
#				project['sender']['obj'] = self._get_user( self._username )
#
#			cmddata = { 'availableOU': self.ldap_anon.availableOU,
#						'grouplist': grouplist,
#						'userfilter': userfilter,
#						'msg': msg,
#						'cmdexitcode': cmdexitcode,
#						'project': project,
#						}
#
#			if cmddata['cmdexitcode'] == 'success':
#				cmd = '%s --init --force %s' % (DISTRIBUTION_CMD, os.path.join(DISTRIBUTION_DATA_PATH, project['name']))
#				debugmsg( ud.ADMIN, ud.INFO, 'calling "%s"' % cmd )
#				proc = notifier.popen.RunIt( cmd, stderr = True )
#				cb = notifier.Callback( self._distribution_project_distribute_return, umcobject, cmddata )
#				proc.signal_connect( 'finished', cb )
#				proc.start()
#			else:
#				self.finished( umcobject.id(), cmddata )
#		except Exception, e:
#			debugmsg( ud.ADMIN, ud.ERROR, 'EXCEPTION2: %s' % str(e))
#
######
#
#	def _distribution_project_distribute_return( self, pid, status, stdout, stderr, umcobject, cmddata ):
#		if status != 0:
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_distribute_return: umc-distribute command returned exitcode %s' % status )
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_distribute_return: umc-distribute command returned (stdout):\n %s' % stdout )
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_distribute_return: umc-distribute command returned (stderr):\n %s' % stderr )
#			cmddata['msg'].append( _('Error occurred while distributing files (status=%s)') % status )
#			cmddata['cmdexitcode'] = 'failure'
#
#		self.finished( umcobject.id(), cmddata )
#
###################################################
#
#	def distribution_project_show( self, umcobject ):
#		debugmsg( ud.ADMIN, ud.INFO, 'distribution_collect: incomplete=%s options=%s' % ( umcobject.incomplete, umcobject.options ) )
#		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)
#
#		project = None
#		report = ''
#
#		projectname = umcobject.options.get('projectname', None)
#		if not projectname:
#			debugmsg( ud.ADMIN, ud.ERROR, 'no projectname given' )
#			report = _('no projectname given')
#		else:
#			if not os.path.isfile( os.path.join(DISTRIBUTION_DATA_PATH, projectname) ):
#				debugmsg( ud.ADMIN, ud.ERROR, 'project "%(projectname)s": file %(fn)s does not exist' % { 'projectname': projectname, 'fn': os.path.join(DISTRIBUTION_DATA_PATH, projectname)  } )
#				report = _('project "%(projectname)s": file %(fn)s does not exist' ) % { 'projectname': projectname, 'fn': os.path.join(DISTRIBUTION_DATA_PATH, projectname)  }
#			else:
#				project = getProject(os.path.join(DISTRIBUTION_DATA_PATH, projectname))
#
#		self.finished( umcobject.id(), { 'availableOU': self.ldap_anon.availableOU,
#										 'project': project,
#										 }, report = report, success = (len(report) == 0) )
#
#
###################################################
#
#	def distribution_project_collect( self, umcobject ):
#		debugmsg( ud.ADMIN, ud.INFO, 'distribution_collect: incomplete=%s options=%s' % ( umcobject.incomplete, umcobject.options ) )
#		self.ldap_anon.checkConnection(username = self._username, bindpw = self._password)
#
#		project = None
#		report = ''
#
#		projectname = umcobject.options.get('projectname', None)
#		if not projectname:
#			debugmsg( ud.ADMIN, ud.ERROR, 'no projectname given' )
#			report = _('no projectname given')
#		else:
#			fn_project = os.path.join(DISTRIBUTION_DATA_PATH, projectname)
#			if not os.path.isfile( fn_project ):
#				debugmsg( ud.ADMIN, ud.ERROR, 'project "%(projectname)s": file %(fn)s does not exist' % ( projectname, fn_project ) )
#				report = _('project "%(projectname)s": file %(fn)s does not exist' ) % { 'projectname': projectname, 'fn': fn_project  }
#			else:
#				project = getProject(fn_project)
#
#		if report:
#			self.finished( umcobject.id(), { 'availableOU': self.ldap_anon.availableOU,
#											 'project': project,
#											 }, report = report, success = False )
#		else:
#			cmddata = { 'msg': [],
#						'cmdexitcode': 'success',
#						'project': project }
#
#			cmd = '%s --collect --force %s\n' % (DISTRIBUTION_CMD, os.path.join(DISTRIBUTION_DATA_PATH, fn_project))
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd = "%s"' % cmd )
#			proc = notifier.popen.RunIt( cmd, stderr = True )
#			cb = notifier.Callback( self._distribution_project_collect_return, umcobject, cmddata )
#			proc.signal_connect( 'finished', cb )
#			proc.start()
#
#	def _distribution_project_collect_return( self, pid, status, stdout, stderr, umcobject, cmddata ):
#		if status != 0:
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd umc-distribution-collect returned exitcode %s' % status )
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd umc-distribution-collect returned (stdout):\n %s' % '\n'.join(stdout) )
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd umc-distribution-collect returned (stderr):\n %s' % '\n'.join(stderr) )
#			cmddata['msg'].append( _('An error occurred while collecting data (exitcode: %s)') % str(status) )
#			cmddata['cmdexitcode'] = 'failure'
#		cmddata['msg'].extend( stdout )
#
#		if cmddata['project']['atjob'] == None:
#			self.finished( umcobject.id(), cmddata )
#		else:
#			cmd = '/usr/bin/atrm %s' % cmddata['project']['atjob']
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return: cmd = "%s"' % cmd )
#			proc = notifier.popen.RunIt( cmd, stderr = True )
#			cb = notifier.Callback( self._distribution_project_collect_return2, umcobject, cmddata )
#			proc.signal_connect( 'finished', cb )
#			proc.start()
#
#	def _distribution_project_collect_return2( self, pid, status, stdout, stderr, umcobject, cmddata ):
#		if status != 0:
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return2: cmd atrm returned exitcode %s' % status )
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return2: cmd atrm returned (stdout):\n %s' % '\n'.join(stdout) )
#			debugmsg( ud.ADMIN, ud.ERROR, 'distribution_project_collect_return2: cmd atrm returned (stderr):\n %s' % '\n'.join(stderr) )
#			cmddata['msg'].append( _('An error occurred while removing automatic deadline (exitcode: %s)') % str(status) )
#			cmddata['cmdexitcode'] = 'failure'
#
#		self.finished( umcobject.id(), cmddata )
