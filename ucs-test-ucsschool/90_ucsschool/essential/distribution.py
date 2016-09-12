"""""""""""""""""""""""""""""""""""""""
  **Class Distribution**\n
"""""""""""""""""""""""""""""""""""""""
"""
.. module:: distribution
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""

from univention.testing.ucsschool import UMCConnection
import os
import time
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils


class Distribution(object):

	"""Contains the needed functionality for Materials distribution.
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
	:param sender: name of the creater user (teacher or admin)
	:type sender: str
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
			sender=None,
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
		account = utils.UCSTestDomainAdminCredentials()
		admin = account.username
		passwd = account.bindpw
		self.school = school
		self.name = name if name else uts.random_string()
		self.description = description if description else uts.random_string()
		if distributeTime:
			self.distributeTime = distributeTime
		else:
			self.distributeTime = time.strftime('%I:%M')
		if distributeDate:
			self.distributeDate = distributeDate
		else:
			self.distributeDate = time.strftime('%Y-%m-%d')
		self.collectTime = collectTime if collectTime else time.strftime(
			'%I:%M')
		self.collectDate = collectDate if collectDate else time.strftime(
			'%Y-%m-%d')
		self.distributeType = distributeType
		self.collectType = collectType
		self.files = files
		self.recipients = recipients
		self.ucr = ucr if ucr else ucr_test.UCSTestConfigRegistry()
		self.sender = sender if sender else admin
		self.flavor = flavor if flavor else 'admin'
		if umcConnection:
			self.umcConnection = umcConnection
		else:
			self.ucr.load()
			host = self.ucr.get('hostname')
			self.umcConnection = UMCConnection(host)
			self.umcConnection.auth(admin, passwd)

	def query(self, filt='private', pattern=''):
		"""Calles 'distribution/query'
		:param pattern: the pattern to use in the search
		:type pattern: str
		"""
		flavor = self.flavor
		param = {
			'filter': filt,
			'pattern': pattern
		}
		reqResult = self.umcConnection.request(
			'distribution/query',
			param,
			flavor)
		result = [x['name'] for x in reqResult if reqResult is not None]
		return result

	def get(self):
		"""Calls 'distribute/get'"""
		name = [self.name]
		reqResult = self.umcConnection.request('distribution/get', name, self.flavor)
		return reqResult[0]

	def idir(self, path):
		"""Dir a specific path.\n
		:param path: wanted path
		:type path: str
		:return: list of file names
		"""
		files = []
		for root, _, filenames in os.walk(path):
			for f in filenames:
				files.append(os.path.relpath(os.path.join(root, f), path))
		return files

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
		boundary = '---------------------------103454444410473823401882756'
		data = self.genData(file_name, content_type, boundary, self.flavor)
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
			'/univention-management-console/upload/distribution/upload',
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
		for filename, encoding in self.files:
			with open(filename, 'w') as g:
				g.write('test_content')
			self.uploadFile(filename, content_type)
		print 'Adding Project %s' % (self.name)
		flavor = self.flavor
		recipients = []
		for item in self.recipients:
			recipients.append(item.dn())
		print 'recipients=', recipients
		files = [file_name.decode(encoding).encode('UTF-8') for file_name, encoding in self.files]
		param = [
			{
				'object': {
					'collectDate': self.collectDate,
					'collectTime': self.collectTime,
					'collectType': self.collectType,
					'description': self.description,
					'distributeDate': self.distributeDate,
					'distributeTime': self.distributeTime,
					'distributeType': self.distributeType,
					'files': files,
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
		print 'reqResult =', reqResult
		if not reqResult[0]['success']:
			utils.fail('Unable to add project (%r)' % (param,))

	def check_add(self):
		"""Calls 'distribution/query'
		and check the existance of the added project
		"""
		print 'Checking %s addition' % (self.name,)
		current = self.query(pattern=self.name)
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
		:param description: description of the project to be added later
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
		:param recipients: groups which are included in the project
		:type recipients: list of group objects
		"""
		print 'Editing Project %s' % (self.name)
		description = description if description else self.description
		if distributeType:
			distributeType = distributeType
		else:
			distributeType = self.distributeType
		if distributeTime:
			distributeTime = distributeTime
		else:
			distributeTime = self.distributeTime
		if distributeDate:
			distributeDate = distributeDate
		else:
			distributeDate = self.distributeDate
		collectType = collectType if collectType else self.collectType
		collectTime = collectTime if collectTime else self.collectTime
		collectDate = collectDate if collectDate else self.collectDate
		files = files if files else [x for x, y in self.files]
		recipients = recipients if recipients else self.recipients
		new_recipients = []
		for item in recipients:
			new_recipients.append(item.dn())
		flavor = self.flavor
		param = [{
			'object': {
				'collectDate': collectDate,
				'collectTime': collectTime,
				'collectType': collectType,
				'description': description,
				'distributeDate': distributeDate,
				'distributeTime': distributeTime,
				'distributeType': distributeType,
				'files': files,
				'name': self.name,
				'recipients': new_recipients
			},
			'options': None
		}]
		reqResult = self.umcConnection.request(
			'distribution/put',
			param,
			flavor)
		print 'reqResult =', reqResult
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
			self.files = [(x, 'utf8') for x in files]
			self.recipients = recipients

	def check_put(self, previousGetResult):
		"""Calls 'distribution/get' and check the modified project
		:param previousGetResult: info from previous get
		:type previousGetResult: dict
		check changing sates for distribution and collection
		"""
		print 'Checking %s modification' % (self.name,)
		found = self.get()
		supposed = {
			'files': found['files'],
			'sender': found['sender'],
			'description': found['description'],
			'recipients': found['recipients'],
			'distributeType': found['distributeType'],
			'__type__': found['__type__'],
			'collectType': found['collectType'],
			'name': found['name'],
			'starttime': found['starttime'],
			'deadline': found['deadline']
		}
		recips = [{'id': y.dn(), 'label': y.name} for y in self.recipients]

		if self.distributeType != 'automatic':
			sTime = None
		else:
			sTime = '%s %s' % (self.distributeDate, self.distributeTime)
		if self.collectType != 'automatic':
			dTime = None
		else:
			dTime = '%s %s' % (self.collectDate, self.collectTime)
		current = {
			'files': [x for x, y in self.files],
			'sender': self.sender,
			'description': self.description,
			'recipients': recips,
			'distributeType': self.distributeType,
			'__type__': 'PROJECT',
			'collectType': self.collectType,
			'name': self.name,
			'starttime': sTime,
			'deadline': dTime,
		}
		print 'supposed = ', supposed
		print 'current = ', current

		fail_state = supposed != current
		if fail_state:
			utils.fail(
				'Project %s was not modified successfully,supposed!=current' %
				(self.name,))

		# check distribute
		check = 'distribution'
		before_type = previousGetResult['distributeType']
		after_type = found['distributeType']
		before_time = previousGetResult['starttime']
		after_time = found['starttime']
		before_atJob = previousGetResult['atJobNumDistribute']
		after_atJob = found['atJobNumDistribute']
		fail_state = fail_state or self.put_fail(
				before_type,
				after_type,
				before_time,
				after_time,
				before_atJob,
				after_atJob)
		if fail_state:
			utils.fail(
				'Project %s was not modified successfully, %s: %s -> %s' %
				(self.name, check, before_type, after_type))

		# check collect
		check = 'collection'
		before_type = previousGetResult['collectType']
		after_type = found['collectType']
		before_time = previousGetResult['deadline']
		after_time = found['deadline']
		before_atJob = previousGetResult['atJobNumCollect']
		after_atJob = found['atJobNumCollect']
		fail_state = fail_state or self.put_fail(
				before_type,
				after_type,
				before_time,
				after_time,
				before_atJob,
				after_atJob)
		if fail_state:
			utils.fail(
				'Project %s was not modified successfully, %s: %s -> %s' %
				(self.name, check, before_type, after_type))

	def put_fail(
			self,
			before_type,
			after_type,
			before_time,
			after_time,
			before_atJob,
			after_atJob):
		"""Checks if the atjobs are in the expected formats
		:param before_type: type before using put command
		:type before_type: str
		:param after_type: type after using put command
		:type after_type: str
		:param before_atJob: atJobNum before using put command
		:type before_atJob: str or None
		:param after_atJob: atJobNum after using put command
		:type after_atJob: str or None
		:param before_time: time before using put command
		:type before_time: str
		:param after_time: time after using put command
		:type after_time: str
		"""
		fail_state = False
		# manual -> manual
		# atJobs == don't care
		if before_type == 'manual' and after_type == 'manual':
			pass

		# manual -> automatic
		# atJobs don't care -> int
		if before_type == 'manual' and after_type == 'automatic':
			fail_state = not (isinstance(after_atJob, (int, long)))

		# automatic -> manual
		# atJobs int -> don't care
		if before_type == 'automatic' and after_type == 'manual':
			fail_state = not (isinstance(before_atJob, (int, long)))

		# automatic -> automatic
		# atJobs int1 -> int2 & int1 < int2
		if before_type == 'automatic' and after_type == 'automatic':
			fail1 = not (
				isinstance(
					before_atJob, (int, long)) and isinstance(
					after_atJob, (int, long)))
			fail2 = not (
				before_time != after_time and (
					before_atJob < after_atJob))
			fail_state = fail1 or fail2
		return fail_state

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
		"""Checks if the distribution was successful
		by checking the file system.\n
		:param users: names of users to have the material distributed for
		:type users: list of str
		"""
		print 'Checking %s distribution' % (self.name,)
		for user in users:
			path = self.getUserFilesPath(user, 'distribute')
			print 'file_path=', path
			existingFiles = self.idir(path)
			print 'existingFiles=', existingFiles
			files = [x for x, y in self.files]
			if files != existingFiles:
				utils.fail(
					'Project files were not distributed for user %s' %
					(user,))

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
		"""Checks if the collection was successful
		by checking the file system.\n
		:param users: names of users to have the material collected form
		:type users: list of str
		"""
		print 'Checking %s collection' % (self.name,)
		for user in users:
			path = self.getUserFilesPath(user, 'collect')
			print 'file_path=', path
			existingFiles = self.idir(path)
			print 'existingFiles=', existingFiles
			files = [x for x, y in self.files]
			if files != existingFiles:
				utils.fail(
					'Project files were not collected for user %s' %
					(user,))

	def remove(self):
		"""Calls 'distribution/remove'"""
		print 'Removing Project %s' % (self.name)
		flavor = self.flavor
		param = [{
			'object': self.name,
			'options': None
		}]
		reqResult = self.umcConnection.request(
			'distribution/remove',
			param,
			flavor)
		if reqResult:
			utils.fail('Unable to remove project (%r)' % (param,))

	def check_remove(self):
		"""Calls 'distribution/query'
		and check the existance of the removed project
		"""
		print 'Checking %s removal' % (self.name,)
		current = self.query(pattern=self.name)
		if self.name in current:
			utils.fail(
				'Project %s was not removed successfully' %
				(self.name,))

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

	def adopt(self, project_name):
		"""Calls 'distribute/adopt'"""
		print 'Adopting project', self.name
		flavor = self.flavor
		reqResult = self.umcConnection.request(
			'distribution/adopt',
			[project_name],
			flavor)
		if reqResult:
			utils.fail('Failed to adopt project (%r)' % (project_name,))

	def check_adopt(self, project_name):
		print 'Checking adopting'
		q = self.query(pattern=project_name)
		if not (project_name in q):
			utils.fail(
				'Project %s was not adopted successfully' %
				(project_name,))

	def getUserFilesPath(self, user, purpose='distribute'):
		"""Gets the correct files path for a specific user depending on
		the value of the ucr variable ucsschool/import/roleshare.\n
		:param user: user name
		:type user: str
		:param purpose: either for distribution or collection
		:type purpose: str ('distribute' or 'collect')
		"""
		path = ''
		self.ucr.load()
		roleshare = self.ucr.get('ucsschool/import/roleshare')
		if purpose == 'distribute':
			if roleshare == 'no' or roleshare is False:
				path = '/home/{0}/Unterrichtsmaterial/{1}/'.format(user, self.name)
			else:
				path = '/home/{0}/schueler/{1}/Unterrichtsmaterial/{2}'.format(
					self.school,
					user,
					self.name)
		elif purpose == 'collect':
			if roleshare == 'no' or roleshare is False:
				path = '/home/{0}/Unterrichtsmaterial/{1}/{2}/'.format(
						self.sender,
						self.name,
						user)
			else:
				path = '/home/{0}/lehrer/{1}/Unterrichtsmaterial/{2}/{3}'.format(
					self.school,
					self.sender,
					self.name,
					user)
		return path
