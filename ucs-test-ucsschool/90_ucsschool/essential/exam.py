"""""""""""""""""""""""""""""""""""""""
  **Class Exam**\n
"""""""""""""""""""""""""""""""""""""""
"""
.. module:: exam
	:platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""

from univention.lib.umc_connection import UMCConnection
import glob
import os
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils


class StartFail(Exception):
	pass

class FinishFail(Exception):
	pass

def get_dir_files(dir_path, recursive=True):
	result = []
	for f in glob.glob('%s/*' % dir_path):
		if os.path.isfile(f):
			result.append(os.path.basename(f))
		if os.path.isdir(f) and	recursive:
			result.extend(get_dir_files(f))
	return result


class Exam(object):
	"""Contains the needed functionality for exam module.\n
	:param school: name of the school
	:type school: str
	:param room: name of room of the exam
	:type room: str
	:param examEndTime: exam end time
	:type examEndTime: str in format "HH:mm"
	:param name: name of the exam to be created later
	:type name: str
	:param recipients: names of the classes to make the exam
	:type recipients: list of str
	:param directory: name of the directory for the exam, default=name
	:type directory: str
	:param files: list of files to be uploaded to the exam directory
	:type files: list of str
	:param sharemode: sharemode
	:type sharemode: str either "home" or "all"
	:param internetRule: name of the internet Rule to be applied in the exam
	:type internetRule: str
	:param customRule: cutom internet rule
	:type customRule: str
	:param umcConnection:
	:type umcConnection: UMC connection object
	"""
	def __init__(
			self,
			school,
			room,			# room dn
			examEndTime,	# in format "HH:mm"
			recipients,		# list of classes dns
			name=None,
			directory=None,
			files=[],
			shareMode='home',
			internetRule=None,
			customRule='',
			umcConnection=None
			):
		self.school = school
		self.room = room
		self.examEndTime = examEndTime
		self.recipients = recipients

		self.name = name if name else uts.random_name()
		self.directory = directory if directory else self.name
		self.files = files
		self.shareMode = shareMode
		self.internetRule = internetRule
		self.customRule = customRule

		if umcConnection:
			self.umcConnection = umcConnection
		else:
			self.ucr = ucr_test.UCSTestConfigRegistry()
			self.ucr.load()
			host = self.ucr.get('ldap/master')
			self.umcConnection = UMCConnection(host)
			account = utils.UCSTestDomainAdminCredentials()
			admin = account.username
			passwd = account.bindpw
			self.umcConnection.auth(admin, passwd)

	def start(self):
		"""Starts an exam"""
		param = {
				'school': self.school,
				'name': self.name,
				'room': self.room,
				'examEndTime': self.examEndTime,
				'recipients': self.recipients,
				'directory': self.directory,
				'files': self.files,
				'shareMode': self.shareMode,
				'internetRule': self.internetRule,
				'customRule': self.customRule
				}
		print 'Starting exam %s in room %s' % (
				self.name,
				self.room
				)
		print 'param = %s' % param
		reqResult = self.umcConnection.request(
				'schoolexam/exam/start',
				param
				)
		print 'REQ RESULT = ', reqResult
		if not reqResult['success']:
			raise StartFail('Unable to start exam (%r)' % (param,))

	def finish(self):
		"""Finish an exam"""
		param = {
				'exam': self.name,
				'room': self.room
				}
		print 'Finishing exam %s in room %s' % (
				self.name,
				self.room
				)
		print 'param = %s' % param
		reqResult = self.umcConnection.request(
				'schoolexam/exam/finish',
				param
				)
		print 'REQ RESULT = ', reqResult
		if not reqResult['success']:
			raise FinishFail('Unable to finish exam (%r)' % param)


	def genData(self, file_name, content_type, boundary):
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
Content-Disposition: form-data; name="iframe"

false
--{0}
Content-Disposition: form-data; name="uploadType"

html5
--{0}--
""".format(boundary, os.path.basename(file_name), content_type, f.read())
		return data.replace("\n", "\r\n")

	def uploadFile(self, file_name, content_type='application/octet-stream'):
		"""Uploads a file via http POST request.\n
		:param file_name: file name to be uploaded
		:type file_name: str
		:param content_type: type of the content of the file
		:type content_type: str ('application/octet-stream',..)
		"""
		print 'Uploading file %s' % file_name
		boundary = '---------------------------12558488471903363215512784168'
		data = self.genData(file_name, content_type, boundary)
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
			'/umcp/upload/schoolexam/upload',
			data,
			headers=headers)
		r = httpcon.getresponse().status
		print 'R=', r
		if r != 200:
			print 'httpcon.response().status=', r
			utils.fail('Unable to upload the file.')

	def get_internetRules(self):
		"""Get internet rules"""
		reqResult = self.umcConnection.request('schoolexam/internetrules',{})
		print 'InternetRules = ', reqResult
		return reqResult

	def fetch_internetRule(self, internetRule_name):
		if internetRule_name not in self.get_internetRules():
			utils.fail('Exam %s was not able to fetch internet rule %s' % (self.name, internetRule_name))

	def get_schools(self):
		"""Get schools"""
		reqResult = self.umcConnection.request('schoolexam/schools',{})
		schools = [x['label'] for x in reqResult]
		print 'Schools = ', schools
		return schools


	def fetch_school(self, school):
		if school not in self.get_schools():
			utils.fail('Exam %s was not able to fetch school %s' % (self.name, school))

	def get_groups(self):
		"""Get groups"""
		reqResult = self.umcConnection.request(
				'schoolexam/groups',
				{
					'school':self.school,
					'pattern':''
					}
				)
		groups = [x['label'] for x in reqResult]
		print 'Groups = ', groups
		return groups

	def fetch_groups(self, group):
		if group not in self.get_groups():
			utils.fail('Exam %s was not able to fetch group %s' % (self.name, group))

	def get_lessonEnd(self):
		"""Get lessonEnd"""
		reqResult = self.umcConnection.request('schoolexam/lesson_end',{})
		print 'Lesson End = ', reqResult
		return reqResult

	def fetch_lessonEnd(self, lessonEnd):
		if lessonEnd not in self.get_lessonEnd():
			utils.fail('Exam %s was not able to fetch lessonEnd %s' % (self.name, lessonEnd))

	def collect(self):
		"""Collect results"""
		reqResult = self.umcConnection.request('schoolexam/exam/collect',{'exam':self.name})
		print 'Collect = ', reqResult
		return reqResult

	def check_collect(self):
		account = utils.UCSTestDomainAdminCredentials()
		admin = account.username
		path = '/home/%s/Klassenarbeiten/%s' % (admin, self.name)
		path_files = get_dir_files(path)
		if not set(self.files).issubset(set(path_files)):
			utils.fail('%r were not collected to %r' % (self.files, path))

	def check_upload(self):
		path = '/tmp/ucsschool-exam-upload*'
		path_files = get_dir_files(path)
		if not set(self.files).issubset(set(path_files)):
			utils.fail('%r were not uploaded to %r' % (self.files, path))

	def check_distribute(self):
		path = '/home/%s/schueler' %  self.school
		path_files = get_dir_files(path)
		if not set(self.files).issubset(set(path_files)):
			utils.fail('%r were not uploaded to %r' % (self.files, path))

