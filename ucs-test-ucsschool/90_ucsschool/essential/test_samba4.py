from sys import exit
from subprocess import Popen, PIPE

from univention.testing.codes import TestCodes
from univention.config_registry import ConfigRegistry


class TestSamba4(object):

    def __init__(self):
        """
        Test class constructor
        """
        self.UCR = ConfigRegistry()

        self.admin_username = ''
        self.admin_password = ''

        self.gpo_reference = ''

    def return_code_result_skip(self):
        """
        Stops the test returning the code 77 (RESULT_SKIP).
        """
        exit(TestCodes.REASON_INSTALL)

    def create_and_run_process(self, cmd, stdin=None, std_input=None):
        """
        Creates a process as a Popen instance with a given 'cmd'
        and executes it. When stdin is needed, it can be provided with kwargs.
        """
        proc = Popen(cmd, stdin=stdin, stdout=PIPE, stderr=PIPE)
        return proc.communicate(input=std_input)

    def grep_for_key(self, grep_in, key):
        """
        Runs grep on given 'grep_in' with a given 'key'. Returns the output.
        """
        stdout, stderr = self.create_and_run_process(("grep", key),
                                                     PIPE,
                                                     grep_in)
        if stderr:
            utils.fail("An error occured while running a grep with a "
                       "keyword '%s':\n'%s'" % (key, stderr))
        return stdout

    def get_ucr_test_credentials(self):
        """
        Loads the UCR to get credentials for the test.
        """
        print("\nObtatining Administrator username and password "
              "for the test from the UCR")
        try:
            self.UCR.load()

            self.admin_username = self.UCR['tests/domainadmin/account']
            # extracting the 'uid' value of the administrator username string:
            self.admin_username = self.admin_username.split(',')[0][len('uid='):]
            self.admin_password = self.UCR['tests/domainadmin/pwd']
        except KeyError as exc:
            print("\nAn exception while trying to read data from the UCR for "
                  "the test: '%s'. Skipping the test." % exc)
            self.return_code_result_skip()

    def delete_samba_gpo(self):
        """
        Deletes the Group Policy Object using the 'samba-tool gpo del'.
        """
        print("\nRemoving previously created Group Policy Object (GPO) with "
              "a reference: %s" % self.gpo_reference)

        cmd = ("samba-tool", "gpo", "del", self.gpo_reference,
               "--username=" + self.admin_username,
               "--password=" + self.admin_password)

        stdout, stderr = self.create_and_run_process(cmd)
        if stderr:
            print("\nAn error message while removing the GPO using "
                  "'samba-tool':\n%s" % stderr)

        print "\nSamba-tool produced the following output:\n", stdout
