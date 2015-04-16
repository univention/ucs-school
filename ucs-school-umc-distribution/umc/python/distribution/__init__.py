#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   
#
# Copyright 2012-2015 Univention GmbH
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

from univention.lib.i18n import Translation
from univention.management.console.modules import UMC_OptionTypeError, UMC_CommandError
from univention.management.console.modules.decorators import file_upload
from univention.management.console.log import MODULE

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions
import os
from datetime import datetime, timedelta

from ucsschool.lib.schoolldap import LDAP_Connection, SchoolBaseModule, Display

import util
import tempfile
import shutil

_ = Translation( 'ucs-school-umc-distribution' ).translate

class Instance( SchoolBaseModule ):
	def __init__( self ):
		SchoolBaseModule.__init__(self)
		self._tmpDir = None

	def init(self):
		SchoolBaseModule.init(self)
		# initiate paths for data distribution
		util.initPaths()

	def destroy(self):
		self._cleanTmpDir()

	def _cleanTmpDir(self):
		# clean up the temporary upload directory
		if self._tmpDir:
			MODULE.info('Clean up temporary directory: %s' % self._tmpDir)
			shutil.rmtree(self._tmpDir, ignore_errors=True)
			self._tmpDir = None

	@file_upload
	def upload(self, request):
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of dicts, but got: %s' % str(request.options) )

		for file in request.options:
			if not ('tmpfile' in file and 'filename' in file):
				raise UMC_OptionTypeError( 'Invalid upload data, got: %s' % str(file) )

			# create a temporary upload directory, if it does not already exist
			if not self._tmpDir:
				self._tmpDir = tempfile.mkdtemp(prefix='ucsschool-distribution-upload-')
				MODULE.info('Created temporary directory: %s' % self._tmpDir)

			filename = self.__workaround_filename_bug(file)
			destPath = os.path.join(self._tmpDir, filename)
			MODULE.info('Received file %r, saving it to %r' % (file['tmpfile'], destPath))
			shutil.move(file['tmpfile'], destPath)

		# done
		self.finished( request.id, None )

	def __workaround_filename_bug(self, file):
		### the following code block is a heuristic to support both: fixed and unfixed Bug #37716
		filename = file['filename']
		try:
			# The UMC-Webserver decodes filename in latin-1, need to revert
			filename = filename.encode('ISO8859-1')
		except UnicodeEncodeError:
			# we got non-latin characters, Bug #37716 is fixed and string contains e.g. '→'
			filename = file['filename'].encode('UTF-8')
		else:
			# the string contains at least no non-latin1 characters
			try:
				# try if the bytes could be UTF-8
				# can't fail if Bug #37716 is fixed
				filename.decode('UTF-8')
			except UnicodeDecodeError:
				filename = file['filename'].encode('UTF-8')  # Bug #37716 was fixed
		MODULE.info('Detected filename %r as %r' % (file['filename'], filename))
		### the code block can be removed and replaced by filename = file['filename'].encode('UTF-8') after Bug #37716
		return filename

	def checkfiles(self, request):
		'''Checks whether the given filename has already been uploaded:

		request.options: { 'filenames': [ '...', ... ], project: '...' }

		returns: {
			'filename': '...',
			'sessionDuplicate': True|False,
			'projectDuplicate': True|False,
			'distributed': True|False
		}
		'''

		if not 'filenames' in request.options or not 'project' in request.options:
			raise UMC_OptionTypeError( 'Expected dict with entries "filenames" and "project", but got: %s' % request.options )
		if not isinstance(request.options.get('filenames'), (tuple, list)):
			raise UMC_OptionTypeError( 'The entry "filenames" is expected to be an array, but got: %s' % request.options.get('filenames') )

		# load project
		project = None
		if request.options.get('project'):
			project = util.Project.load(request.options.get('project'))


		result = []
		for ifile in request.options.get('filenames'):
			ifile = ifile.encode('UTF-8')
			# check whether file has already been upload in this session
			iresult = dict(sessionDuplicate = False, projectDuplicate = False, distributed = False)
			iresult['filename'] = ifile
			iresult['sessionDuplicate'] = self._tmpDir != None and os.path.exists(os.path.join(self._tmpDir, ifile))

			# check whether the file exists in the specified project and whether
			# it has already been distributed
			if project:
				iresult['projectDuplicate'] = ifile in project.files
				iresult['distributed'] = ifile in project.files and not os.path.exists(os.path.join(project.cachedir, ifile))
			result.append(iresult)
		# done :)
		self.finished( request.id, result )

	def query( self, request ):
		MODULE.info( 'distribution.query: options: %s' % str( request.options ) )
		pattern = request.options.get('pattern', '').lower()
		filter = request.options.get('filter', 'private').lower()
		result = [ dict(
				# only show necessary information
				description = i.description,
				name = i.name,
				sender = i.sender.username,
				recipients = len(i.recipients),
				files = len(i.files),
				isDistributed = i.isDistributed
			) for i in util.Project.list()
			# match the pattern
			if (i.name.lower().find(pattern) >= 0 or i.description.lower().find(pattern) >= 0)
			# match also the category
			and (filter == 'all' or i.sender.dn == self._user_dn)
		]
		MODULE.info( 'distribution.query: results: %s' % str( result ) )
		self.finished( request.id, result )

	@LDAP_Connection()
	def _get_sender( self, request, ldap_user_read = None, ldap_position = None, search_base = None ):
		'''Return a User instance of the currently logged in user.'''
		sender = None
		try:
			# open UDM object
			userModule = udm_modules.get('users/user')
			obj = userModule.object(None, ldap_user_read, None, self._user_dn)
			obj.open()

			# create a new User object
			sender = util.User(obj.info)
			sender.dn = obj.dn
		except udm_exceptions.base as e:
			self.finished(request.id, None, _('Failed to load user information: %s') % e, False)
			MODULE.error('Could not find user DN: %s' % self._user_dn)
			raise UMC_CommandError( _('Could not authenticate user "%s"!') % self._user_dn )
		return sender

	@LDAP_Connection()
	def _save( self, request, doUpdate = True, ldap_user_read = None, ldap_position = None, search_base = None ):
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % (type(request.options),) )

		# try to open the UDM user object of the current user
		sender = self._get_sender(request)

		# try to create all specified projects
		result = []
		for ientry in request.options:
			iprops = ientry.get('object', {})
			try:
				# remove keys that may not be set from outside
				for k in ('atJobNumCollect', 'atJobNumDistribute'):
					iprops.pop(k, None)

				# transform filenames into bytestrings
				iprops['files'] = [f.encode('UTF-8') for f in iprops.get('files', [])]

				# load the project or create a new one
				project = None
				orgProject = None
				if doUpdate:
					# try to load the given project
					orgProject = util.Project.load(iprops.get('name', ''))
					if not orgProject:
						raise ValueError(_('The specified project does not exist: %s') % iprops['name'])

					# create a new project with the updated values
					project = util.Project(orgProject.dict)
					project.update(iprops)
				else:
					# create a new project
					project = util.Project(iprops)

				# make sure that the project owner himself is modifying the project
				if doUpdate and project.sender.dn != self._user_dn:
					raise IOError(_('The project can only be modified by the owner himself'))

				# handle time settings for distribution/collection of project files
				for jsuffix, jprop, jname in (('distribute', 'starttime', _('Project distribution')), ('collect', 'deadline', _('Project collection'))):
					if '%sType' % jsuffix in iprops:
						# check the distribution/collection type: manual/automat
						jtype = (iprops['%sType' % jsuffix]).lower()
						if jtype == 'automatic':
							try:
								# try to parse the given time parameters
								strtime = '%s %s' % (iprops['%sDate' % jsuffix], iprops['%sTime' % jsuffix])
								jdate = datetime.strptime(strtime, '%Y-%m-%d %H:%M')
								setattr(project, jprop, jdate)
							except ValueError as e:
								raise ValueError(_('Could not set date for: %s') % jname)

							# make sure the execution time lies sufficiently in the future
							if getattr(project, jprop) - datetime.now() < timedelta(minutes=1):
								raise ValueError(_('The specified time needs to lie in the future for: %s') % jname)
						else:
							# manual distribution/collection
							setattr(project, jprop, None)

				if project.starttime and project.deadline:
					# make sure distributing happens before collecting
					if project.deadline - project.starttime < timedelta(minutes=3):
						raise ValueError(_('Distributing the data needs to happen sufficiently long enough before collecting them'))

				if 'recipients' in iprops:
					# lookup the users in LDAP and save them to the project
					users = [ientry for ientry in [ util.openRecipients(idn, ldap_user_read, search_base) for idn in iprops.get('recipients', []) ] if ientry ]
					project.recipients = users
					MODULE.info('recipients: %s' % users)

				if not doUpdate:
					# set the sender (i.e., owner) of the project
					project.sender = sender

				# initiate project and validate its values
				project.validate()

				# make sure that there is no other project with the same directory name
				# if we add new projects
				if not doUpdate and project.isNameInUse():
					MODULE.error('The project name is already in use: %s' % (project.name))
					raise ValueError(_('The specified project directory name "%s" is already in use by a different project.') % (project.name))

				# try to save project to disk
				project.save()

				# move new files into project directory
				if self._tmpDir:
					for ifile in project.files:
						isrc = os.path.join(self._tmpDir, ifile)
						itarget = os.path.join(project.cachedir, ifile)
						if os.path.exists(isrc):
							# mv file to cachedir
							shutil.move( isrc, itarget )
							os.chown( itarget, 0, 0 )

				# remove files that have been marked for removal
				if doUpdate:
					for ifile in set(orgProject.files) - set(project.files):
						itarget = os.path.join(project.cachedir, ifile)
						try:
							os.remove(itarget)
						except OSError as e:
							pass

				# re-distribute the project in case it has already been distributed
				if doUpdate and project.isDistributed:
					usersFailed = []
					project.distribute(usersFailed)

					if usersFailed:
						# not all files could be distributed
						MODULE.info('Failed processing the following users: %s' % usersFailed)
						usersStr = ', '.join([ Display.user(i) for i in usersFailed ])
						raise IOError(_('The project could not distributed to the following users: %s') % usersStr)

				# everything ok
				result.append(dict(
					name = iprops.get('name'),
					success = True
				))
			except (ValueError, IOError, OSError) as e:
				# data not valid... create error info
				MODULE.info('data for project "%s" is not valid: %s' % (iprops.get('name'), e))
				result.append(dict(
					name = iprops.get('name'),
					success = False,
					details = str(e)
				))

				if not doUpdate:
					# remove eventually created project file and cache dir
					for ipath in (project.projectfile, project.cachedir):
						if os.path.basename(ipath) not in os.listdir(util.DISTRIBUTION_DATA_PATH):
							# no file / directory has been created yet
							continue
						try:
							MODULE.info('cleaning up... removing: %s' % ipath)
							shutil.rmtree(ipath)
						except (IOError, OSError) as e:
							pass

		if len(result) and reduce(lambda x, y: x and y, [ i['success'] for i in result ]):
			# clean temporary upload directory if everything went well
			self._cleanTmpDir()

		# return the results
		self.finished(request.id, result)

	def put( self, request ):
		"""Modify an existing project, expects:

		request.options = [ { object: ..., options: ... }, ... ]
		"""
		MODULE.info( 'distribution.put: options: %s' % str( request.options ) )
		self._save(request, True)

	def add( self, request ):
		"""Add a new project, expects:

		request.options = [ { object: ..., options: ... }, ... ]
		"""
		MODULE.info( 'distribution.add: options: %s' % str( request.options ) )
		self._save(request, False)

	@LDAP_Connection()
	def get( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		"""Returns the objects for the given IDs

		requests.options = [ <ID>, ... ]

		return: [ { ... }, ... ]
		"""
		MODULE.info( 'distribution.get: options: %s' % str( request.options ) )

		# try to load all given projects
		ids = request.options
		result = []
		if isinstance( ids, ( list, tuple ) ):
			# list of all project properties (dicts) or None if project is not valid
			for iproject in [ util.Project.load(iid) for iid in ids ]:
				# make sure that project could be loaded
				if not iproject:
					result.append(None)
					continue

				# make sure that only the project owner himself (or an admin) is able
				# to see the content of a project
				if request.flavor == 'teacher' and iproject.sender.dn != self._user_dn:
					raise UMC_CommandError(_('Project details are only visible to the project owner himself or an administrator.'))

				# prepare date and time properties for distribution/collection of project files
				props = iproject.dict
				for jjob, jsuffix in ((iproject.atJobDistribute, 'distribute'), (iproject.atJobCollect, 'collect')):
					MODULE.info('check job: %s' % jsuffix)
					if not jjob:
						# no job is registered -> manual job distribution/collection
						MODULE.info('no existing job -> manual execution')
						props['%sType' % jsuffix] = 'manual'
						continue

					# job is registered -> prepare date and time fields
					MODULE.info('job nr #%d scheduled for %s -> automatic execution' % (jjob.nr, jjob.execTime))
					props['%sType' % jsuffix] = 'automatic'
					props['%sDate' % jsuffix] = datetime.strftime(jjob.execTime, '%Y-%m-%d')
					props['%sTime' % jsuffix] = datetime.strftime(jjob.execTime, '%H:%M')

				# adjust sender / recipients properties
				props['sender'] = props['sender'].username
				recipients = []
				for recip in props['recipients']:
					recipients.append( {
						'id' : recip.dn,
						'label' : recip.type == util.TYPE_USER and Display.user( recip.dict ) or recip.name
						} )
				props['recipients'] = recipients

				# append final dict to result list
				MODULE.info('final project dict: %s' % props)
				result.append(props)

		else:
			MODULE.warn( 'distribution.get: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		# return the results
		MODULE.info( 'distribution.get: results: %s' % str( result ) )
		self.finished( request.id, result )

	def distribute( self, request ):
		MODULE.info( 'distribution.distribute: options: %s' % str( request.options ) )

		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % type(request.options) )

		# update the sender information of the selected projects
		ids = request.options
		result = []
		for iid in ids:
			MODULE.info( 'Distribute project: %s' % iid )
			try:
				# make sure that project could be loaded
				iproject = util.Project.load(iid)
				if not iproject:
					raise IOError( _('Project "%s" could not be loaded') % iid )

				# make sure that only the project owner himself (or an admin) is able
				# to distribute a project
				if request.flavor == 'teacher' and iproject.sender.dn != self._user_dn:
					raise ValueError(_('Only the owner himself or an administrator may distribute a project.'))

				# project was loaded successfully... try to distribute it
				usersFailed = []
				iproject.distribute(usersFailed)

				# raise an error in case distribution failed for some users
				if usersFailed:
					MODULE.info('Failed processing the following users: %s' % usersFailed)
					usersStr = ', '.join([ Display.user(i) for i in usersFailed ])
					raise IOError(_('The project could not distributed to the following users: %s') % usersStr)

				# save result
				result.append(dict(
					name = iid,
					success = True
				))
			except (ValueError, IOError) as e:
				result.append(dict(
					name = iid,
					success = False,
					details = str(e)
				))

		# return the results
		self.finished(request.id, result)
		MODULE.info( 'distribution.distribute: results: %s' % str( result ) )

	def collect( self, request ):
		MODULE.info( 'distribution.collect: options: %s' % str( request.options ) )

		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % (type(request.options),) )

		# try to open the UDM user object of the current user
		sender = self._get_sender(request)

		# update the sender information of the selected projects
		ids = request.options
		result = []
		for iid in ids:
			MODULE.info( 'Collect project: %s' % iid )
			try:
				# make sure that project could be loaded
				iproject = util.Project.load(iid)
				if not iproject:
					raise IOError( _('Project "%s" could not be loaded') % iid )

				# replace the projects sender with the current logged in user
				iproject.sender = sender

				# project was loaded successfully... try to distribute it
				dirsFailed = []
				iproject.collect(dirsFailed)

				# raise an error in case distribution failed for some users
				if dirsFailed:
					dirsStr = ', '.join(dirsFailed)
					MODULE.info('Failed collecting the following dirs: %s' % dirsStr)
					raise IOError(_('The following user directories could not been collected: %s') % dirsStr)

				# save result
				result.append(dict(
					name = iid,
					success = True
				))
			except (ValueError, IOError) as e:
				result.append(dict(
					name = iid,
					success = False,
					details = str(e)
				))

		# return the results
		self.finished(request.id, result)
		MODULE.info( 'distribution.collect: results: %s' % str( result ) )

	def adopt( self, request ):
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % (type(request.options),) )

		# try to open the UDM user object of the current user
		sender = self._get_sender(request)

		# update the sender information of the selected projects
		ids = request.options
		result = []
		for iid in ids:
			try:
				# make sure that project could be loaded
				iproject = util.Project.load(iid)
				if not iproject:
					raise IOError( _('Project "%s" could not be loaded') % iid )

				# project was loaded successfully
				iproject.sender = sender
				iproject.save()
			except (ValueError, IOError) as e:
				result.append(dict(
					name = iid,
					success = False,
					details = str(e)
				))

		# return the results
		self.finished(request.id, result)

	def remove( self, request ):
		"""Removes the specified projects

		requests.options = [ <name>, ... ]

		"""
		MODULE.info( 'distribution.remove: options: %s' % str( request.options ) )

		ids = request.options
		if not isinstance( ids, ( list, tuple ) ):
			MODULE.warn( 'distribution.remove: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		# list of all project properties (dicts) or None if project is not valid
		for iproject in [ util.Project.load(ientry.get('object')) for ientry in ids ]:
			# make sure that project could be loaded
			if not iproject:
				continue

			# make sure that only the project owner himself (or an admin) is able
			# to see the content of a project
			if request.flavor == 'teacher' and iproject.sender.dn != self._user_dn:
				raise UMC_CommandError(_('Only the owner himself or an administrator may delete a project.'))

			# purge the project
			iproject.purge()

		self.finished( request.id, None )

