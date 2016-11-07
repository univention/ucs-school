#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: Distribution Module
#
# Copyright 2007-2016 Univention GmbH
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

import os
import re
import json
import shutil
import traceback
from pipes import quote
from datetime import datetime

from univention.lib import atjobs
from univention.lib.i18n import Translation
from univention.management.console.log import MODULE
from univention.management.console.config import ucr

#import univention.admin.modules as udm_modules
import univention.admin.uexceptions as udm_exceptions

import ucsschool.lib.models

_ = Translation('ucs-school-umc-distribution').translate

DISTRIBUTION_CMD = '/usr/lib/ucs-school-umc-distribution/umc-distribution'
DISTRIBUTION_DATA_PATH = ucr.get('ucsschool/datadistribution/cache', '/var/lib/ucs-school-umc-distribution')
POSTFIX_DATADIR_SENDER = ucr.get('ucsschool/datadistribution/datadir/sender', 'Unterrichtsmaterial')
POSTFIX_DATADIR_RECIPIENT = ucr.get('ucsschool/datadistribution/datadir/recipient', 'Unterrichtsmaterial')

TYPE_USER = 'USER'
TYPE_GROUP = 'GROUP'
TYPE_PROJECT = 'PROJECT'


class DistributionException(Exception):
	pass


class InvalidProjectFilename(DistributionException):
	pass


class _Dict(object):

	'''Custom dict-like class. The initial set of keyword arguments is stored
	in an internal dict. Entries of this intial set can be accessed directly
	on the object (myDict.myentry = ...).'''

	def __init__(self, type, **initDict):
		initDict['__type__'] = type
		object.__setattr__(self, '_dict', initDict)

	# overwrite __setattr__ such that, e.g., project.cachedir can be called directly
	def __setattr__(self, key, value):
		_dict = object.__getattribute__(self, '_dict')

		# check whether the class has the specified attribute
		hasAttr = True
		try:
			object.__getattribute__(self, key)
		except AttributeError:
			hasAttr = False

		if not hasAttr and key in _dict:
			# if the key is in the internal dict, update its value
			_dict[key] = value
		else:
			# default
			object.__setattr__(self, key, value)

	# overwrite __getattribute__ such that, e.g., project.cachedir can be called directly
	def __getattribute__(self, key):
		_dict = object.__getattribute__(self, '_dict')

		# check whether the class has the specified attribute
		hasAttr = True
		try:
			object.__getattribute__(self, key)
		except AttributeError:
			hasAttr = False

		if not hasAttr and key in _dict:
			# if the key is in the internal dict, return its value
			return _dict[key]
		# default
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

	@property
	def type(self):
		return self.__type__


class _DictEncoder(json.JSONEncoder):

	'''A custom JSONEncoder class that can encode _Dict objects.'''

	def default(self, obj):
		if isinstance(obj, _Dict):
			return obj.dict
		return json.JSONEncoder.default(self, obj)


def jsonEncode(val):
	'''Encode to JSON using the custom _Dict encoder.'''
	return _DictEncoder(indent=2).encode(val)


def jsonDecode(val):
	'''Decode a JSON string and replace dict types with _Dict.'''
	def _dict_type(x):
		if x['__type__'] == TYPE_USER:
			return User(**x)
		elif x['__type__'] == TYPE_GROUP:
			return Group(**x)
		elif x['__type__'] == TYPE_PROJECT:
			return Project(**x)
		else:
			return _Dict(**x)

	return json.loads(val, object_hook=_dict_type)


class User(_Dict):

	def __init__(self, *args, **_props):
		# init empty project dict
		_Dict.__init__(self, TYPE_USER,
			unixhome='',
			username='',
			uidNumber='',
			gidNumber='',
			firstname='',
			lastname='',
			dn=''
		)

		# update specified entries
		if len(args):
			self.update(args[0])
		self.update(_props)

	# shortcut :)
	@property
	def homedir(self):
		return self.unixhome


class Group(_Dict):

	def __init__(self, *args, **_props):
		_Dict.__init__(self, TYPE_GROUP,
						dn='',
						name='',
						members=[]
						)
		# update specified entries
		if len(args):
			self.update(args[0])
		self.update(_props)


def openRecipients(entryDN, ldap_connection):
	try:
		group_ = ucsschool.lib.models.Group.from_dn(entryDN, None, ldap_connection)
	except udm_exceptions.noObject:  # either not existant or not a groups/group object
		try:
			user = ucsschool.lib.models.User.from_dn(entryDN, None, ldap_connection)
		except udm_exceptions.noObject as exc:
			MODULE.error('%s is neither a group nor a user: %s' % (entryDN, exc))
			return  # neither a user nor a group. probably object doesn't exists
		return User(user.get_udm_object(ldap_connection).info, dn=user.dn)
	else:
		if not group_.self_is_workgroup() and not group_.self_is_class():
			MODULE.error('%s is not a school class or workgroup but %r' % (group_.dn, type(group_).__name__))
			return
		group = Group(group_.get_udm_object(ldap_connection).info, dn=group_.dn)
		if group_.school:
			name_pattern = re.compile('^%s-' % (re.escape(group_.school)), flags=re.I)
			group.name = name_pattern.sub('', group.name)
		for userdn in group_.users:
			try:
				user = ucsschool.lib.models.User.from_dn(userdn, None, ldap_connection)
			except udm_exceptions.noObject as exc:
				MODULE.warn('User %r does not exists: %s' % (userdn, exc))
				continue  # no user or doesn't exists
			except udm_exceptions.base as exc:
				MODULE.error('Cannot open user %r: %s' % (userdn, exc))
				continue

			if not user.is_student(ldap_connection):
				# only add students and exam students
				MODULE.info('ignoring non student %r' % (userdn,))

			group.members.append(User(user.get_udm_object(ldap_connection).info, dn=user.dn))
		return group


class Project(_Dict):

	def __init__(self, *args, **_props):
		# init empty project dict
		_Dict.__init__(self, TYPE_PROJECT,
			name=None,
			description=None,
			files=[],
			starttime=None,  # str
			deadline=None,  # str
			atJobNumDistribute=None,  # int
			atJobNumCollect=None,  # int
			sender=None,  # User
			recipients=[],  # [ (User|Group) , ...]
		)

		# update specified entries
		if len(args):
			self.update(args[0])
		else:
			self.update(_props)

	@property
	def projectfile(self):
		'''The absolute project path to the project file.'''
		return os.path.join(DISTRIBUTION_DATA_PATH, self.name)

	@property
	def cachedir(self):
		'''The absolute path of the project cache directory.'''
		return os.path.join(DISTRIBUTION_DATA_PATH, '%s.data' % self.name)

	@property
	def sender_projectdir(self):
		'''The absolute path of the project directory in the senders home.'''
		if self.sender and self.sender.homedir:
			return os.path.join(self.sender.homedir, POSTFIX_DATADIR_SENDER, self.name)
		return None

	@property
	def atJobDistribute(self):
		return atjobs.load(self.atJobNumDistribute)

	@property
	def atJobCollect(self):
		return atjobs.load(self.atJobNumCollect)

	def user_projectdir(self, user):
		'''Return the absolute path of the project dir for the specified user.'''
		return os.path.join(user.homedir, POSTFIX_DATADIR_RECIPIENT, self.name)

	@property
	def isDistributed(self):
		'''True if files have already been distributed.'''
		# distributed files can still be found in the internal property 'files',
		# however, upon distribution they are removed from the cache directory;
		# thus, if one of the specified files does not exist, the project has
		# already been distributed
		files = [ifn for ifn in self.files if os.path.exists(os.path.join(self.cachedir, ifn))]
		return len(files) != len(self.files)

	def _convStr2Time(self, key):
		'''Converts the string value of the specified key in the internal dict
		to a datetime instance.'''
		_dict = object.__getattribute__(self, '_dict')
		try:
			return datetime.strptime(_dict.get(key), '%Y-%m-%d %H:%M')
		except (ValueError, TypeError):
			pass
		return None

	def _convTime2String(self, key, time):
		'''Converts the time value of the specified key to string and saves it to
		the internal dict. Parameter time may an instance of string or datetime.'''
		_dict = object.__getattribute__(self, '_dict')
		if time is None:
			# unset value
			_dict[key] = None
		elif isinstance(time, basestring):
			# a string a saved directly to the internal dict
			_dict[key] = time
		elif isinstance(time, datetime):
			# a datetime instance is converted to string
			_dict[key] = datetime.strftime(time, '%Y-%m-%d %H:%M')
		else:
			raise ValueError('property "%s" needs to be of type str or datetime' % key)

	@property
	def starttime(self):
		return self._convStr2Time('starttime')

	@starttime.setter
	def starttime(self, time):
		self._convTime2String('starttime', time)

	@property
	def deadline(self):
		return self._convStr2Time('deadline')

	@deadline.setter
	def deadline(self, time):
		self._convTime2String('deadline', time)

	def validate(self):
		'''Validate the project data. In case of any errors with the data,
		a ValueError with a proper error message is raised.'''
		if not (isinstance(self.name, basestring) and self.name):
			raise ValueError(_('The given project directory name must be non-empty.'))
		# disallow certain characters to avoid problems in Windows/Mac/Unix systems:
		# http://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words
		for ichar in ('/', '\\', '?', '%', '*', ':', '|', '"', '<', '>', '$', "'"):
			if self.name.find(ichar) >= 0:
				raise ValueError(_('The specified project directory may not contain the character "%s".') % ichar)
		if self.name in ('..', '.') >= 0:
			raise ValueError(_('The specified project directory must be different from "." and "..".'))
		if self.name.startswith('.') or self.name.endswith('.'):
			raise ValueError(_('The specified project directory may not start nor end with a ".".'))
		if self.name.endswith(' ') or self.name.startswith(' '):
			raise ValueError(_('The specified project directory may not end with a space.'))
		if len(self.name) >= 255:
			raise ValueError(_('The specified project directory may at most be 254 characters long.'))
		if not (isinstance(self.description, basestring) and self.description):
			raise ValueError(_('The given project description must be non-empty.'))
		#if not (isinstance(self.files, list)): # and self.files):
		#	raise ValueError(_('At least one file must be specified.'))
		#if not (isinstance(self.recipients, list)): # and self.recipients):
		#	raise ValueError(_('At least one recipient must be specified.'))
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
		return any(iuser for iuser in self.getRecipients() if os.path.exists(self.user_projectdir(iuser)))

	def save(self):
		'''Save project data to disk and create job. In case of any errors, an IOError is raised.'''
		backupFile = '.%s.bak' % self.projectfile
		try:
			# update at-jobs
			self._unregister_at_jobs()
			self._register_at_jobs()

			# try to save backup of old file
			try:
				os.rename(self.projectfile, backupFile)
			except (OSError, IOError) as e:
				pass

			# save the project file
			with open(self.projectfile, 'w') as fd:
				fd.write(jsonEncode(self))

			# create cache directory
			self._createCacheDir()
		except (OSError, IOError) as e:
			# try to restore backup copy
			try:
				os.rename(backupFile, self.projectfile)
			except (OSError, IOError) as e:
				pass

			# raise a new IOError
			raise IOError(_('Could not save project file: %s (%s)') % (self.projectfile, str(e)))

		# try to remove backup file
		try:
			os.remove(backupFile)
		except (OSError, IOError) as e:
			pass

	def _createCacheDir(self):
		'''Create cache directory.'''
		# create project cache directory
		MODULE.info('creating project cache dir: %s' % self.cachedir)
		try:
			os.makedirs(self.cachedir, 0o700)
			os.chown(self.cachedir, 0, 0)
		except (OSError, IOError) as exc:
			if exc.errno == 17:
				MODULE.info('cache dir %s exists.' % self.cachedir)
			else:
				MODULE.error('Failed to create cachedir: %s' % (exc,))

	def _createProjectDir(self):
		'''Create project directory in the senders home.'''
		if not self.sender:
			return

		self._create_project_dir(self.sender, self.sender_projectdir)

		if not self.sender_projectdir:
			MODULE.error('ERROR: Sender information is not specified, cannot create project dir in the sender\'s home!')

	def _create_project_dir(self, user, projectdir=None):
		umask = os.umask(0)  # set umask so that os.makedirs can set correct permissions
		try:
			owner = int(user.uidNumber)
			group = int(user.gidNumber)
			homedir = user.homedir

			# create home directory with correct permissions if not yet exsists (e.g. user never logged in via samba)
			if homedir and not os.path.exists(homedir):
				MODULE.warn('recreate homedir %r uidNumber=%r gidNumber=%r' % (homedir, owner, group))
				os.makedirs(homedir, 0o711)
				os.chmod(homedir, 0o700)
				os.chown(homedir, owner, group)

			# create the project dir
			if projectdir and not os.path.exists(projectdir):
				MODULE.info("creating project dir in user's home: %s" % (projectdir,))
				os.makedirs(projectdir, 0o700)
				os.chown(projectdir, owner, group)

			# set owner and permission
			if homedir and projectdir:
				startdir = os.path.normpath(homedir).rstrip('/')
				projectdir = os.path.normpath(projectdir).rstrip('/')
				if not projectdir.startswith(startdir):
					raise OSError('Projectdir is not underneath of homedir: %s %s' % (projectdir, startdir))
				parts = projectdir[len(startdir):].lstrip('/').split('/')
				for part in parts:
					startdir = os.path.join(startdir, part)
					if os.path.isdir(startdir):  # prevent race conditions with symlink attacs
						os.chown(startdir, owner, group)

		except (OSError, IOError) as exc:
			import traceback
			MODULE.error(traceback.format_exc())
			MODULE.error('failed to create/chown %r: %s' % (projectdir, exc))
		finally:
			os.umask(umask)

	def _register_at_jobs(self):
		'''Registers at-jobs for distributing and collecting files.'''

		# register the starting job
		# make sure that the startime, if given, lies in the future
		if self.starttime and self.starttime > datetime.now():
			MODULE.info('register at-jobs: starttime = %s' % self.starttime)
			cmd = """'%s' --distribute %s""" % (DISTRIBUTION_CMD, quote(self.projectfile))
			print 'register at-jobs: starttime = %s  cmd = %s' % (self.starttime, cmd)
			atJob = atjobs.add(cmd, self.starttime)
			if atJob and self.starttime:
				self.atJobNumDistribute = atJob.nr
			if not atJob:
				MODULE.warn('registration of at-job failed')
				print 'registration of at-job failed'

		# register the collecting job, only if a deadline is given
		if self.deadline and self.deadline > datetime.now():
			MODULE.info('register at-jobs: deadline = %s' % self.deadline)
			print 'register at-jobs: deadline = %s' % self.deadline
			cmd = """'%s' --collect %s""" % (DISTRIBUTION_CMD, quote(self.projectfile))
			atJob = atjobs.add(cmd, self.deadline)
			if atJob:
				self.atJobNumCollect = atJob.nr
			else:
				MODULE.warn('registration of at-job failed')
				print 'registration of at-job failed'

	def _unregister_at_jobs(self):
		# remove at-jobs
		for inr in [self.atJobNumDistribute, self.atJobNumCollect]:
			ijob = atjobs.load(inr)
			if ijob:
				ijob.rm()

	def getRecipients(self):
		users = []
		for item in self.recipients:
			if item.type == TYPE_USER:
				users.append(item)
			elif item.type == TYPE_GROUP:
				users.extend(item.members)

		return users

	def distribute(self, usersFailed=None):
		'''Distribute the project data to all registrated receivers.'''

		if not isinstance(usersFailed, list):
			usersFailed = []

		# determine which files shall be distributed
		# note: already distributed files will be removed from the cache directory,
		#       yet they are still kept in the internal list of files
		files = [ifn for ifn in self.files if os.path.exists(os.path.join(self.cachedir, ifn))]

		if not files:
			# no files to distribute
			MODULE.info('No new files to distribute in project: %s' % self.name)
			return

		# make sure all necessary directories exist
		self._createProjectDir()

		# iterate over all recipients
		MODULE.info('Distributing project "%s" with files: %s' % (self.name, ", ".join(files)))
		for user in self.getRecipients() + [self.sender]:
			# create user project directory
			MODULE.info('recipient: uid=%s' % user.username)
			self._create_project_dir(user, self.user_projectdir(user))

			# copy files from cache to recipient
			for fn in files:
				src = str(os.path.join(self.cachedir, fn))
				target = str(os.path.join(self.user_projectdir(user), fn))
				try:
					if os.path.islink(src):
						raise IOError('Symlinks are not allowed')
					shutil.copyfile(src, target)
				except (OSError, IOError) as e:
					MODULE.error('failed to copy "%s" to "%s": %s' % (src, target, str(e)))
					usersFailed.append(user)
				try:
					os.chown(target, int(user.uidNumber), int(user.gidNumber))
				except (OSError, IOError) as e:
					MODULE.error('failed to chown "%s": %s' % (target, str(e)))
					usersFailed.append(user)

		# remove cached files
		for fn in files:
			try:
				src = str(os.path.join(self.cachedir, fn))
				if os.path.exists(src):
					os.remove(src)
				else:
					MODULE.info('file has already been distributed: %s' % src)
			except (OSError, IOError) as e:
				MODULE.error('failed to remove file: %s [%s]' % (src, e))

		return len(usersFailed) == 0

	def collect(self, dirsFailed=None):
		if not isinstance(dirsFailed, list):
			dirsFailed = []

		# make sure all necessary directories exist
		self._createProjectDir()

		# collect data from all recipients
		for recipient in self.getRecipients():
			# guess a proper directory name (in case with " versionX" suffix)
			dirVersion = 1
			targetdir = os.path.join(self.sender_projectdir, recipient.username)
			while os.path.exists(targetdir):
				dirVersion += 1
				targetdir = os.path.join(self.sender_projectdir, '%s version%d' % (recipient.username, dirVersion))

			# copy entire directory of the recipient
			srcdir = os.path.join(self.user_projectdir(recipient))
			MODULE.info('collecting data for user "%s" from %s to %s' % (recipient.username, srcdir, targetdir))
			if not os.path.isdir(srcdir):
				MODULE.info('Source directory does not exist (no files distributed?)')
			else:
				try:
					# copy dir
					def ignore(src, names):
						# !important" don't let symlinks be copied (e.g. /etc/shadow).
						# don't use shutil.copytree(symlinks=True) for this as it changes the owner + mode + flags of the symlinks afterwards
						return [name for name in names if os.path.islink(os.path.join(src, name))]
					shutil.copytree(srcdir, targetdir, ignore=ignore)

					# fix permission
					os.chown(targetdir, int(self.sender.uidNumber), int(self.sender.gidNumber))
					for root, dirs, files in os.walk(targetdir):
						for momo in dirs + files:
							os.chown(os.path.join(root, momo), int(self.sender.uidNumber), int(self.sender.gidNumber))

				except (OSError, IOError, ValueError):
					MODULE.warn('Copy failed: "%s" ->  "%s"' % (srcdir, targetdir))
					MODULE.info('Traceback:\n%s' % traceback.format_exc())
					dirsFailed.append(srcdir)

		return len(dirsFailed) == 0

	def purge(self):
		"""Remove project's cache directory, project file, and at job registrations."""
		if not self.projectfile or not os.path.exists(self.projectfile):
			MODULE.error('cannot remove empty or non existing projectfile: %s' % self.projectfile)
			return

		self._unregister_at_jobs()

		# remove cachedir
		MODULE.info('trying to purge projectfile [%s] and cachedir [%s]' % (self.projectfile, self.cachedir))
		if self.cachedir and os.path.exists(self.cachedir):
			try:
				shutil.rmtree(self.cachedir)
			except (OSError, IOError) as e:
				MODULE.error('failed to cleanup cache directory: %s [%s]' % (self.cachedir, str(e)))

		# remove projectfile
		try:
			os.remove(self.projectfile)
		except (OSError, IOError) as e:
			MODULE.error('cannot remove projectfile: %s [%s]' % (self.projectfile, str(e)))

	@staticmethod
	def sanitize_project_filename(path):
		'''
		sanitize project filename - if the file fn_project lies outside DISTRIBUTION_DATA_PATH
		any user is able to place a json project file and use that for file distribution/collection.
		'''
		if os.path.sep not in path:
			path = os.path.join(DISTRIBUTION_DATA_PATH, path)
		if not os.path.abspath(path).startswith(DISTRIBUTION_DATA_PATH):
			MODULE.error('Path %r does not contain prefix %r' % (path, DISTRIBUTION_DATA_PATH))
			raise InvalidProjectFilename('Path %r does not contain prefix %r' % (path, DISTRIBUTION_DATA_PATH))
		return os.path.abspath(path)

	@staticmethod
	def load(projectfile):
		'''Load the given project file and create a new Project instance.'''
		project = None

		if not projectfile:
			MODULE.info('Empty project filename has been passed to Project.load()')
			return None

		try:
			fn_project = Project.sanitize_project_filename(projectfile)
		except InvalidProjectFilename:
			return None

		if not os.path.exists(fn_project):
			MODULE.error('Cannot load project - project file %s does not exist' % fn_project)
			return None

		try:
			# load project dictionary from JSON file
			fd = open(fn_project, 'r')
			project = jsonDecode(fd.read())
			# project = Project(tmpDict.dict)
			fd.close()

			# convert _Dict instances to User
			if project.sender:
				project.sender = User(project.sender.dict)
			else:
				project.sender = User()

			# project.recipients = [ User(i.dict) for i in project.recipients ]
		except (IOError, ValueError, AttributeError) as e:
			MODULE.error('Could not open/read/decode project file: %s [%s]' % (projectfile, e))
			MODULE.info('TRACEBACK:\n%s' % traceback.format_exc())
			return None

		# make sure the filename matches the property 'name'
		project.name = os.path.basename(projectfile)
		return project

	@staticmethod
	def list():
		fn_projectlist = os.listdir(DISTRIBUTION_DATA_PATH)
		MODULE.info('distribution_search: WALK = %s' % fn_projectlist)
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
		projectlist.sort(cmp=lambda x, y: cmp(x.name.lower(), y.name.lower()))
		return projectlist


def initPaths():
	try:
		if not os.path.exists(DISTRIBUTION_DATA_PATH):
			os.makedirs(DISTRIBUTION_DATA_PATH, 0o700)
	except:
		MODULE.error('error occured while creating %s' % DISTRIBUTION_DATA_PATH)
	try:
		os.chmod(DISTRIBUTION_DATA_PATH, 0o700)
		os.chown(DISTRIBUTION_DATA_PATH, 0, 0)
	except:
		MODULE.error('error occured while fixing permissions of %s' % DISTRIBUTION_DATA_PATH)
