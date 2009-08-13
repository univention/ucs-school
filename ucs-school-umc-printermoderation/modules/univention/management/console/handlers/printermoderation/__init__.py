#!/usr/bin/python2.4
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: Printer Moderation Module
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

from subprocess import call
import datetime
import fnmatch
import glob
import grp
import os
import pickle
import pwd
import re
import shutil
import socket
import stat
import traceback

import _revamp
import _types
import _schoolldap

DISTRIBUTION_DATA_PATH = '/var/lib/ucs-school-umc-distribution'
DISTRIBUTION_CMD = '/usr/lib/ucs-school-umc-distribution/umc-distribution'

OWNER = 'root'
WWWGROUP = 'www-data'
CACHE_DIR = '/var/cache/printermoderation'
CUPSPDF_DIR = None
CUPSPDF_USERSUBDIR = None

_ = umc.Translation( 'univention.management.console.handlers.printermoderation' ).translate

icon = 'printermoderation/module'
short_description = _( 'Printer Moderation' )
long_description = _( 'Printer Moderation for Classrooms' )
categories = [ 'all' ]

command_description = {
	'printermoderation/list': umch.command(
		short_description = _( 'List print jobs' ),
		long_description = _( 'List print jobs' ),
		method = 'printermoderation_list',
		values = {
			'ou': _types.ou,
			'selectedgroup' : _types.group,
			},
		startup = True,
		priority = 90
	),
	'printermoderation/job/print': umch.command(
		short_description = _( 'Print job' ),
		long_description = _( 'Print job' ),
		method = 'printermoderation_job_print',
		values = {
			'ou': _types.ou,
			'jobs': _types.jobs,
			'selectedgroup' : _types.group,
			'selectedprinter' : _types.printer,
			},
		priority = 80
	),
	'printermoderation/job/delete': umch.command(
		short_description = _( 'Delete print job' ),
		long_description = _( 'Delete print job' ),
		method = 'printermoderation_job_delete',
		values = {
			'ou': _types.ou,
			'jobs': _types.jobs,
			'selectedgroup' : _types.group,
			},
		priority = 80
	),
	'printermoderation/job/review': umch.command(
		short_description = _( 'Review print job' ),
		long_description = _( 'Review print job' ),
		method = 'printermoderation_job_review',
		values = {
			'ou': _types.ou,
			# WARNING only the first job is reviewed!!
			'jobs': _types.jobs,
			'selectedgroup' : _types.group,
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

class Printjob (object):
	def __init__ (self, owner, fullfilename):
		self.owner = owner # got univention.admin.modules here
		self.fullfilename = os.path.normpath (fullfilename)
		self.filename = os.path.basename (self.fullfilename)
		self.tmpfilename = None

		stats = os.stat (self.fullfilename)
		self.ctime = datetime.datetime.fromtimestamp (stats[stat.ST_CTIME])

		s = self.filename.index ('-') + 2
		e = len (self.filename) - 5
		if s >= e:
			self.name = self.filename
		else:
			self.name = self.filename[s:e]

	def getRelativeFilename (self):
		relative = self.fullfilename[len(CUPSPDF_DIR):]
		if relative.startswith (os.path.sep):
			relative = relative[len(os.path.sep):]
		return relative

	def getRelativeTmpfilename (self):
		if self.tmpfilename == None:
			return None
		relative = self.tmpfilename[len(CACHE_DIR):]
		if relative.startswith (os.path.sep):
			relative = relative[len(os.path.sep):]
		return relative

	def copyToTmpdir (self, messages):
		ownerid = pwd.getpwnam (OWNER)[2]
		groupid = grp.getgrnam (WWWGROUP)[2]
		if None in (groupid, ownerid):
			debugmsg(ud.ADMIN, ud.ERROR, \
					'Id(s) not found: (%s:%s), (%s:%s)' % \
					(OWNER, ownerid, WWWGROUP, groupid))
			messages.append (_ ('Unable to copy printjob to temporary directory'))
			return
		tmpdir = os.tempnam (CACHE_DIR)
		os.makedirs (tmpdir, mode=0750)
		os.chown (tmpdir, ownerid, groupid)
		tmpfilename = os.path.join (tmpdir, \
				os.path.basename (self.fullfilename))
		shutil.copy (self.fullfilename, tmpfilename)
		os.chown (tmpfilename, ownerid, groupid)
		os.chmod (tmpfilename, 0750)
		self.tmpfilename = tmpfilename
		return self.tmpfilename

	def printIt (self, username, printername, messages):
		debugmsg(ud.ADMIN, ud.INFO, 'print')
		if not os.path.exists (self.fullfilename):
			debugmsg(ud.ADMIN, ud.ERROR, \
					'File does not exist: %s' % self.fullfilename)
			messages.append (_ ('File does not exist') + \
					(': %s' % self.fullfilename))
		elif not printername or printername.strip () == '':
			debugmsg(ud.ADMIN, ud.ERROR, \
					'Printer not specified: %s' % printername)
			messages.append (_ ('Printer not specified') + \
					(': %s' % printername))
		else:
			debugmsg(ud.ADMIN, ud.INFO, \
					'Printing file: %s' % self.fullfilename)
			call (['lpr', \
					# specify printer
					'-P', printername, \
					# print as alternate user
					'-U', username, \
					# set job name
					'-J', self.name, \
					# delete file after printing
					'-r', \
					# the file
					self.fullfilename])
		return messages

	def delete (self, messages):
		debugmsg(ud.ADMIN, ud.INFO, 'delete')
		if not os.path.exists (self.fullfilename):
			debugmsg(ud.ADMIN, ud.ERROR, \
					'File does not exist: %s' % self.fullfilename)
			messages.append (_ ('File does not exist') + \
					(': %s' % self.fullfilename))
		else:
			try:
				debugmsg(ud.ADMIN, ud.INFO, \
						'Deleting file: %s' % self.fullfilename)
				os.unlink (self.fullfilename)
			except:
				debugmsg(ud.ADMIN, ud.ERROR, \
						'Error deleting file: %s\n%s' % \
						(self.fullfilename, traceback.format_exc().replace('%','#')))
				messages.append (_ ('Error deleting file') + \
						(': %s' % self.fullfilename))
		return messages

	def __str__ (self):
		return self.name

class handler( umch.simpleHandler, _revamp.Web  ):
	def __init__( self ):
		global CUPSPDF_DIR, CUPSPDF_USERSUBDIR
		umch.simpleHandler.__init__( self, command_description )
		_revamp.Web.__init__( self )

		# generate config objects
		self.configRegistry = univention.config_registry.ConfigRegistry()
		self.configRegistry.load()

		CUPSPDF_DIR, CUPSPDF_USERSUBDIR = os.path.normpath \
				(self.configRegistry.get ('cups/cups-pdf/directory')).split ('%U')
		# create directory if it does not exist
		try:
			if not os.path.exists (CUPSPDF_DIR):
				os.makedirs( DISTRIBUTION_DATA_PATH, 0755 )
		except:
			debugmsg(ud.ADMIN, ud.ERROR, \
					'error occured while creating %s' % CUPSPDF_DIR)

		self.ldap_anon = _schoolldap.SchoolLDAPConnection()
		self.ldap_master = _schoolldap.SchoolLDAPConnection( ldapserver = self.configRegistry['ldap/master'] )

		debugmsg( ud.ADMIN, ud.INFO, 'availableOU=%s' % self.ldap_anon.availableOU )

	def printermoderation_list (self, umcobject):
		debugmsg (ud.ADMIN, ud.ERROR, 'printermoderation_list')
		self.ldap_anon.switch_ou(umcobject.options.get('ou', \
				self.ldap_anon.availableOU[0]))

		selectedgroup = umcobject.options.get ('selectedgroup', None)
		grouplist = self._generate_grouplist ( umcobject )
		accountlist = self._generate_accountlist ( umcobject, \
				self.ldap_anon.searchbasePupils )
		messages = []

		# Sort joblist by creation date descending
		printjoblist = self._generate_printjoblist (umcobject, \
				accountlist)
		printjoblist = sorted (printjoblist, key = lambda x: x.ctime)

		self.finished (umcobject.id (), (self.ldap_anon.availableOU, \
				grouplist, selectedgroup, printjoblist, messages))

	def printermoderation_job_print (self, umcobject):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_job_print' )
		selectedou = umcobject.options.get('ou', None)
		selectedgroup = umcobject.options.get ('selectedgroup', None)
		selectedprinter = umcobject.options.get('selectedprinter', None)
		messages = []
		printers = []
		jobs = umcobject.options.get ('jobs', None)
		printedjobs = []

		if not selectedprinter:
			# retrieve printers
			printers = self._generate_printerlist (socket.getfqdn ())

		for p in printers:
			print p.info

		if selectedou and selectedgroup and selectedprinter:
			for job in jobs:
				try:
					userdn, filename = job
					printer = self._get_printer (selectedprinter)
					# WARNING only a plain filename without any path components is allowed here!
					filename = os.path.basename (filename)
					printjob = self._get_printjob (userdn, filename)
					if printjob:
						# Print job and delete associated jobfile after printing
						messages = printjob.printIt (self._username, \
								printer.info['name'], messages)
						printedjobs.append (printjob)
						debugmsg( ud.ADMIN, ud.INFO, 'Job printed: %s' % printjob.name )
				except:
					debugmsg( ud.ADMIN, ud.ERROR, 'Error unpacking values: %s' % job )
					continue
		self.finished (umcobject.id (), (selectedou, selectedgroup, \
				printers, selectedprinter, jobs, printedjobs, messages))

	def printermoderation_job_delete (self, umcobject):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_job_delete' )
		selectedou = umcobject.options.get('ou', None)
		selectedgroup = umcobject.options.get ('selectedgroup', None)
		messages = []
		deletedjobs = []

		if selectedou and selectedgroup:
			jobs = umcobject.options.get ('jobs', None)
			for job in jobs:
				try:
					userdn, filename = job
					# WARNING only a plain filename without any path components is allowed here!
					filename = os.path.basename (filename)
					printjob = self._get_printjob (userdn, filename)
					if printjob:
						# Delete associated print jobfile
						messages = printjob.delete (messages)
						deletedjobs.append (printjob)
						debugmsg( ud.ADMIN, ud.INFO, 'Job deleted: %s' % printjob.name )
				except:
					debugmsg( ud.ADMIN, ud.ERROR, 'Error unpacking values: %s' % job )
					continue
		self.finished (umcobject.id (), (selectedou, selectedgroup, deletedjobs, messages))

	def printermoderation_job_review (self, umcobject):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_job_review' )
		# 1. Provide download link?
		selectedou = umcobject.options.get('ou', None)
		selectedgroup = umcobject.options.get ('selectedgroup', None)
		jobs = umcobject.options.get ('jobs', None)
		printjob = None
		messages = []

		if not None in (selectedou, selectedgroup, jobs) and len (jobs) > 0:
			# WARNING only the first job is reviewed!!
			job = jobs[0]
			userdn, filename = job
			# WARNING only a plain filename without any path components is allowed here!
			filename = os.path.basename (filename)
			printjob = self._get_printjob (userdn, filename)
			printjob.copyToTmpdir (messages)

		self.finished (umcobject.id (), (selectedou, selectedgroup, printjob, messages))

##################################################

	def _get_user( self, uid ):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_get_user' )
		userresult = univention.admin.modules.lookup(
				self.ldap_anon.usermodule, self.ldap_anon.co,
				self.ldap_anon.lo, scope='sub', superordinate=None,
				base=self.configRegistry['ldap/base'], filter=('uid=%s' % uid))
		if userresult and userresult[0]:
			user = userresult[0]
			user.open()
			return user
		debugmsg( ud.ADMIN, ud.ERROR, '_get_user: error while searching user object of uid=%s' % uid )

		debugmsg( ud.ADMIN, ud.INFO, '_get_user: unable to find user object of uid=%s' % uid )
		return None

	def _get_printjob (self, userdn, filename):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_get_printjob' )
		userlist = self._generate_userlist ([userdn])
		printjob = None

		if len (userlist) > 0:
			user = userlist[0]
			fullfilename = os.path.join (CUPSPDF_DIR, \
					user.info['username'], \
					CUPSPDF_USERSUBDIR, filename)
			if os.path.exists (fullfilename):
				printjob = Printjob (user, fullfilename)
		return printjob

	def _get_printer (self, printerdn):
		printer = None
		pr = univention.admin.objects.get(self.ldap_anon.printermodule, \
				None, self.ldap_anon.lo, None, printerdn)
		if pr:
			pr.open ()
			printer = pr
		return printer

	def _generate_printerlist (self, hostname=None):
		printerlist = []

		printerresult = univention.admin.modules.lookup( \
				self.ldap_anon.printermodule, \
				self.ldap_anon.co, self.ldap_anon.lo, \
				scope='sub', superordinate=None, \
				base=self.ldap_anon.searchbasePrinters)
		ud.debug( ud.ADMIN, ud.INFO, 'PRINTERMODERATION: list of printers %s' % str(printerresult) )

		for p in printerresult:
			p.open()
			if not hostname or hostname.strip () == '' or hostname in p.info['spoolHost']:
				printerlist.append (p)

		printerlist = sorted(printerlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
							  key = lambda x: x.info['name'] )

		return printerlist

	def _generate_printjoblist (self, umcobject, accountlist):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_generate_printjoblist' )
		printjoblist = []

		selectedgroup = umcobject.options.get ('selectedgroup', None)
		if selectedgroup and selectedgroup != _('No group selected'):
			#uids = [os.path.basename (path) for path in \
					#glob.glob (os.path.join (CUPSPDF_DIR, '*')) \
					#if os.path.isdir (path) ]

			for account in accountlist:
				# Retrieve available jobs for the users in group
				documents = [path for path in \
					glob.glob (os.path.join (CUPSPDF_DIR, account.info['username'], \
					CUPSPDF_USERSUBDIR, '*.pdf')) \
					if os.path.isfile (path) ]

				printjoblist += [Printjob (account, document) \
						for document in documents]
		return printjoblist

	def _generate_accountlist ( self, umcobject, filterbase = None ):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_generate_accountlist' )
		accountlist = []
		selectedgroup = umcobject.options.get ('selectedgroup', None)
		if selectedgroup and selectedgroup != _( 'No group selected' ):
			accountresult = univention.admin.modules.lookup( self.ldap_anon.groupmodule, self.ldap_anon.co, self.ldap_anon.lo,
									 scope='sub', superordinate=None,
									 base=self.ldap_anon.searchbaseClasses, filter='cn=%s' % selectedgroup)
			ud.debug( ud.ADMIN, ud.INFO, 'PRINTERMODERATION: list accounts from groups %s' % str( accountresult ) )

			for ar in accountresult:
				ar.open()
				ud.debug( ud.ADMIN, ud.INFO, 'PRINTERMODERATION: got users %s' % ar['users'] )
				userlist = ar['users']
				if filterbase:
					userlist = [ dn for dn in userlist if dn.endswith(filterbase) ]
				accountlist += self._generate_userlist( userlist )

		accountlist = sorted( accountlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
							  key = lambda x: x.info['username'] )
		return accountlist

	def _generate_userlist( self, userdns, lo = None ):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_generate_userlist' )
		if lo == None:
			lo = self.ldap_anon.lo

		userlist = []
		for userdn in userdns:
			ud.debug( ud.ADMIN, ud.INFO, \
					'printermoderation_generate_userlist: get user %s' % userdn )
			ur = univention.admin.objects.get(self.ldap_anon.usermodule, \
					None, lo, None, userdn)
			if ur:
				ur.open ()
				userlist.append( ur )

		userlist = sorted( userlist, cmp = lambda x, y: cmp( x.lower(), y.lower() ),
						   key = lambda x: x[ 'username' ] )
		return userlist

	def _generate_grouplist ( self, sorted_list = False ):
		debugmsg( ud.ADMIN, ud.INFO, 'printermoderation_generate_grouplist' )
		grouplist = []

		groupresult = univention.admin.modules.lookup(
				self.ldap_anon.groupmodule, self.ldap_anon.co,
				self.ldap_anon.lo, scope='sub', superordinate=None,
				base=self.ldap_anon.searchbaseClasses, filter=None)
		for gr in groupresult:
			grouplist.append (gr['name'])
		if sorted_list:
			grouplist = sorted (grouplist)

		grouplist.insert( 0, _( 'No group selected' ) )
		return grouplist
