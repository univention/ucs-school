#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console module:
#   Moderating print jobs of students
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

import datetime
import glob
import locale
import os
import shutil
import stat
import subprocess
import uuid

from univention.lib.i18n import Translation

from univention.management.console.modules import UMC_OptionTypeError, Base
from univention.management.console.log import MODULE
from univention.management.console.config import ucr
from univention.management.console.protocol.message import Response
from univention.management.console.protocol.definitions import *

from ucsschool.lib import LDAP_Connection, LDAP_ConnectionError, set_credentials, SchoolSearchBase, SchoolBaseModule, Display

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

	def __init__(self):
		global CUPSPDF_DIR, CUPSPDF_USERSUBDIR

		SchoolBaseModule.__init__(self)

		CUPSPDF_DIR, CUPSPDF_USERSUBDIR = os.path.normpath(ucr.get('cups/cups-pdf/directory')).split('%U')
		# create directory if it does not exist
		try:
			if not os.path.exists(CUPSPDF_DIR):
				os.makedirs(DISTRIBUTION_DATA_PATH, 0o755)
		except:
			MODULE.error('error occured while creating %s' % CUPSPDF_DIR)

	@LDAP_Connection()
	def printers(self, request, ldap_user_read=None, ldap_position=None, search_base=None):
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

		self.finished(request.id, result)

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
			user_path = os.path.join(CUPSPDF_DIR, student.info['username'], CUPSPDF_USERSUBDIR, '*.pdf')
			for document in filter(lambda filename: os.path.isfile(filename), glob.glob(user_path)):
				printjoblist.append(Printjob(student, document).json())

		self.finished(request.id, printjoblist)

	def download(self, request):
		"""Searches for print jobs

		requests.options = {}
		  'username' -- owner of the print job
		  'filename' -- relative filename of the print job

		return: <PDF document>
		"""
		self.required_options(request, 'username', 'printjob')
		response = Response(mime_type='application/pdf')
		response.id = request.id
		response.command = 'COMMAND'
		if request.options['username'].find('/') > 0 or request.options['printjob'].find('/') > 0:
			raise UMC_OptionTypeError('Invalid file')
		path = os.path.join(CUPSPDF_DIR, request.options['username'], CUPSPDF_USERSUBDIR, request.options['printjob'])
		if not os.path.exists(path):
			raise UMC_OptionTypeError('Invalid file')
		fd = open(path)
		response.body = fd.read()
		fd.close()
		self.finished(request.id, response)

	def get(self, request):
		"""Returns the objects for the given IDs

		requests.options = [ <ID>, ... ]

		return: [ { 'id' : <unique identifier>, 'name' : <display name>, 'color' : <name of favorite color> }, ... ]
		"""
		MODULE.info('printermoderation.get: options: %s' % str(request.options))
		ids = request.options
		result = []
		if isinstance(ids, (list, tuple)):
			ids = set(ids)
			result = filter(lambda x: x['id'] in ids, Instance.entries)
		else:
			MODULE.warn('printermoderation.get: wrong parameter, expected list of strings, but got: %s' % str(ids))
			raise UMC_OptionTypeError('Expected list of strings, but got: %s' % str(ids))
		MODULE.info('printermoderation.get: results: %s' % str(result))
		self.finished(request.id, result)

	def delete(self, request):
		"""Delete a print job

		requests.options = {}
		  'username' -- owner of the print job
		  'printjob' -- relative filename of the print job

		return: <PDF document>
		"""
		self.required_options(request, 'username', 'printjob')
		if request.options['username'].find('/') > 0 or request.options['printjob'].find('/') > 0:
			raise UMC_OptionTypeError('Invalid file')
		path = os.path.join(CUPSPDF_DIR, request.options['username'], CUPSPDF_USERSUBDIR, request.options['printjob'])
		success = True
		if os.path.exists(path):
			MODULE.info('Deleting print job "%s"' % path)
			try:
				os.unlink(path)
			except OSError as e:
				success = False
				MODULE.error('Error deleting print job: %s' % str(e))

		self.finished(request.id, success)

	def printit(self, request):
		"""Print a given document on the given printer

		requests.options = {}
		  'username' -- owner of the print job
		  'printjob' -- relative filename of the print job
		  'printer' -- the printer to use (<hostname>://<printer>)

		return: <PDF document>
		"""
		self.required_options(request, 'username', 'printjob', 'printer')

		if request.options['username'].find('/') > 0 or request.options['printjob'].find('/') > 0:
			raise UMC_OptionTypeError('Invalid file')
		if request.options['printer'].find('://') < 1:
			raise UMC_OptionTypeError('Invalid printer URI')

		spoolhost, printer = request.options['printer'].split('://', 1)
		path = os.path.join(CUPSPDF_DIR, request.options['username'], CUPSPDF_USERSUBDIR, request.options['printjob'])
		success = False
		if os.path.exists(path):
			MODULE.info('Deleting print job "%s"' % path)
			MODULE.error('Printing: "%s"' % '" "'.join([
				'lpr',
				# specify printer
				'-P', printer,
				# print as alternate user
				'-U', request.options['username'],
				# set job name
				'-J', Printjob.filename2label(request.options['printjob']),
				# delete file after printing
				'-r',
				# spool host
				'-H', spoolhost,
				# the file
				path]))
			success = subprocess.call([
				'lpr',
				# specify printer
				'-P', printer,
				# print as alternate user
				'-U', request.options['username'],
				# set job name
				'-J', Printjob.filename2label(request.options['printjob']),
				# delete file after printing
				'-r',
				# the file
				path,
				# spool host
				'-H', spoolhost]) == 0
			if success:
				MODULE.info('Printing was success')
			else:
				MODULE.error('Printing has failed')

		self.finished(request.id, success)


class Printjob(object):
	pdf_cache = {}

	def __init__(self, owner, fullfilename):
		self.owner = owner  # got univention.admin.modules here
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
				name = name[: -4]
		return name

	def json(self):
		return {
			'id': self.fullfilename,
			'username': self.owner['username'],
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
