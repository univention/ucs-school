#!/usr/share/ucs-test/runner python
## desc: Distribute empty project and check collection
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave, memberserver]
## tags: [apptest,ucsschool,ucsschool_base1]
## bugs: [47160]
## exposure: dangerous
## packages: [ucs-school-umc-distribution]

from univention.testing.ucsschool.distribution import Distribution
from univention.testing.ucsschool.workgroup import Workgroup
from univention.testing.umc import Client
import time
import subprocess
import os
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils

# Generate the required time variables in the correct format


def getDateTime(starttime, deadline):
	distTime = time.strftime('%H:%M', starttime)
	distDate = time.strftime('%Y-%m-%d', starttime)
	collTime = time.strftime('%H:%M', deadline)
	collDate = time.strftime('%Y-%m-%d', deadline)
	return distTime, distDate, collTime, collDate


def main():
	with utu.UCSTestSchool() as schoolenv:
		with ucr_test.UCSTestConfigRegistry() as ucr:
			host = ucr.get('hostname')
			connection = Client(host)

			# Create ou, teacher, student, group
			school, oudn = schoolenv.create_ou(name_edudc=ucr.get('hostname'))
			tea, teadn = schoolenv.create_user(school, is_teacher=True)
			tea2, teadn2 = schoolenv.create_user(school, is_teacher=True)
			stu, studn = schoolenv.create_user(school)
			group = Workgroup(school, members=[studn])
			group.create()
			utils.wait_for_replication_and_postrun()

			connection.authenticate(tea, 'univention')

			# Create new project
			project = Distribution(school, sender=tea, connection=connection, ucr=ucr, files=[], recipients=[group], flavor='teacher')
			project.add()
			project.check_add()
			project.distribute()
			project.check_distribute([stu])
			student_project_path = project.getUserFilesPath(stu, purpose='distribute')
			filename = uts.random_string()
			subprocess.check_call(['touch', os.path.join(student_project_path, filename)])
			project.files.append((filename, 'utf-8',))
			project.collect()
			project.check_collect([stu])

			project.remove()
			project.check_remove()


if __name__ == '__main__':
	main()
