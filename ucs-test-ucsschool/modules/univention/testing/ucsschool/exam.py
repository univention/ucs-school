"""
**Class Exam**

.. module:: exam
    :platform: Unix

.. moduleauthor:: Ammar Najjar <najjar@univention.de>
"""
from __future__ import print_function

import glob
import os
import re
import subprocess

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.ucs_samba import wait_for_s4connector
from univention.testing.umc import Client, ClientSaml


def get_dir_files(dir_path, recursive=True):
    result = []
    for f in glob.glob("%s/*" % dir_path):
        if os.path.isfile(f):
            result.append(os.path.basename(f))
        if os.path.isdir(f) and recursive:
            result.extend(get_dir_files(f))
    return result


def get_s4_rejected():
    cmd = ["univention-s4connector-list-rejected"]
    out, err = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    out, err = out.decode("UTF-8"), err.decode("UTF-8")
    print("rejected Objects:", out, err)
    found = re.findall(r"DN:\s\w{2,4}=.*", out)
    return set(found)


def check_s4_rejected(existing_rejects):
    new_rejects = get_s4_rejected()
    fail = [x for x in new_rejects if x not in existing_rejects]
    assert not fail, "There is at least one new rejected object: %r" % (fail,)


def check_proof_uniqueMember():
    cmd = ["/usr/share/univention-directory-manager-tools/proof_uniqueMembers"]
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = popen.communicate()
    out, err = out.decode("UTF-8"), err.decode("UTF-8")
    returncode = popen.returncode
    print(out, err, returncode)
    assert returncode == 0, "Proof unique members failed"


def wait_replications_check_rejected_uniqueMember(existing_rejects):
    utils.wait_for_replication()
    wait_for_s4connector()
    check_s4_rejected(existing_rejects)
    # TODO uncomment next line after fixing bug #36251
    # check_proof_uniqueMember()


class Exam(object):
    """
    Contains the needed functionality for exam module.\n
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
    :param connection:
    :type connection: UMC connection object
    """

    UMC_SCHOOLEXAM_LOG_PATH = "/var/log/univention/management-console-module-schoolexam.log"

    def __init__(
        self,
        school,
        room,  # room dn
        examEndTime,  # in format "HH:mm"
        recipients,  # list of classes dns
        name=None,
        directory=None,
        files=None,
        shareMode="home",
        internetRule="none",
        customRule="",
        connection=None,
    ):
        self.school = school
        self.room = room
        self.examEndTime = examEndTime
        self.recipients = recipients

        self.name = name if name else uts.random_name()
        self.directory = directory if directory else self.name
        self.files = files or []
        self.shareMode = shareMode
        self.internetRule = internetRule
        self.customRule = customRule

        if connection:
            self.client = connection
        else:
            self.client = Client.get_test_connection()

    def start(self):
        """Starts an exam"""
        param = {
            "school": self.school,
            "name": self.name,
            "room": self.room,
            "examEndTime": self.examEndTime,
            "recipients": self.recipients,
            "directory": self.directory,
            "files": self.files,
            "shareMode": self.shareMode,
            "internetRule": self.internetRule,
            "customRule": self.customRule,
        }
        print("Starting exam %s in room %s" % (self.name, self.room))
        print("param = %s" % param)
        reqResult = self.client.umc_command("schoolexam/exam/start", param).result
        print("Start exam response = ", reqResult)
        assert reqResult["success"], "Unable to start exam (%r)" % (param,)

    def save(self, update=False, fields=None):
        """Saves an exam. If fields is a list only the given values are set in the request"""
        param = {
            "school": "",
            "name": "",
            "room": "",
            "examEndTime": "",
            "recipients": [],
            "directory": "",
            "files": [],
            "shareMode": "",
            "internetRule": "",
            "customRule": "",
        }
        if fields is None:
            param = {
                "school": self.school,
                "name": self.name,
                "room": self.room,
                "examEndTime": self.examEndTime,
                "recipients": self.recipients,
                "directory": self.directory,
                "files": self.files,
                "shareMode": self.shareMode,
                "internetRule": self.internetRule,
                "customRule": self.customRule,
            }
        else:
            for field in fields:
                param[field] = getattr(self, field, "")
        print("Saving exam {}".format(self.name))
        command = "put" if update else "add"
        reqResult = self.client.umc_command("schoolexam/exam/{}".format(command), param).result
        print("Save exam response = {}".format(reqResult))
        assert reqResult, "Unable to {} exam {!r}".format(command, param)

    def get(self):
        """Gets an exam and returns result"""
        reqResult = self.client.umc_command("schoolexam/exam/get", [self.name]).result
        return reqResult

    def delete(self):
        """Deletes an exam and returns result"""
        reqResult = self.client.umc_command("schoolexam/exam/delete", {"exams": [self.name]}).result
        return reqResult

    def finish(self):
        """Finish an exam"""
        param = {"exam": self.name, "room": self.room}
        print("Finishing exam %s in room %s" % (self.name, self.room))
        print("param = %s" % param)
        reqResult = self.client.umc_command("schoolexam/exam/finish", param).result
        print("Finish exam response = ", reqResult)
        assert reqResult["success"], "Unable to finish exam (%r)" % param

    def genData(self, file_name, content_type, boundary, override_file_name=None):
        """
        Generates data in the form to be sent via http POST request.\n
        :param file_name: file name to be uploaded
        :type file_name: str
        :param content_type: type of the content of the file
        :type content_type: str ('text/plain',..)
        :param boundary: the boundary
        :type boundary: str (-------123091)
        :param flavor: flavor of the acting user
        :type flavor: str
        """
        mime_file_name = override_file_name or os.path.basename(file_name)
        with open(file_name) as f:
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
""".format(
                boundary, mime_file_name, content_type, f.read()
            )
        return data.replace("\n", "\r\n")

    def uploadFile(self, file_name, content_type=None, override_file_name=None):
        """
        Uploads a file via http POST request.\n
        :param file_name: file name to be uploaded
        :type file_name: str
        :param content_type: type of the content of the file
        :type content_type: str ('application/octet-stream',..)
        """
        print("Uploading file %s" % file_name)
        content_type = content_type or "application/octet-stream"
        boundary = "---------------------------12558488471903363215512784168"
        data = self.genData(file_name, content_type, boundary, override_file_name=override_file_name)
        header_content = {"Content-Type": "multipart/form-data; boundary=%s" % (boundary,)}
        self.client.request("POST", "upload/schoolexam/upload", data, headers=header_content)

    def get_internetRules(self):
        """Get internet rules"""
        reqResult = self.client.umc_command("schoolexam/internetrules", {}).result
        print("InternetRules = ", reqResult)
        return reqResult

    def fetch_internetRule(self, internetRule_name):
        if internetRule_name not in self.get_internetRules():
            utils.fail("Exam %s was not able to fetch internet rule %s" % (self.name, internetRule_name))

    def get_schools(self):
        """Get schools"""
        reqResult = self.client.umc_command("schoolexam/schools", {}).result
        schools = [x["label"] for x in reqResult]
        print("Schools = ", schools)
        return schools

    def fetch_school(self, school):
        assert school in self.get_schools(), "Exam %s was not able to fetch school %s" % (
            self.name,
            school,
        )

    def get_groups(self):
        """Get groups"""
        reqResult = self.client.umc_command(
            "schoolexam/groups", {"school": self.school, "pattern": ""}
        ).result
        print("Groups response = ", reqResult)
        groups = [x["label"] for x in reqResult]
        print("Groups = ", groups)
        return groups

    def fetch_groups(self, group):
        assert group in self.get_groups(), "Exam %s was not able to fetch group %s" % (self.name, group)

    def get_lessonEnd(self):
        """Get lessonEnd"""
        reqResult = self.client.umc_command("schoolexam/lesson_end", {}).result
        print("Lesson End = ", reqResult)
        return reqResult

    def fetch_lessonEnd(self, lessonEnd):
        assert lessonEnd in self.get_lessonEnd(), "Exam %s was not able to fetch lessonEnd %s" % (
            self.name,
            lessonEnd,
        )

    def collect(self):
        """Collect results"""
        reqResult = self.client.umc_command("schoolexam/exam/collect", {"exam": self.name}).result
        print("Collect respose = ", reqResult)
        return reqResult

    def check_collect(self):
        username = self.client.username or utils.UCSTestDomainAdminCredentials().username
        path = os.path.join(
            os.path.expanduser("~{}".format(username)), "Klassenarbeiten/%s-Ergebnisse" % (self.name,)
        )
        path_files = get_dir_files(path)
        assert set(self.files).issubset(set(path_files)), "%r were not collected to %r" % (
            self.files,
            path,
        )
        self._check_collection_logs()

    def check_upload(self):
        path = "/tmp/ucsschool-exam-upload*"
        path_files = get_dir_files(path)
        assert set(self.files).issubset(set(path_files)), "%r were not uploaded to %r" % (
            self.files,
            path,
        )

    def check_distribute(self):
        path = "/home/%s/schueler" % self.school
        path_files = get_dir_files(path)
        assert set(self.files).issubset(set(path_files)), "%r were not uploaded to %r" % (
            self.files,
            path,
        )

    def _check_collection_logs(self, lines=50):
        """Check last lines for specific errors"""
        with open(self.UMC_SCHOOLEXAM_LOG_PATH) as f:
            lines = f.readlines()[-lines:]
            for line in lines:

                # Bug 57661
                assert not re.match(r".*ERROR.*failed to create/chown.*/home/.*Klassenarbeiten", line)
                assert not re.match(r".*PermissionError:.*/home/.*Klassenarbeiten", line)


class ExamSaml(Exam):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("connection", ClientSaml.get_test_connection())
        super(ExamSaml, self).__init__(*args, **kwargs)
