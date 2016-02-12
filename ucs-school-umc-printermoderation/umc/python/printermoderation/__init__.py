#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Moderating print jobs of students
#
# Copyright 2012-2016 Univention GmbH
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

import datetime
import glob
import os
import stat
import subprocess

from univention.lib.i18n import Translation

from univention.management.console.modules import UMC_OptionTypeError
from univention.management.console.modules.decorators import simple_response, sanitize
from univention.management.console.modules.sanitizers import StringSanitizer
from univention.management.console.log import MODULE
from univention.management.console.config import ucr

from ucsschool.lib import LDAP_Connection, SchoolBaseModule, Display

import univention.admin.modules as udm_modules

DISTRIBUTION_DATA_PATH = '/var/lib/ucs-school-umc-distribution'
DISTRIBUTION_CMD = '/usr/lib/ucs-school-umc-distribution/umc-distribution'

OWNER = 'root'
WWWGROUP = 'www-data'
CACHE_DIR = '/var/cache/printermoderation'
CUPSPDF_DIR = None
CUPSPDF_USERSUBDIR = None

_ = Translation('ucs-school-umc-printermoderation').translate

# read list of UDM mdules
udm_modules.update()


class Instance(SchoolBaseModule):

	def init(self):
		global CUPSPDF_DIR, CUPSPDF_USERSUBDIR
		SchoolBaseModule.init(self)
		CUPSPDF_DIR, CUPSPDF_USERSUBDIR = os.path.normpath(ucr.get('cups/cups-pdf/directory', '/var/spool/cups-pdf/%U')).split('%U')
		# create directory if it does not exist
		try:
			if not os.path.exists(CUPSPDF_DIR):
				os.makedirs(DISTRIBUTION_DATA_PATH, 0o755)
		except (OSError, IOError) as exc:
			MODULE.error('error occured while creating %s: %s' % (CUPSPDF_DIR, exc))

	def _get_path(self, username, printjob):
		printjob = printjob.replace('/', '')
		username = username.replace('/', '')
		path = os.path.join(CUPSPDF_DIR, username, CUPSPDF_USERSUBDIR, printjob)
		if not os.path.realpath(path).startswith(os.path.realpath(CUPSPDF_DIR)):
			raise UMC_OptionTypeError('Invalid file')
		return path

	def _get_all_username_variants(self, username):
		"""
		Checks for print job directories for the given username regardless of
		the case of the directory name.
		"""
		username = username.replace('/', '')
		all_user_dirs = os.walk(CUPSPDF_DIR).next()[1]
		return [x for x in all_user_dirs if x.lower() == username.lower()]

	@simple_response
	@LDAP_Connection()
	def printers(self, ldap_user_read=None, ldap_position=None, search_base=None):
		"""List all available printers except PDF printers

		requests.options = {}
		  'school' -- school OU (optional)

		return: [ { 'id' : <spool host>://<printer name>, 'label' : <display name> }, ... ]
		"""
		printers = udm_modules.lookup('shares/printer', None, ldap_user_read, scope='sub', base=search_base.printers)

		result = []
		for prt in printers:
			# ignore PDF printers
			uri = prt.info.get('uri', [])
			if uri and uri[0].startswith('cups-pdf'):
				continue
			name = prt.info['name']
			spool_host = prt.info['spoolHost'][0]
			result.append({'id': '%s://%s' % (spool_host, name), 'label': name})
		return result

	@LDAP_Connection()
	def query(self, request, ldap_user_read=None, ldap_position=None, search_base=None):
		"""Searches for print jobs

		requests.options = {}
		  'school' -- school OU (optional)
		  'class' -- if not  set to 'all' the print jobs of the given class are listed only
		  'pattern' -- search pattern that must match the name or username of the students

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.error('query')
		self.required_options(request, 'class')

		klass = request.options.get('class')
		if klass in (None, 'None'):
			klass = None
		students = self._users(ldap_user_read, search_base, group=klass, user_type='student', pattern=request.options.get('pattern', ''))

		printjoblist = []

		for student in students:
			username = student.info['username']
			path_username = dict((self._get_path(username, ''), username) for username in self._get_all_username_variants(username))
			for user_path, username in path_username.iteritems():
				printjoblist.extend(Printjob(student, username, document).json() for document in glob.glob(os.path.join(user_path, '*.pdf')) if os.path.isfile(document))

		self.finished(request.id, printjoblist)

	@sanitize(
		username=StringSanitizer(required=True),
		printjob=StringSanitizer(required=True),
	)
	def download(self, request):
		"""Searches for print jobs

		requests.options = {}
		  'username' -- owner of the print job
		  'printjob' -- relative filename of the print job

		return: <PDF document>
		"""
		path = self._get_path(request.options['username'], request.options['printjob'])

		if not os.path.exists(path):
			raise UMC_OptionTypeError('Invalid file')

		with open(path) as fd:
			self.finished(request.id, fd.read(), mimetype='application/pdf')

	@sanitize(
		username=StringSanitizer(required=True),
		printjob=StringSanitizer(required=True),
	)
	@simple_response
	def delete(self, username, printjob):
		"""Delete a print job

		requests.options = {}
		  'username' -- owner of the print job
		  'printjob' -- relative filename of the print job

		return: <PDF document>
		"""
		path = self._get_path(username, printjob)

		success = True
		if os.path.exists(path):
			MODULE.info('Deleting print job %r' % (path,))
			try:
				os.unlink(path)
			except OSError as exc:
				success = False
				MODULE.error('Error deleting print job: %s' % (exc,))
		return success

	@sanitize(
		username=StringSanitizer(required=True),
		printjob=StringSanitizer(required=True),
		printer=StringSanitizer(required=True),
	)
	@simple_response
	def printit(self, username, printjob, printer):
		"""Print a given document on the given printer

		requests.options = {}
		  'username' -- owner of the print job
		  'printjob' -- relative filename of the print job
		  'printer' -- the printer to use (<hostname>://<printer>)

		return: <PDF document>
		"""

		path = self._get_path(username, printjob)

		try:
			spoolhost, printer = printer.split('://', 1)
		except ValueError:
			raise UMC_OptionTypeError('Invalid printer URI')

		success = False
		if os.path.exists(path):
			MODULE.info('Deleting print job %r' % (path,))
			cmd = [
				'lpr',
				# specify printer
				'-P', printer,
				# print as alternate user
				'-U', username,
				# set job name
				'-J', Printjob.filename2label(printjob),
				# delete file after printing
				'-r',
				# the file
				path,
				# spool host
				'-H', spoolhost
			]
			MODULE.error('Printing: %r' % '" "'.join(cmd))
			success = subprocess.call(cmd) == 0
			if success:
				MODULE.info('Printing was success')
			else:
				MODULE.error('Printing has failed')

		return success


class Printjob(object):
	pdf_cache = {}

	def __init__(self, owner, username, fullfilename):
		self.owner = owner  # got univention.admin.modules here
		self.username = username  # username w.r.t. case sensitivity
		self.fullfilename = os.path.normpath(fullfilename)
		self.filename = os.path.basename(self.fullfilename)
		self.tmpfilename = None

		stats = os.stat(self.fullfilename)
		self.ctime = datetime.datetime.fromtimestamp(stats[stat.ST_CTIME])

		self.name = Printjob.filename2label(self.filename)
		self.readPDF()

	@staticmethod
	def filename2label(filename):
		name = filename
		if '-' in filename:
			name = filename.split('-', 1)[1]
			if name.endswith('.pdf'):
				name = name[:-4]
		return name

	def json(self):
		return {
			'id': self.fullfilename,
			'username': self.username,
			'user': Display.user(self.owner),
			'printjob': self.name,
			'filename': self.filename,
			'date': (self.ctime.year, self.ctime.month, self.ctime.day, self.ctime.hour, self.ctime.minute, self.ctime.second),
			'pages': self.metadata.get('pages')
		}

	def readPDF(self):
		self.metadata = {}
		if self.fullfilename in Printjob.pdf_cache:
			MODULE.error('PDF file was cached: %s' % self.fullfilename)
			self.metadata = Printjob.pdf_cache[self.fullfilename]
			return
		pdfinfo = subprocess.Popen(['/usr/bin/pdfinfo', self.fullfilename], shell=False, env={'LANG': 'C'}, stdout=subprocess.PIPE)
		stdout, stderr = pdfinfo.communicate()
		for line in stdout.split('\n'):
			if not line:
				continue
			try:
				key, value = line.split(':', 1)
			except ValueError:
				MODULE.error('Could not parse line: %s' % line)
				continue
			self.metadata[key.strip().lower()] = value.strip()

		Printjob.pdf_cache[self.fullfilename] = self.metadata
