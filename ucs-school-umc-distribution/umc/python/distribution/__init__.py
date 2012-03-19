#!/usr/bin/python2.6
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   
#
# Copyright 2012 Univention GmbH
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
from univention.management.console.modules import UMC_OptionTypeError, UMC_CommandError, Base
from univention.management.console.log import MODULE
from univention.management.console.protocol.definitions import *

import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions
import os
import time

from ucsschool.lib.schoolldap import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, LDAP_Filter, Display

import util

_ = Translation( 'ucs-school-umc-distribution' ).translate

class Instance( SchoolBaseModule ):
	def __init__( self ):
		SchoolBaseModule.__init__(self)

	def init(self):
		SchoolBaseModule.init(self)
		# initiate paths for data distribution
		util.initPaths()

	@LDAP_Connection()
	def users( self, request, search_base = None, ldap_user_read = None, ldap_position = None ):
		# parse group parameter
		group = request.options.get('group')
		if not group or group == 'None':
			group = None

		# get list of all users matching the given pattern
		result = [ {
			'id': i.dn,
			'label': Display.user(i)
		} for i in self._users( ldap_user_read, search_base, group = group, user_type = 'pupil', pattern = request.options.get('pattern') ) ]
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
		except udm_exceptions.noObject as e:
			self.finished(request.id, None, _('Failed to load user information: %s') % e, False)
			MODULE.error('Could not find user DN: %s' % self._user_dn)
		except Exception as e:
			self.finished(request.id, None, str(e), False)
			MODULE.error('Could not open user DN: %s (%s)' % (self._user_dn, e))

		return sender

	@LDAP_Connection()
	def _save( self, request, doUpdate = True, ldap_user_read = None, ldap_position = None, search_base = None ):
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		# try to open the UDM user object of the current user
		sender = self._get_sender(request)
		if not sender:
			return

		# try to create all specified projects
		result = []
		userModule = udm_modules.get('users/user')
		for ientry in request.options:
			iprops = ientry.get('object', {})
			try:
				# remove keys that may not be set from outside
				for k in ('atJobNumCollect', 'atJobNumDistribute'):
					iprops.pop(k, None)

				# load the project or create a new one
				project = None
				if doUpdate:
					# try to load the given project
					project = util.Project.load(iprops.get('name', ''))
					if not project:
						raise ValueError(_('The specified project does not exist: %s') % iprops['name'])

					# update project values
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
								jtime = time.mktime(time.strptime(strtime, '%Y-%m-%d %H:%M'))
								project.dict[jprop] = jtime
							except ValueError as e:
								raise ValueError(_('Could not set time for: %s') % jname)

							# make sure the execution time lies sufficiently (5min) in the future
							if time.time() + 60 * 5 > project.dict[jprop]:
								raise ValueError(_('The specified time needs to lie in the future for: %s') % jname)
						else:
							# manual distribution/collection
							project.dict[jprop] = None

				if 'recipients' in iprops:
					# lookup the users in LDAP and save them to the project
					users = []
					for idn in iprops.get('recipients', []):
						try:
							# try to load the UDM user object given its DN
							iobj = userModule.object(None, ldap_user_read, None, idn)
							iobj.open()

							# create a new User object, it will only remember its relevant information
							iuser = util.User(i.info)
							iuser.dn = i.dn
							users.append(iuser)
						except udm_exceptions.noObject as e:
							MODULE.error('Could not find user DN: %s' % idn)
						except Exception as e:
							MODULE.error('Could not open user DN: %s (%s)' % (idn, e))
					project.recipients = users

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

				# everything ok
				result.append(dict(
					name = iprops.get('name'),
					success = True
				))
			except (ValueError, IOError) as e:
				# data not valid... create error info
				result.append(dict(
					name = iprops.get('name'),
					success = False,
					details = str(e)
				))

		# return the results
		self.finished(request.id, result)

#TODO: move files into cache directory
#			# move files to sender directory and to project cache directory
#			debugmsg( ud.ADMIN, ud.INFO, 'copy files to sender directory and cache directory' )
#			filelist = project['files']
#			project['files'] = []
#			for fileitem in filelist:
#				# copy to sender directory
#				target = str( os.path.join( project['sender']['projectdir'], fileitem['filename'] ) )
#				debugmsg( ud.ADMIN, ud.INFO, 'coping %s to %s' % ( fileitem['tmpfname'], target ) )
#				try:
#					shutil.copy( fileitem['tmpfname'], target )
#					os.chown( target, int(sender_obj['uidNumber']), int(sender_obj['gidNumber']) )
#				except Exception, e:
#					debugmsg( ud.ADMIN, ud.ERROR, 'failed to copy/chown "%s" to "%s": %s' % (fileitem['tmpfname'], target, str(e)))
#
#				# move to cache directory
#				target = str( os.path.join( project_data_dir, fileitem['filename'] ) )
#				debugmsg( ud.ADMIN, ud.INFO, 'moving %s to %s' % ( fileitem['tmpfname'], target ) )
#				try:
#					shutil.move( fileitem['tmpfname'], target )
#					os.chown( target, 0, 0 )
#				except Exception, e:
#					debugmsg( ud.ADMIN, ud.ERROR, 'failed to copy/chown "%s" to "%s": %s' % (fileitem['tmpfname'], target, str(e)))
#				project['files'].append( fileitem['filename'] )

#TODO: distribute if no starttime is given
#			if not project['starttime']:
#				debugmsg( ud.ADMIN, ud.INFO, 'no starttime set - distributing data now')
#				distributeData( project )

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
		MODULE.info( '### reques.flavor: %s' % str( request.flavor ) )

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
					props['%sType' % jsuffix] = 'automatic'
					props['%sDate' % jsuffix] = time.strftime('%Y-%m-%d', time.localtime(jjob.execTime))
					props['%sTime' % jsuffix] = time.strftime('%H:%M', time.localtime(jjob.execTime))
					MODULE.info('job nr #%d scheduled for %s %s -> automatic execution' % (jjob.nr, props['%sDate' % jsuffix], props['%sTime' % jsuffix]))

				# adjust sender / recipients properties
				props['sender'] = props['sender'].username
				props['recipients'] = [ j.username for j in props['recipients'] ]

				# append final dict to result list
				MODULE.info('final project dict: %s' % props)
				result.append(props)

		else:
			MODULE.warn( 'distribution.get: wrong parameter, expected list of strings, but got: %s' % str( ids ) )
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		# return the results
		MODULE.info( 'distribution.get: results: %s' % str( result ) )
		self.finished( request.id, result )

	def adopt( self, request ):
		# make sure that we got a list
		if not isinstance(request.options, (tuple, list)):
			raise UMC_OptionTypeError( 'Expected list of strings, but got: %s' % str(ids) )

		# try to open the UDM user object of the current user
		sender = self._get_sender(request)
		if not sender:
			return

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

