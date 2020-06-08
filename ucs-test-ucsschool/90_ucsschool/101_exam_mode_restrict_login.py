#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Check login restrictions of exam users and original users during exam
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## bugs: [49960]
## packages: [univention-samba4, ucs-school-umc-computerroom, ucs-school-umc-exam]

import os
from datetime import datetime, timedelta
from univention.testing.ucsschool.computerroom import Room, Computers
from univention.testing.ucsschool.exam import Exam
import univention.testing.ucr as ucr_test
import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.udm
import univention.testing.utils as utils
import univention.testing.strings as uts
from ucsschool.lib.models import Student


def main():
	with univention.testing.udm.UCSTestUDM() as udm:
		with utu.UCSTestSchool() as schoolenv:
			with ucr_test.UCSTestConfigRegistry() as ucr:
				open_ldap_co = schoolenv.open_ldap_connection()
				ucr.load()

				print('# create test users and classes')
				if ucr.is_true('ucsschool/singlemaster'):
					edudc = None
				else:
					edudc = ucr.get('hostname')
				school, oudn = schoolenv.create_ou(name_edudc=edudc)
				klasse_dn = udm.create_object('groups/group', name='%s-AA1' % school, position="cn=klassen,cn=schueler,cn=groups,%s" % oudn)
				tea, teadn = schoolenv.create_user(school, is_teacher=True)
				stu, studn = schoolenv.create_user(school)
				student2 = Student(
					name=uts.random_username(),
					school=school,
					firstname=uts.random_name(),
					lastname=uts.random_name())
				student2.position = "cn=users,%s" % ucr['ldap/base']
				student2.create(open_ldap_co)
				orig_udm = student2.get_udm_object(open_ldap_co)
				orig_udm['sambaUserWorkstations'] = ['OTHERPC']
				orig_udm.modify()
				udm.modify_object('groups/group', dn=klasse_dn, append={"users": [teadn]})
				udm.modify_object('groups/group', dn=klasse_dn, append={"users": [studn]})
				udm.modify_object('groups/group', dn=klasse_dn, append={"users": [student2.dn]})

				print('# import random computers')
				computers = Computers(open_ldap_co, school, 2, 0, 0)
				pc1, pc2 = computers.create()

				print('# set 2 computer rooms to contain the created computers')
				room1 = Room(school, host_members=pc1.dn)
				room2 = Room(school, host_members=pc2.dn)
				for room in [room1, room2]:
					schoolenv.create_computerroom(school, name=room.name, description=room.description, host_members=room.host_members)

				print('# Set an exam and start it')
				current_time = datetime.now()
				chosen_time = current_time + timedelta(hours=2)
				exam = Exam(
					school=school,
					room=room2.dn,  # room dn
					examEndTime=chosen_time.strftime("%H:%M"),  # in format "HH:mm"
					recipients=[klasse_dn]  # list of classes dns
				)
				exam.start()

				exam_member_dns = [
					"uid=exam-%s,cn=examusers,%s" % (stu, oudn),
					"uid=exam-%s,cn=examusers,%s" % (student2.name, oudn)
				]

				for dn in exam_member_dns:
					result = open_ldap_co.get(dn, ['sambaUserWorkstations'], True)
					assert result.get('sambaUserWorkstations') == [pc2.name]
				result = open_ldap_co.get(student2.dn, ['sambaUserWorkstations'], True)
				assert result.get('sambaUserWorkstations') == ['$OTHERPC']
				print('# stopping exam')
				exam.finish()
				result = open_ldap_co.get(student2.dn, ['sambaUserWorkstations'], True)
				assert result.get('sambaUserWorkstations') == ['OTHERPC']


if __name__ == '__main__':
	main()
