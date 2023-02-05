#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: ucs-school-printermoderation-find-printer-in-ou-check
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-printermoderation, ucs-school-import]

import socket
import subprocess
import tempfile

import univention.testing.strings as uts
from univention.testing import utils
from univention.testing.umc import Client


# add / del / modify Printer
def doPrinter(operation, printer_name, schoolName, spool_host, domainname):
    localIp = socket.gethostbyname(socket.gethostname())
    uri = "%s://%s" % ("lpd", localIp)
    print_server = "%s.%s" % (spool_host, domainname)
    with tempfile.NamedTemporaryFile("w+", suffix=".csv") as fd:
        line = "%s\t%s\t%s\t%s\t%s\n" % (operation, schoolName, print_server, printer_name, uri)
        fd.write(line)
        fd.flush()
        subprocess.check_call(["/usr/share/ucs-school-import/scripts/import_printer", fd.name])
    utils.wait_for_replication_and_postrun()


# check the existance of the created printer
def printerExist(connection, printerName, schoolName):
    requestResult = connection.umc_command("printermoderation/printers", {"school": schoolName}).result
    return [d for d in requestResult if d["label"] == printerName]


def test_ucs_school_printermoderatoion_find_printer_in_ou(schoolenv, ucr):
    newPrinterName = uts.random_string()
    host = ucr.get("hostname")
    domainname = ucr.get("domainname")
    connection = Client(host)
    account = utils.UCSTestDomainAdminCredentials()
    admin = account.username
    passwd = account.bindpw
    connection.authenticate(admin, passwd)

    # create more than one OU
    (schoolName1, _), (schoolName2, _), (schoolName3, _) = schoolenv.create_multiple_ous(
        3, name_edudc=host
    )

    # add new printer
    doPrinter("A", newPrinterName, schoolName1, host, domainname)

    # check if the printer exists in the correct OU
    for i in range(5):
        assert printerExist(
            connection, newPrinterName, schoolName1
        ), "Printer not found in the specified OU"

        for school in [schoolName2, schoolName3]:
            assert not printerExist(
                connection, newPrinterName, school
            ), "Printer underneath of wrong OU was found."

    # delete the created printer
    doPrinter("D", newPrinterName, schoolName1, host, domainname)
