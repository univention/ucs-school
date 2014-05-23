"""""""""""""""""""""""""""""""""""""""
  **Class Distribution**\n
"""""""""""""""""""""""""""""""""""""""
"""
.. module:: distribution
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""

from univention.lib.umc_connection import UMCConnection
import os
import time
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils

class Distribution(object):

	"""Contains the needed functuality for Materials distribution.
	By default the distribution is manual.\n
	:param school: name of the ou
	:type school: str
	:param umcConnection:
	:type umcConnection: UMC connection object
	:param ucr:
	:type ucr: UCR object
	:param name: name of distribution project to be added later
	:type name: str
	:param description: description of distribution project to be added  later
	:type description: str
	:param username: name of the creater user (teacher or admin)
	:type username: str
	:param flavor: flavor of the acting user
	:type flavor: str ('teacher' or 'admin')
	:param distributeTime: time for automatic distribution
	:type distributeTime: str ('%I:%M')
	:param distributionDate: date for automatic distribution
	:type distributionDate: str ('%Y-%m-%d)
	:param collectionTime: time for automatic collection
	:type collectionTime: str ('%I:%M')
	:param collectionDate: date for automatic collection
	:type collectionDate: str ('%Y-%m-%d)
	:param distributeType: type of the distribution
	:type distributionType: str ('automatic' or 'manual')
	:param collectionTye: type of the collection
	:type collectionType: str ('automatic' or 'manual')
	:param files: names of material files for the distribution project
	:type files: list of str
	:param recipients: groups which are included in the distribution project
	:type recipients: list of group objects
	"""
	def __init__(
			self,
			school,
			umcConnection=None,
			username=None,
			flavor=None,
			ucr=None,
			description=None,
			name=None,
			distributeType='manual',
			distributeTime=None,
			distributeDate=None,
			collectType='manual',
			collectTime=None,
			collectDate=None,
			files=[],
			recipients=[]):
		self.school = school
		self.name = name if name else uts.random_string()
		self.description = description if description else uts.random_string()
		self.distributeTime = distributeTime if distributeTime else time.strftime('%I:%M')
		self.distributeDate = distributeDate if distributeDate else time.strftime('%Y-%m-%d')
		self.collectTime = collectTime if collectTime else time.strftime('%I:%M')
		self.collectDate = collectDate if collectDate else time.strftime('%Y-%m-%d')
		self.distributeType = distributeType
		self.collectType = collectType
		self.files = files
		self.recipients = recipients
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		self.username = username if username else 'Administrator'
		self.flavor = flavor if flavor else 'admin'
		if umcConnection:
			self.umcConnection = umcConnection
		else:
			self.ucr.load()
			host = self.ucr.get('hostname')
			self.umcConnection = UMCConnection(host)
			self.umcConnection.auth(self.username, 'univention')

	def query(self, pattern=''):
		"""Calles 'distribution/query'
		:param pattern: the pattern to use in the search
		:type pattern: str
		"""
		flavor = self.flavor
		param = {
					'filter': 'private',
					'pattern': pattern
					}
		reqResult = self.umcConnection.request(
				'distribution/query',
				param,
				flavor)
		result = [x['name'] for x in reqResult if reqResult is not None]
		return result

	def genData(self, file_name, content_type, boundary, flavor):
		"""Generates data in the form to be sent via http POST request.\n
		:param file_name: file name to be uploaded
		:type file_name: str
		:param content_type: type of the content of the file
		:type content_type: str ('text/plain',..)
		:param boundary: the boundary
		:type boundary: str (-------123091)
		:param flavor: flavor of the acting user
		:type flavor: str
		"""
		with open(file_name, 'r') as f:
			data = r"""--{0}
Content-Disposition: form-data; name="uploadedfile"; filename="{1}"
Content-Type: {2}

{3}
--{0}
Content-Disposition: form-data; name="flavor"

{4}
--{0}
Content-Disposition: form-data; name="iframe"

false
--{0}
Content-Disposition: form-data; name="uploadType"

html5
--{0}--
""".format(boundary, file_name, content_type, f.read(), flavor)
		return data.replace("\n", "\r\n")

	def uploadFile(self, file_name, content_type):
		"""Uploads a file via http POST request.\n
		:param file_name: file name to be uploaded
		:type file_name: str
		:param content_type: type of the content of the file
		:type content_type: str ('text/plain',..)
		"""
		print 'Uploading a file'
		boundary= '---------------------------103454444410473823401882756'
		data = self.genData(file_name, content_type , boundary, self.flavor)
		headers = dict(self.umcConnection._headers)  # copy headers!
		httpcon = self.umcConnection.get_connection()
		header_content = {
			'Content-Type': 'multipart/form-data; boundary=%s' % (boundary,)
		}
		headers.update(header_content)
		headers['Cookie'] = headers['Cookie'].split(";")[0]
		headers['Accept'] = 'application/json'
		httpcon.request(
				"POST",
				'/umcp/upload/distribution/upload',
				data,
				headers=headers)
		r = httpcon.getresponse().status
		if r != 200:
			print 'httpcon.response().status=', r
			utils.fail('Unable to upload the file.')

	def add(self):
		"""Create files and upload them then add the project,
		calls: 'distribution/add'
		"""
		# creatng and uploading the files
		content_type = 'text/plain'
		for filename in self.files:
			with open(filename, 'w') as g:
				g.write('test_content')
			self.uploadFile(filename, content_type)
		print 'Adding Project %s' % (self.name)
		flavor = self.flavor
		recipients = []
		for item in self.recipients:
			recipients.append(item.dn())
		print 'recipients=', recipients
		param = [
				{
					'object':{
						'collectDate': self.collectDate,
						'collectTime': self.collectTime,
						'collectType': self.collectType,
						'description': self.description,
						'distributeDate': self.distributeDate,
						'distributeTime' : self.distributeTime,
						'distributeType' : self.distributeType,
						'files': self.files,
						'name': self.name,
						'recipients': recipients
						},
					'options': None
					}
				]
		print 'param=', param
		reqResult = self.umcConnection.request(
				'distribution/add',
				param,
				flavor)
		if not reqResult[0]['success']:
			utils.fail('Unable to add project (%r)' % (param,))

	def check_add(self):
		"""Calls 'distribution/query' and check the existance of the added project"""
		print 'Checking %s addition' % (self.name,)
		current = self.query(self.name)
		if not (self.name in current):
			utils.fail('Project %s was not added successfully' % (self.name,))

	def put(
			self,
			description=None,
			distributeType=None,
			distributeTime=None,
			distributeDate=None,
			collectType=None,
			collectTime=None,
			collectDate=None,
			files=[],
			recipients=[]):
		"""Modifies the already existing project.\n
		:param description: description of distribution project to be added  later
		:type description: str
		:param distributeTime: time for automatic distribution
		:type distributeTime: str ('%I:%M')
		:param distributionDate: date for automatic distribution
		:type distributionDate: str ('%Y-%m-%d)
		:param collectionTime: time for automatic collection
		:type collectionTime: str ('%I:%M')
		:param collectionDate: date for automatic collection
		:type collectionDate: str ('%Y-%m-%d)
		:param distributeType: type of the distribution
		:type distributionType: str ('automatic' or 'manual')
		:param collectionTye: type of the collection
		:type collectionType: str ('automatic' or 'manual')
		:param files: names of material files for the distribution project
		:type files: list of str
		:param recipients: groups which are included in the distribution project
		:type recipients: list of group objects
		"""
		print 'Editing Project %s' % (self.name)
		description = description if description else self.description
		distributeType = distributeType if distributeType else self.distributeType
		distributeTime = distributeTime if distributeTime else self.distributeTime
		distributeDate = distributeDate if distributeDate else self.distributeDate
		collectType = collectType if collectType else self.collectType
		collectTime = collectTime if collectTime else self.collectTime
		collectDate = collectDate if collectDate else self.collectDate
		files = files if files else self.files
		recipients = recipients if recipients else self.recipients
		new_recipients = []
		for item in recipients:
			new_recipients.append(item.dn())
		flavor = self.flavor
		param = [
				{
					'object':{
						'collectDate': collectDate,
						'collectTime': collectTime,
						'collectType': collectType,
						'description': description,
						'distributeDate': distributeDate,
						'distributeTime' : distributeTime,
						'distributeType' : distributeType,
						'files': files,
						'name': self.name,
						'recipients': new_recipients
						},
					'options': None
					}
				]
		reqResult = self.umcConnection.request('distribution/put', param, flavor)
		if not reqResult[0]['success']:
			utils.fail('Unable to edit project with params =(%r)' % (param,))
		else:
			self.description = description
			self.distributeType = distributeType
			self.distributeTime = distributeTime
			self.distributeDate = distributeDate
			self.collectType = collectType
			self.collectTime = collectTime
			self.collectDate = collectDate
			self.files = files
			self.recipients = recipients

	def get(self):
		"""Calls 'distribute/get'"""
		flavor = self.flavor
		reqResult = self.umcConnection.request(
				'distribution/get',
				[self.description],
				flavor)
		return reqResult[0]

	def idir(self, path):
		"""Dir a specific path.\n
		:param path: wanted path
		:type path: str
		:return: list of file names
		"""
		files = []
		for root, _ , filenames in os.walk(path):
			for f in filenames:
				files.append(os.path.relpath(os.path.join(root, f), path))
		return files

	def distribute(self):
		"""Calls 'distribution/distribute'"""
		print 'Distributing Project %s' % (self.name)
		flavor = self.flavor
		reqResult = self.umcConnection.request(
				'distribution/distribute',
				[self.name],
				flavor)
		if not reqResult[0]['success']:
			utils.fail('Unable to distribute project (%r)' % (self.name,))

	def check_distribute(self, users):
		"""Checks if the distribution was successful by checking the file system.\n
		:param users: names of users to have the material distributed for
		:type users: list of str
		"""
		print 'Checking %s distribution' % (self.name,)
		for user in users:
			files_path = '/home/{0}/schueler/{1}/Unterrichtsmaterial/{2}'.format(
					self.school,
					user,
					self.name)
			print 'file_path=', files_path
			existingFiles = self.idir(files_path)
			print 'existingFiles=', existingFiles
			if self.files != existingFiles:
				utils.fail('Project files were not distributed for user %s' % (user,))

	def collect(self):
		"""Calls 'distribution/collect'"""
		print 'Collecting Project %s' % (self.name)
		flavor = self.flavor
		reqResult = self.umcConnection.request(
				'distribution/collect',
				[self.name],
				flavor)
		if not reqResult[0]['success']:
			utils.fail('Unable to collect project (%r)' % (self.name,))

	def check_collect(self, users):
		"""Checks if the collection was successful by checking the file system.\n
		:param users: names of users to have the material collected form
		:type users: list of str
		"""
		print 'Checking %s collection' % (self.name,)
		for user in users:
			files_path = '/home/{0}/lehrer/{1}/Unterrichtsmaterial/{2}/{3}'.format(
					self.school,
					self.username,
					self.name,
					user)
			print 'file_path=', files_path
			existingFiles = self.idir(files_path)
			print 'existingFiles=', existingFiles
			if self.files != existingFiles:
				utils.fail('Project files were not collected for user %s' % (user,))

	def remove(self):
		"""Calls 'distribution/remove'"""
		print 'Removing Project %s' % (self.name)
		flavor = self.flavor
		param = [
				{
					'object': self.name,
					'options': None
					}
				]
		reqResult = self.umcConnection.request(
				'distribution/remove',
				param,
				flavor)
		if reqResult:
			utils.fail('Unable to remove project (%r)' % (param,))

	def check_remove(self):
		"""Calls 'distribution/query' and check the existance of the removed project"""
		print 'Checking %s removal' % (self.name,)
		current = self.query(self.name)
		if self.name in current:
			utils.fail('Project %s was not removed successfully' % (self.name,))

	def checkFiles(self, files):
		"""Calls 'distribution/checkfiles'"""
		print 'Checking files Project %s' % (self.name)
		flavor = self.flavor
		param = {
				'project': self.name,
				'filenames': files
				}
		reqResult = self.umcConnection.request(
				'distribution/checkfiles',
				param,
				flavor)
		if reqResult:
			utils.fail('Unable to chack files for project (%r)' % (param,))

	# FIXME under construction
	def check_put(self):
		"""Calls 'distribution/get' and check the existance of the added project"""
		print 'Checking %s modification' % (self.name,)
		found = self.get(self.description)
		current = {
				'files': self.files,
				'sender': self.username,
				'description': self.description,
				'recipients': self.recipients,
				'distributeType': self.distributeType,
				'__type__': 'PROJECT',
				'collectType': self.collectType,
				'name': self.name,
				'deadline': '%s %s' % (self.collectDate, self.collectTime),
				'starttime': '%s %s' % (self.distributeDate, self.distributeTime),
				'atJobNumDistribute': None,
				'atJobNumCollect': None
				}
		if self.name != current:
			utils.fail('Project %s was not modified successfully' % (self.name,))

	def adopt(self):
		pass
