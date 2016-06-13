# -*- coding: utf-8 -*-

import univention.testing.ucr as ucr_test
from univention.testing.ucsschool import UMCConnection
import univention.testing.strings as uts
import univention.testing.utils as utils
import tempfile
import re
from pprint import pprint
from essential.user import User


class FailHTTPStatus(Exception):
	pass


class FailShow(Exception):
	pass


class FailProgress(Exception):
	pass


class FailImport(Exception):
	pass


class FailUploadFile(Exception):
	pass


class FailRecheck(Exception):
	pass


class FailSchools(Exception):
	pass


class FailErrors(Exception):
	pass


class FailWarnings(Exception):
	pass


class CSVImport(object):

	"""CSVImport class, inclues all the needed operations to perform a user import"""

	def __init__(self, school, user_type):
		self.school = school
		self.user_type = user_type
		self.ucr = ucr_test.UCSTestConfigRegistry()
		self.ucr.load()
		host = self.ucr.get('hostname')
		self.umc_connection = UMCConnection(host)
		account = utils.UCSTestDomainAdminCredentials()
		admin = account.username
		passwd = account.bindpw
		self.umc_connection.auth(admin, passwd)

	def genData(self, boundary, file_name, content_type, school, user_type, delete_not_mentioned):
		"""Generates data in the form to be sent via http POST request.\n
		:param file_name: file name to be uploaded
		:type file_name: str
		:param content_type: type of the content of the file
		:type content_type: str  = 'text/csv'
		:param boundary: the boundary
		:type boundary: str (-------123091)
		:param flavor: flavor of the acting user
		:type flavor: str
		"""
		with open(file_name, 'r') as f:
			if delete_not_mentioned:
				data = r"""--{0}
Content-Disposition: form-data; name="uploadedfile"; filename="{1}"
Content-Type: {2}

{3}
--{0}
Content-Disposition: form-data; name="school"

{4}
--{0}
Content-Disposition: form-data; name="type"

{5}
--{0}
Content-Disposition: form-data; name="delete_not_mentioned"

true
--{0}
Content-Disposition: form-data; name="iframe"

false
--{0}
Content-Disposition: form-data; name="uploadType"

html5
--{0}--
""".format(boundary, file_name, content_type, f.read(), school, user_type)
			else:
				data = r"""--{0}
Content-Disposition: form-data; name="uploadedfile"; filename="{1}"
Content-Type: {2}

{3}
--{0}
Content-Disposition: form-data; name="school"

{4}
--{0}
Content-Disposition: form-data; name="type"

{5}
--{0}
Content-Disposition: form-data; name="iframe"

false
--{0}
Content-Disposition: form-data; name="uploadType"

html5
--{0}--
""".format(boundary, file_name, content_type, f.read(), school, user_type)
		return data.replace("\n", "\r\n")

	def uploadFile(self, file_name, content_type, delete_not_mentioned, expected_upload_status):
		"""Uploads a file via http POST request.\n
		:param file_name: file name to be uploaded
		:type file_name: str
		:param content_type: type of the content of the file
		:type content_type: str ('text/csv')
		"""
		print 'Uploading file %r' % file_name
		boundary = '---------------------------18209455381072592677374099768'
		data = self.genData(boundary, file_name, content_type, self.school, self.user_type, delete_not_mentioned)
		headers = dict(self.umc_connection._headers)  # copy headers!
		httpcon = self.umc_connection.get_connection()
		header_content = {
			'Content-Type': 'multipart/form-data; boundary=%s' % (boundary,)
		}
		headers.update(header_content)
		headers['Cookie'] = headers['Cookie'].split(";")[0]
		headers['Accept'] = 'application/json'
		try:
			httpcon.request(
				"POST",
				'/univention-management-console/upload/schoolcsvimport/save',
				data,
				headers=headers)
			response = httpcon.getresponse()
			status = response.status
			if status != expected_upload_status:
				print "DEBUG: request response message = ", response.msg, response.reason, response.read()
				raise FailHTTPStatus('Unexpected httpcon.response().status=%r' % status)
			elif status == 200:
				response_text = response.read()
				# replace some string values with other types
				rep = {'null': 'None', 'true': 'True'}
				pattern = re.compile("|".join(rep.keys()))
				response_dict = eval(pattern.sub(lambda m: rep[re.escape(m.group(0))], response_text))
				self.file_id = response_dict['result'][0]['file_id']
				self.id_nr = 1
			else:
				print 'Expected http_status = %r' % status
		except FailUploadFile:
			raise
		return status

	def show(self):
		param = {
			'file_id': self.file_id,
			'columns': ["name", "firstname", "lastname", "birthday", "password", "email", "school_classes"],
		}
		if self.user_type == 'staff':
			param['columns'].remove('school_classes')
		try:
			reqResult = self.umc_connection.request('schoolcsvimport/show', param)
			self.id_nr = reqResult['id']
		except FailShow:
			raise

	def progress(self):
		param = {
			'progress_id': self.id_nr
		}
		try:
			reqResult = self.umc_connection.request('schoolcsvimport/progress', param)
		except FailProgress:
			raise
		return reqResult

	def recheck(self, user):
		param = {
			'file_id': self.file_id,
			'user_attrs': [user]
		}
		try:
			reqResult = self.umc_connection.request('schoolcsvimport/recheck', param)
			print 'RECHECK RESULT = ', reqResult
			return reqResult
		except FailRecheck:
			raise

	def schools(self):
		try:
			reqResult = self.umc_connection.request('schoolcsvimport/schools', {})
		except FailSchools:
			raise
		return [x['id'] for x in reqResult]

	def check_schools(self):
		if self.school not in self.schools():
			raise FailSchools('School %s not found by request: schoolcsvimport/schools' % (self.school))

	def write_import_file(self, filename, lines, has_header=True):
		with open(filename, 'wb') as f:
			f.write(''.join(lines))
			f.flush()

	def read_import_file(self, filename, has_header=True):
		with open(filename, 'rb') as f:
			lines = f.readlines()
		if has_header:
			columns = lines[0][:-1].split(',')
			lines = lines[1:]
		else:
			columns = []
		lines = [x[:-1] for x in lines]
		return lines, columns

	def import_users(self, users):
		line_nr = 1
		param = []

		def get_type_name(typ):
			if typ == 'cSVStudent':
				return 'Student'
			elif typ == 'cSVTeacher':
				return 'Teacher'
			elif typ == 'cSVStaff':
				return 'Staff'
			elif typ == 'cSVTeachersAndStaff':
				return 'Teacher and Staff'
		for user in users:
			user.update({'line': line_nr})
			user.update({'type_name': get_type_name(user['type'])})
			options = {
				'file_id': self.file_id,
				'attrs': user
			}
			line_nr += 1
			param.append(options)
		try:
			pprint(('Importing users with parameters=', param))
			reqResult = self.umc_connection.request('schoolcsvimport/import', param)
			self.id_nr = reqResult['id']
			utils.wait_for_replication()
		except FailImport:
			raise


def verify_persons(persons_list):
	for person in persons_list:
		person.verify()


def update_persons(school, persons_list, users):
	def get_role(typ):
		if typ == 'cSVStudent':
			return 'student'
		elif typ == 'cSVTeacher':
			return 'teacher'
		elif typ == 'cSVStaff':
			return 'staff'
		elif typ == 'cSVTeachersAndStaff':
			return 'teacher_staff'

	def get_mode(action):
		if action == 'delete':
			return 'D'
		elif action == 'create':
			return 'A'
		elif action == 'modify':
			return 'M'
	users = [x for y in users for x in y]
	for user in users:
		person = User(
			school,
			role=get_role(user['type']),
			school_classes=user.get('school_classes', {}),
			mode=get_mode(user['action']),
			username=user['name'],
			firstname=user['firstname'],
			lastname=user['lastname'],
			password=user['password'],
			mail=user.get('email'),
		)
		person_old_version = [x for x in persons_list if x.username == person.username]
		if person_old_version:
			persons_list.remove(person_old_version[0])
			persons_list.append(person)
		else:
			persons_list.append(person)


def random_email():
	"""Create random email in the current domainname"""
	ucr = ucr_test.UCSTestConfigRegistry()
	ucr.load()
	return '%s@%s' % (uts.random_name(), ucr.get('domainname'))


def random_line_stu_tea():
	"""create random line to import random student/teacher/teacher and staff"""
	return '%s,%s,%s,%s%s.%s%s.%s,%s,%s,%s\n' % (
			uts.random_username(),
			uts.random_name(),
			uts.random_name(),
			uts.random_int(1, 2),
			uts.random_int(1, 8),
			uts.random_int(0, 0),
			uts.random_int(1, 9),
			uts.random_int(1980, 2014),
			uts.random_name(),
			random_email(),
			uts.random_string(),
	)


def random_line_staff():
	"""create random line to import random staff"""
	return '%s,%s,%s,%s%s.%s%s.%s,%s,%s\n' % (
			uts.random_username(),
			uts.random_name(),
			uts.random_name(),
			uts.random_int(0, 2),
			uts.random_int(1, 8),
			uts.random_int(0, 0),
			uts.random_int(1, 9),
			uts.random_int(1980, 2014),
			uts.random_name(),
			random_email(),
	)


def staff_file(nr_of_lines):
	"""Creates random contents of file ready to import staff"""
	result = ['Username,First name,Last name,Birthday,Password,Email\n']
	for i in xrange(nr_of_lines):
		result.append(random_line_staff())
	return result


def stu_tea_file(nr_of_lines):
	"""Creates random contents of file ready to import student/teacher/teacher and staff"""
	result = ['Username,First name,Last name,Birthday,Password,Email,Class\n']
	for i in xrange(nr_of_lines):
		result.append(random_line_stu_tea())
	return result


def check_import_users(school, user_types, files, delete_not_mentioned, expected_upload_status, expected_errors, expected_warnings):
	"""Import users from the passed files and check the returned errors and warnings"""
	users = []
	counter = 0
	for user_type, lines in zip(user_types, files):
		print '(', counter, ')', '-' * 59
		print ' ** (User Type = %s, expected_upload_status = %r )' % (user_type, expected_upload_status)
		print ' ** delete not mentioned = ', delete_not_mentioned
		print ' ** lines =  %r' % (lines,)
		f = tempfile.NamedTemporaryFile(dir='/tmp')
		m = CSVImport(school=school, user_type=user_type)
		m.check_schools()
		m.write_import_file(f.name, lines)
		upload_status = m.uploadFile(f.name, 'text/csv', delete_not_mentioned, expected_upload_status)
		if upload_status == 200:
			m.show()
			while True:
				prog = m.progress()
				if prog['finished']:
					users.append(prog['result']['users'])
					break
			lines, columns = m.read_import_file(f.name)
			m.import_users(users[counter])
			counter += 1
			while True:
				prog2 = m.progress()
				if prog2['finished']:
					break
			f.close()
	users = [[x for x in y] for y in users]
	pprint(('Users = ', users))
	errors = [x['errors'] for y in users for x in y if x['errors']]
	errors_keys = [k for x in errors for k, v in x.iteritems()]
	print 'ERRORS_KEYS=', errors_keys
	if sorted(expected_errors) != sorted(errors_keys):
		raise FailErrors('current error keys = %r, expected Errors = %r' % (errors_keys, expected_errors))
	warnings = [x['warnings'] for y in users for x in y if x['warnings']]
	warnings_keys = [k for x in warnings for k, v in x.iteritems()]
	print 'WARNINGS_KEYS=', warnings_keys
	if sorted(expected_warnings) != sorted(warnings_keys):
		raise FailWarnings('current warning keys= %r, expected warnings = %r' % (warnings_keys, expected_warnings))
	return users, errors, warnings


def get_usernames(files):
	"""retrieve usernames from an import file"""
	return [x.split(',')[0] for x in files if x.split(',')[0] != 'Username']


def transform_usernames(files_01, files_02, nr_of_lines):
	"""Assign the usernames from files_01 to users from files_02"""
	for i, files in enumerate(files_01):
		usernames = get_usernames(files)
		for j in xrange(1, nr_of_lines + 1):
			line = files_02[i][j].split(',')
			line[0] = usernames[j - 1]
			files_02[i][j] = ','.join(line)
