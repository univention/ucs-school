#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention Management Console
#  module: Distribution Module
#
# Copyright 2007-2024 Univention GmbH
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

import errno
import itertools
import json
import os
import re
import shutil
import traceback
from datetime import datetime
from pipes import quote

import PAM
from six import iteritems, string_types

import ucsschool.lib.models
import univention.admin.uexceptions as udm_exceptions
from ucsschool.lib.models.user import User as SchoolLibUser
from univention.admin.uldap import getMachineConnection
from univention.lib import atjobs
from univention.lib.i18n import Translation
from univention.management.console.config import ucr
from univention.management.console.log import MODULE

_ = Translation("ucs-school-umc-distribution").translate

DISTRIBUTION_CMD = "/usr/lib/ucs-school-umc-distribution/umc-distribution"
DISTRIBUTION_DATA_PATH = ucr.get(
    "ucsschool/datadistribution/cache", "/var/lib/ucs-school-umc-distribution"
)

DISTRIBUTION_EXCLUDE_OTHER_TEACHERS = ucr.is_true("ucsschool/datadistribution/exclude_teachers", False)

POSTFIX_DATADIR_SENDER = ucr.get("ucsschool/datadistribution/datadir/sender", "Unterrichtsmaterial")
POSTFIX_DATADIR_SENDER_PROJECT_SUFFIX = ucr.get(
    "ucsschool/datadistribution/datadir/sender/project/suffix", "-Ergebnisse"
)
POSTFIX_DATADIR_RECIPIENT = ucr.get(
    "ucsschool/datadistribution/datadir/recipient", "Unterrichtsmaterial"
)
PAM_HOMEDIR_SESSION = ucr.is_true("homedir/create", True)


TYPE_USER = "USER"
TYPE_GROUP = "GROUP"
TYPE_PROJECT = "PROJECT"


class DistributionException(Exception):
    pass


class InvalidProjectFilename(DistributionException):
    pass


class _Dict(object):
    """
    Custom dict-like class. The initial set of keyword arguments is stored
    in an internal dict. Entries of this intial set can be accessed directly
    on the object (myDict.myentry = ...).
    """

    def __init__(self, type, **initDict):
        initDict["__type__"] = type
        object.__setattr__(self, "_dict", initDict)

    def __repr__(self):
        return repr(self.dict)

    # overwrite __setattr__ such that, e.g., project.cachedir can be called directly
    def __setattr__(self, key, value):
        _dict = object.__getattribute__(self, "_dict")

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
        _dict = object.__getattribute__(self, "_dict")

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
        """Update internal dict with the dict given as parameter."""
        # copy entries from the given dict over to the project properties
        _dict = self.dict
        for k, v in iteritems(props):
            if k in _dict:
                _dict[k] = v

    @property
    def dict(self):
        """The internal dict."""
        return self._dict

    @property
    def type(self):
        return self.__type__


class _DictEncoder(json.JSONEncoder):
    """A custom JSONEncoder class that can encode _Dict objects."""

    def default(self, obj):
        if isinstance(obj, _Dict):
            return obj.dict
        return json.JSONEncoder.default(self, obj)


def jsonEncode(val):
    """Encode to JSON using the custom _Dict encoder."""
    return _DictEncoder(indent=2).encode(val)


def jsonDecode(val):
    """Decode a JSON string and replace dict types with _Dict."""

    def _dict_type(x):
        if x["__type__"] == TYPE_USER:
            return User(**x)
        elif x["__type__"] == TYPE_GROUP:
            return Group(**x)
        elif x["__type__"] == TYPE_PROJECT:
            if "isDistributed" not in x and "files" in x:
                #  Guess distribution status for projects created prior fixing bug #47160
                cachedir = os.path.join(DISTRIBUTION_DATA_PATH, "%s.data" % x["name"])
                files = [ifn for ifn in x["files"] if os.path.exists(os.path.join(cachedir, ifn))]
                x["isDistributed"] = len(files) != len(x["files"])
            return Project(**x)
        else:
            return _Dict(**x)

    return json.loads(val, object_hook=_dict_type)


class User(_Dict):
    def __init__(self, *args, **_props):
        # init empty project dict
        super(User, self).__init__(
            TYPE_USER,
            unixhome="",
            username="",
            uidNumber="",
            gidNumber="",
            firstname="",
            lastname="",
            dn="",
        )

        # update specified entries
        if len(args):
            self.update(args[0])
        self.update(_props)

    # shortcut :)
    @property
    def homedir(self):
        return self.unixhome

    def school_lib_user(self, lo):
        return SchoolLibUser.from_dn(self.dn, None, lo)


class Group(_Dict):
    def __init__(self, *args, **_props):
        super(Group, self).__init__(TYPE_GROUP, dn="", name="", members=[])
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
            MODULE.error("%s is neither a group nor a user: %s" % (entryDN, exc))
            return  # neither a user nor a group. probably object doesn't exists
        return User(user.get_udm_object(ldap_connection).info, dn=user.dn)
    else:
        if not group_.self_is_workgroup() and not group_.self_is_class():
            MODULE.error(
                "%s is not a school class or workgroup but %r" % (group_.dn, type(group_).__name__)
            )
            return
        group = Group(group_.get_udm_object(ldap_connection).info, dn=group_.dn)
        if group_.school:
            name_pattern = re.compile("^%s-" % (re.escape(group_.school)), flags=re.I)
            group.name = name_pattern.sub("", group.name)
        for userdn in group_.users:
            try:
                user = ucsschool.lib.models.User.from_dn(userdn, None, ldap_connection)
            except udm_exceptions.noObject as exc:
                MODULE.warn("User %r does not exists: %s" % (userdn, exc))
                continue  # no user or doesn't exists
            except udm_exceptions.base as exc:
                MODULE.error("Cannot open user %r: %s" % (userdn, exc))
                continue

            if not user.is_student(ldap_connection):
                # only add students and exam students
                MODULE.info("ignoring non student %r" % (userdn,))

            group.members.append(User(user.get_udm_object(ldap_connection).info, dn=user.dn))
        return group


class Project(_Dict):
    def __init__(self, *args, **_props):
        # init empty project dict
        super(Project, self).__init__(
            TYPE_PROJECT,
            name=None,
            description=None,
            files=[],
            starttime=None,  # str
            deadline=None,  # str
            atJobNumDistribute=None,  # int
            atJobNumCollect=None,  # int
            sender=None,  # User
            recipients=[],  # [ (User|Group) , ...]
            isDistributed=False,
            room=None,  # str
        )

        # update specified entries
        if len(args):
            self.update(args[0])
        else:
            self.update(_props)

    def __repr__(self):
        return "Project(name={!r}) dict={!r}".format(self.name, self.dict)

    @staticmethod
    def _get_directory_size(src):
        needed_space = 0
        for (path, _dirs, files) in os.walk(src):
            for file in files:
                filename = os.path.join(path, file)
                needed_space += os.path.getsize(filename)
        return needed_space

    @property
    def projectfile(self):
        """The absolute project path to the project file."""
        return os.path.join(DISTRIBUTION_DATA_PATH, self.name)

    @property
    def cachedir(self):
        """The absolute path of the project cache directory."""
        return os.path.join(DISTRIBUTION_DATA_PATH, "%s.data" % self.name)

    @property
    def sender_projectdir(self):
        """The absolute path of the project directory in the senders home."""
        if self.sender and self.sender.homedir:
            return os.path.join(
                self.sender.homedir,
                POSTFIX_DATADIR_SENDER,
                "%s%s" % (self.name, POSTFIX_DATADIR_SENDER_PROJECT_SUFFIX),
            )
        return None

    @property
    def atJobDistribute(self):
        return atjobs.load(self.atJobNumDistribute)

    @property
    def atJobCollect(self):
        return atjobs.load(self.atJobNumCollect)

    # The number of results collected for each student.
    @property
    def num_results(self):
        # This only works because two requirements are fullfilled:
        # - A project always has at least one recipient
        # - All recipients have the same number of collected results
        # If any of that changes this property has to be modified!

        return len(list(self._all_versions(self.getRecipients()[0])))

    def user_projectdir(self, user):
        """Return the absolute path of the project dir for the specified user."""
        return os.path.join(user.homedir, POSTFIX_DATADIR_RECIPIENT, self.name)

    def _convStr2Time(self, key):
        """
        Converts the string value of the specified key in the internal dict
        to a datetime instance.
        """
        _dict = object.__getattribute__(self, "_dict")
        try:
            return datetime.strptime(_dict.get(key), "%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass
        return None

    def _convTime2String(self, key, time):
        """
        Converts the time value of the specified key to string and saves it to
        the internal dict. Parameter time may an instance of string or datetime.
        """
        _dict = object.__getattribute__(self, "_dict")
        if time is None:
            # unset value
            _dict[key] = None
        elif isinstance(time, string_types):
            # a string a saved directly to the internal dict
            _dict[key] = time
        elif isinstance(time, datetime):
            # a datetime instance is converted to string
            _dict[key] = datetime.strftime(time, "%Y-%m-%d %H:%M")
        else:
            raise ValueError('property "%s" needs to be of type str or datetime' % key)

    @property
    def starttime(self):
        return self._convStr2Time("starttime")

    @starttime.setter
    def starttime(self, time):
        self._convTime2String("starttime", time)

    @property
    def deadline(self):
        return self._convStr2Time("deadline")

    @deadline.setter
    def deadline(self, time):
        self._convTime2String("deadline", time)

    def validate(self):
        """
        Validate the project data. In case of any errors with the data,
        a ValueError with a proper error message is raised.
        """
        if not (isinstance(self.name, string_types) and self.name):
            raise ValueError(_("The given project directory name must be non-empty."))
        # disallow certain characters to avoid problems in Windows/Mac/Unix systems:
        # http://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words
        for ichar in ("/", "\\", "?", "%", "*", ":", "|", '"', "<", ">", "$", "'"):
            if self.name.find(ichar) >= 0:
                raise ValueError(
                    _('The specified project directory may not contain the character "%s".') % ichar
                )
        if self.name in ("..", "."):
            raise ValueError(_('The specified project directory must be different from "." and "..".'))
        if self.name.startswith(".") or self.name.endswith("."):
            raise ValueError(_('The specified project directory may not start nor end with a ".".'))
        if self.name.endswith(" ") or self.name.startswith(" "):
            raise ValueError(_("The specified project directory may not start nor end with a space."))
        if len(self.name) >= 255:
            raise ValueError(_("The specified project directory may at most be 254 characters long."))
        if not (isinstance(self.description, string_types) and self.description):
            raise ValueError(_("The given project description must be non-empty."))
        if not self.sender or not self.sender.username or not self.sender.homedir:
            raise ValueError(_("A valid project owner needs to be specified."))

    def isNameInUse(self):
        """Verifies whether the given project name is already in use."""
        # check for a project with given name
        if os.path.exists(self.projectfile):
            return True

        # check whether a project directory with the given name exists in the
        # recipients' home directories
        return any(
            iuser for iuser in self.getRecipients() if os.path.exists(self.user_projectdir(iuser))
        )

    def save(self):
        """Save project data to disk and create job. In case of any errors, an IOError is raised."""
        self._update_at_jobs()
        self._createCacheDir()
        self._write_projectfile()

    def _update_at_jobs(self):
        self._unregister_at_jobs()
        self._register_at_jobs()

    def _write_projectfile(self):
        new_projecfile = ".%s.new" % self.projectfile
        try:
            with open(new_projecfile, "w") as fd:
                fd.write(jsonEncode(self))
            os.rename(new_projecfile, self.projectfile)
        except EnvironmentError as exc:
            raise IOError(_("Could not save project file: %s (%s)") % (self.projectfile, str(exc)))

    def _createCacheDir(self):
        """Create cache directory."""
        # create project cache directory
        MODULE.info("creating project cache dir: %s" % self.cachedir)
        try:
            os.makedirs(self.cachedir, 0o700)
            os.chown(self.cachedir, 0, 0)
        except (OSError, IOError) as exc:
            if exc.errno == errno.EEXIST:
                MODULE.info("cache dir %s exists." % self.cachedir)
            else:
                MODULE.error("Failed to create cachedir: %s" % (exc,))

    def _createProjectDir(self):
        """Create project directory in the senders home."""
        if not self.sender:
            return

        self._create_project_dir(self.sender, self.sender_projectdir)

        if not self.sender_projectdir:
            MODULE.error(
                "ERROR: Sender information is not specified, cannot create project dir in the sender's "
                "home!"
            )

    def _create_project_dir(self, user, projectdir=None):
        umask = os.umask(0)  # set umask so that os.makedirs can set correct permissions
        try:
            owner = int(user.uidNumber)
            group = int(user.gidNumber)
            homedir = user.homedir

            # create home directory with correct permissions if not yet exsists (e.g. user never logged
            # in via samba)
            if homedir and not os.path.exists(homedir):
                if PAM_HOMEDIR_SESSION:
                    MODULE.warn(
                        "recreate homedir %r uidNumber=%r gidNumber=%r (PAM)" % (homedir, owner, group)
                    )
                    try:
                        p = PAM.pam()
                        p.start("session")
                        p.set_item(PAM.PAM_USER, user.username)
                        p.open_session()
                        p.close_session()
                    except PAM.error as e:
                        MODULE.error("recreating homedir with PAM failed: %s" % str(e))
                if not os.path.exists(homedir):
                    MODULE.warn(
                        "recreate homedir %r uidNumber=%r gidNumber=%r (makedirs)"
                        % (homedir, owner, group)
                    )
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
                startdir = os.path.normpath(homedir).rstrip("/")
                projectdir = os.path.normpath(projectdir).rstrip("/")
                if not projectdir.startswith(startdir):
                    raise OSError(
                        "Projectdir is not underneath of homedir: %s %s" % (projectdir, startdir)
                    )
                parts = projectdir[len(startdir) :].lstrip("/").split("/")
                for part in parts:
                    startdir = os.path.join(startdir, part)
                    if os.path.isdir(startdir):  # prevent race conditions with symlink attacs
                        os.chown(startdir, owner, group)

        except (OSError, IOError) as exc:
            import traceback

            MODULE.error(traceback.format_exc())
            MODULE.error("failed to create/chown %r: %s" % (projectdir, exc))
        finally:
            os.umask(umask)

    def _register_at_jobs(self):
        """Registers at-jobs for distributing and collecting files."""
        # register the starting job
        # make sure that the startime, if given, lies in the future
        if self.starttime and self.starttime > datetime.now():
            MODULE.info("register at-jobs: starttime = %s" % self.starttime)
            cmd = """'%s' --distribute %s""" % (DISTRIBUTION_CMD, quote(self.projectfile))
            print("register at-jobs: starttime = %s  cmd = %s" % (self.starttime, cmd))
            atJob = atjobs.add(cmd, self.starttime)
            if atJob and self.starttime:
                self.atJobNumDistribute = atJob.nr
            if not atJob:
                MODULE.warn("registration of at-job failed")
                print("registration of at-job failed")

        # register the collecting job, only if a deadline is given
        if self.deadline and self.deadline > datetime.now():
            MODULE.info("register at-jobs: deadline = %s" % self.deadline)
            print("register at-jobs: deadline = %s" % self.deadline)
            cmd = """'%s' --collect %s""" % (DISTRIBUTION_CMD, quote(self.projectfile))
            atJob = atjobs.add(cmd, self.deadline)
            if atJob:
                self.atJobNumCollect = atJob.nr
            else:
                MODULE.warn("registration of at-job failed")
                print("registration of at-job failed")

    def _unregister_at_jobs(self):
        # remove at-jobs
        for inr in [self.atJobNumDistribute, self.atJobNumCollect]:
            ijob = atjobs.load(inr)
            if ijob:
                ijob.rm()

    def getRecipients(self):

        lo, _ = getMachineConnection()
        users = []
        for item in self.recipients:
            if item.type == TYPE_USER:
                if not (DISTRIBUTION_EXCLUDE_OTHER_TEACHERS and item.school_lib_user(lo).is_teacher(lo)):
                    users.append(item)
            elif item.type == TYPE_GROUP:
                for member in item.members:
                    if not (
                        DISTRIBUTION_EXCLUDE_OTHER_TEACHERS and member.school_lib_user(lo).is_teacher(lo)
                    ):
                        users.append(member)
        if self.sender not in users:
            users.append(self.sender)

        return users

    def distribute(self, usersFailed=None):
        """Distribute the project data to all registrated receivers."""
        if not isinstance(usersFailed, list):
            usersFailed = []

        # determine which files shall be distributed
        # note: already distributed files will be removed from the cache directory,
        #       yet they are still kept in the internal list of files
        files = [ifn for ifn in self.files if os.path.exists(os.path.join(self.cachedir, ifn))]

        # make sure all necessary directories exist
        self._createProjectDir()

        # iterate over all recipients
        MODULE.info('Distributing project "%s" with files: %s' % (self.name, ", ".join(files)))
        for user in self.getRecipients() + [self.sender]:
            # create user project directory
            MODULE.info("recipient: uid=%s" % user.username)
            self._create_project_dir(user, self.user_projectdir(user))

            # copy files from cache to recipient
            for fn in files:
                src = str(os.path.join(self.cachedir, fn))
                target = str(os.path.join(self.user_projectdir(user), fn))
                try:
                    if os.path.islink(src):
                        raise IOError("Symlinks are not allowed")
                    shutil.copyfile(src, target)
                except (OSError, IOError) as e:
                    MODULE.error('failed to copy "%s" to "%s": %s' % (src, target, str(e)))
                    usersFailed.append(user)
                try:
                    os.chown(target, int(user.uidNumber), int(user.gidNumber))
                except (OSError, IOError) as e:
                    MODULE.error('failed to chown "%s": %s' % (target, str(e)))
                    usersFailed.append(user)
            else:
                MODULE.info("No new files to distribute in project: %s" % self.name)

        # remove cached files
        for fn in files:
            try:
                src = str(os.path.join(self.cachedir, fn))
                if os.path.exists(src):
                    os.remove(src)
                else:
                    MODULE.info("file has already been distributed: %s" % src)
            except (OSError, IOError) as e:
                MODULE.error("failed to remove file: %s [%s]" % (src, e))
        self.isDistributed = True
        self._write_projectfile()

        return len(usersFailed) == 0

    def _all_versions(self, recipient):
        """
        Returns a generator containing all version numbers of existing results for a given recipient.
        :param recipient: The recipient to get the versions for
        :type recipient: User
        :return: iterable(int)
        """
        if not os.path.exists(self.sender_projectdir):
            return ()
        return (
            int(number)
            for number in itertools.chain(
                *[
                    re.findall(r"{}-(\d+)".format(recipient.username), entry)
                    for entry in os.listdir(self.sender_projectdir)
                ]
            )
        )

    def _next_target(self, recipient):
        """
        Generates the next target path/zip path for a given recipient.
        :param recipient: The recipient to generate the target for
        :type recipient: User
        :return: The path to the folder/zip (str)
        """
        current_version = max([0] + list(self._all_versions(recipient)))
        return os.path.join(
            self.sender_projectdir, "%s-%03d" % (recipient.username, current_version + 1)
        )

    def _get_available_space(self):
        """
        Calculates the available space in the project directory of the sender aka teacher.
        :return: The available space in bytes
        """
        statvfs = os.statvfs(self.sender_projectdir)
        return statvfs.f_frsize * statvfs.f_bavail

    # After changing requirements this added function is no longer required, but kept for future
    # reference
    # def prune_results(self, limit, username=None):
    # 	"""
    # 	This function removes collected results from students as long as the number of existing
    # 	collected results is bigger than the given limit. It starts from the oldest version and works
    # 	its way up.
    #
    # 	:param limit: The number of collected results to prune to. Negative numbers are cropped to 0
    # 	:type limit: int
    # 	:param username: If the value is set, the pruning is restricted to the specified user
    # 	:type username: None or string
    # 	"""
    #
    # 	def _delete_result(target):
    # 		try:
    # 			if os.path.isfile(target + '.zip'):
    # 				os.remove(target+'.zip')
    # 			else:
    # 				shutil.rmtree(target)
    # 		except (OSError, IOError, ValueError):
    # 			MODULE.warn('Deletion failed: "%s"' % (target))
    # 			MODULE.info('Traceback:\n%s' % traceback.format_exc())
    #
    # 	limit = max((limit, 0))
    # 	projectdir_content = os.listdir(self.sender_projectdir)
    # 	for recipient in self.getRecipients():
    # 		if username and recipient.username != username:
    # 			continue
    # 		all_versions = list(self._all_versions(recipient))
    # 		all_versions.sort(reverse=True)
    # 		while len(all_versions) > limit:
    # 			target = os.path.join(self.sender_projectdir, '%s-%03d' % (recipient.username,
    # 			    all_versions.pop()))
    # 			_delete_result(target)

    def _fix_permissions(self, path):
        os.chown(path, int(self.sender.uidNumber), int(self.sender.gidNumber))
        try:
            # Remove ntacl set for exams, to allow read access
            os.removexattr(path, "security.NTACL", follow_symlinks=False)
        except OSError as exc:
            no_xattr_set_error = errno.ENODATA
            if exc.errno == no_xattr_set_error:
                pass
            else:
                MODULE.warn("Could not remove ntacl:\n{}".format(exc))

    def collect(self, dirsFailed=None, readOnly=False, compress=False):
        if not isinstance(dirsFailed, list):
            dirsFailed = []
        compressed_suffix = ".zip" if compress else ""

        # make sure all necessary directories exist
        self._createProjectDir()

        # collect data from all recipients
        for recipient in self.getRecipients():
            targetdir = self._next_target(recipient)

            # copy entire directory of the recipient
            srcdir = os.path.join(self.user_projectdir(recipient))
            # check space requirements
            src_size = self._get_directory_size(srcdir)
            available_space = self._get_available_space()
            if available_space - src_size < 0:
                MODULE.warn("not enough space to copy from %s to %s" % (srcdir, targetdir))
                dirsFailed.append(srcdir)
                continue
            MODULE.info(
                'collecting data for user "%s" from %s to %s' % (recipient.username, srcdir, targetdir)
            )
            if not os.path.isdir(srcdir):
                MODULE.info("Source directory does not exist (no files distributed?)")
            else:
                try:
                    # copy dir
                    def ignore(src, names):
                        # !important" don't let symlinks be copied (e.g. /etc/shadow).
                        # don't use shutil.copytree(symlinks=True) for this as it changes the
                        # owner + mode + flags of the symlinks afterwards
                        return [name for name in names if os.path.islink(os.path.join(src, name))]

                    # zip is hard coded for now. But it could be possible to make it configurable
                    if compress and "zip" in (e[0] for e in shutil.get_archive_formats()):
                        shutil.make_archive(targetdir, "zip", srcdir)
                    else:
                        shutil.copytree(srcdir, targetdir, ignore=ignore)

                    # Necessary for correct filename in the permission fixing
                    targetdir = targetdir + compressed_suffix
                    # fix permission
                    self._fix_permissions(targetdir)
                    if compress:
                        os.chmod(targetdir, 0o600)
                    for root, dirs, files in os.walk(targetdir):
                        for momo in dirs + files:
                            self._fix_permissions(os.path.join(root, momo))
                        if readOnly:
                            for file in files:
                                os.chmod(os.path.join(root, file), 0o400)

                except (OSError, IOError, ValueError):
                    MODULE.warn('Copy failed: "%s" ->  "%s"' % (srcdir, targetdir))
                    MODULE.info("Traceback:\n%s" % traceback.format_exc())
                    dirsFailed.append(srcdir)

        return len(dirsFailed) == 0

    def purge(self):
        """Remove project's cache directory, project file, and at job registrations."""
        if not self.projectfile or not os.path.exists(self.projectfile):
            MODULE.error("cannot remove empty or non existing projectfile: %s" % self.projectfile)
            return

        self._unregister_at_jobs()

        # remove cachedir
        MODULE.info(
            "trying to purge projectfile [%s] and cachedir [%s]" % (self.projectfile, self.cachedir)
        )
        if self.cachedir and os.path.exists(self.cachedir):
            try:
                shutil.rmtree(self.cachedir)
            except (OSError, IOError) as e:
                MODULE.error("failed to cleanup cache directory: %s [%s]" % (self.cachedir, str(e)))

        # remove projectfile
        try:
            os.remove(self.projectfile)
        except (OSError, IOError) as e:
            MODULE.error("cannot remove projectfile: %s [%s]" % (self.projectfile, str(e)))

    @staticmethod
    def sanitize_project_filename(path):
        """
        sanitize project filename - if the file fn_project lies outside DISTRIBUTION_DATA_PATH
        any user is able to place a json project file and use that for file distribution/collection.
        """
        if os.path.sep not in path:
            path = os.path.join(DISTRIBUTION_DATA_PATH, path)
        if not os.path.abspath(path).startswith(DISTRIBUTION_DATA_PATH):
            MODULE.error("Path %r does not contain prefix %r" % (path, DISTRIBUTION_DATA_PATH))
            raise InvalidProjectFilename(
                "Path %r does not contain prefix %r" % (path, DISTRIBUTION_DATA_PATH)
            )
        return os.path.abspath(path)

    @staticmethod
    def load(projectfile):
        """Load the given project file and create a new Project instance."""
        project = None

        if not projectfile:
            MODULE.info("Empty project filename has been passed to Project.load()")
            return None

        try:
            fn_project = Project.sanitize_project_filename(projectfile)
        except InvalidProjectFilename:
            return None

        if not os.path.exists(fn_project):
            MODULE.error("Cannot load project - project file %s does not exist" % fn_project)
            return None

        try:
            # load project dictionary from JSON file
            with open(fn_project) as fd:
                project = jsonDecode(fd.read())
            if not project.isDistributed:
                #  Projects created before bug #47160 was fixed didn't save their distribution status
                files = [
                    ifn for ifn in project.files if os.path.exists(os.path.join(project.cachedir, ifn))
                ]
                project.isDistributed = len(files) != len(project.files)

            # convert _Dict instances to User
            if project.sender:
                project.sender = User(project.sender.dict)
            else:
                project.sender = User()

            # project.recipients = [ User(i.dict) for i in project.recipients ]
        except (IOError, ValueError, AttributeError) as e:
            MODULE.error("Could not open/read/decode project file: %s [%s]" % (projectfile, e))
            MODULE.info("TRACEBACK:\n%s" % traceback.format_exc())
            return None

        # make sure the filename matches the property 'name'
        project.name = os.path.basename(projectfile)
        return project

    @staticmethod
    def list(only_distributed=False):
        fn_projectlist = os.listdir(DISTRIBUTION_DATA_PATH)
        MODULE.info("distribution_search: WALK = %s" % fn_projectlist)
        projectlist = []
        for fn_project in fn_projectlist:
            # make sure the entry is a file
            fname = os.path.join(DISTRIBUTION_DATA_PATH, fn_project)
            if not os.path.isfile(fname):
                continue

            # load the project and add it to the result list
            project = Project.load(fname)
            if project:
                if (
                    only_distributed
                    and "isDistributed" in project.dict
                    and project.dict["isDistributed"]
                ) or not only_distributed:
                    projectlist.append(project)

        # sort final result
        projectlist.sort(key=lambda x: x.name.lower())
        return projectlist


def initPaths():
    try:
        if not os.path.exists(DISTRIBUTION_DATA_PATH):
            os.makedirs(DISTRIBUTION_DATA_PATH, 0o700)
    except EnvironmentError:
        MODULE.error("error occured while creating %s" % DISTRIBUTION_DATA_PATH)
    try:
        os.chmod(DISTRIBUTION_DATA_PATH, 0o700)
        os.chown(DISTRIBUTION_DATA_PATH, 0, 0)
    except EnvironmentError:
        MODULE.error("error occured while fixing permissions of %s" % DISTRIBUTION_DATA_PATH)
