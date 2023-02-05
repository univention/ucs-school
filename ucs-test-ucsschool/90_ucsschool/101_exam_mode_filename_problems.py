#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: upload files to exam module with problematic filenames
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-distribution]

from __future__ import print_function

import os
import random
import tempfile

from univention.testing.ucsschool.exam import Exam


def test_exam_mode_filename_problems(ucr):
    hostname = ucr.get("hostname")
    project = Exam("unused_school", "unused_room", "unused_endtime", "unused_recipients")

    for override_file_name in [
        "\\\\%s\\tmp\\foobar.txt" % (hostname,),
        "C:\\Windows\\Temp\\foobar.txt",
        "foobar.txt",
    ]:
        with tempfile.NamedTemporaryFile("w+") as fd:
            token = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(256))
            fd.write(token)
            fd.flush()

            project.uploadFile(
                fd.name, "application/octet-stream", override_file_name=override_file_name
            )

        found = False
        dirlist = [
            name
            for name in os.listdir("/tmp")
            if name.startswith("ucsschool-exam-upload-") and os.path.isdir(os.path.join("/tmp", name))
        ]
        for dirname in dirlist:
            dirname = os.path.join("/tmp", dirname)
            for filename in os.listdir(dirname):
                filename = os.path.join(dirname, filename)
                if os.path.getsize(filename) == 256:
                    try:
                        if token == open(filename).read() and os.path.basename(filename) == "foobar.txt":
                            found = True
                    except (IOError, OSError) as exc:
                        print("Failed to check %r: %r" % (filename, exc))
                if found:
                    break
            if found:
                break
        assert found, 'Failed to upload test file with "forged" filename %r' % (override_file_name,)
