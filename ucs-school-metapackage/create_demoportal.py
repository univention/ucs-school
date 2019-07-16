#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2018-2019 Univention GmbH
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

from univention.management.console.ldap import get_admin_connection
from univention.admin.uldap import position
from ucsschool.lib.models import School, Student, Teacher, Staff, SchoolClass, ucr
import univention.admin.modules as modules
import sys
import os
import subprocess
import base64
import json
import string
import random

lo, pos = get_admin_connection()
modules.update()
module_portal = modules.get('settings/portal')
module_portal_c = modules.get('settings/portal_category')
module_portal_e = modules.get('settings/portal_entry')
module_groups = modules.get('groups/group')
module_users = modules.get('users/user')

is_single_master = ucr.is_true('ucsschool/singlemaster', False)
if is_single_master:
	hostname_demoschool = ucr.get('hostname')
else:
	hostname_demoschool = "DEMOSCHOOL"
hostdn = ucr.get('ldap/hostdn')
demo_secret_path = '/etc/ucsschool/demoschool.secret'
if os.path.isfile(demo_secret_path):
	with open(demo_secret_path, 'r') as fd:
		demo_password = fd.read().strip()
else:
	demo_password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
	with open(demo_secret_path, 'w') as fd:
		os.fchmod(fd.fileno(), 0o640)
		fd.write(demo_password)

# (name, displayName)
SCHOOL = ('DEMOSCHOOL', 'Demo School')

# (name, en, de)
CATEGORIES = [
	('ucsschool_demo_collaboration_communication', 'Collaboration & Communication', 'Kollaboration & Kommunikation'),
	('ucsschool_demo_creativity', 'Creativity', 'Kreativität'),
	('ucsschool_demo_admin', 'Administration', 'Verwaltung')
	]

# (name, name_en, name_de, descr_en, descr_de, link, icon, group)
ENTRIES = [
	('ucsschool_demo_mail', 'Mail', 'Mail', 'Mail', 'Mail', '/univention/ucsschool/demo_tiles.html', 'mail', 'everyone'),
	('ucsschool_demo_chat', 'Chat', 'Chat', 'Chat', 'Chat', '/univention/ucsschool/demo_tiles.html', 'chat', 'everyone'),
	('ucsschool_demo_calendar', 'Calendar', 'Kalender', 'Calendar', 'Kalender', '/univention/ucsschool/demo_tiles.html', 'calendar', 'everyone'),
	('ucsschool_demo_bookResources', 'Book Resources', 'Ressourcen buchen', 'Book Resources', 'Ressourcen buchen', '/univention/ucsschool/demo_tiles.html', 'bookResources', 'teacher'),
	('ucsschool_demo_subPlan', 'Subsitution Plan', 'Vertretungsplan', 'Subsitution Plan', 'Vertretungsplan', '/univention/ucsschool/demo_tiles.html', 'subPlan', 'everyone'),
	('ucsschool_demo_eduFunctions', 'Educational Functions', 'Pädagogische Funktionen', 'Educational Functions', 'Pädagogische Funktionen', '/univention/management/#category=ucs-school-class', 'eduFunctions', 'teacher'),
	('ucsschool_demo_home', 'My files', 'Eigene Dateien', 'My files', 'Eigene Dateien', '/univention/ucsschool/demo_tiles.html', 'home', 'everyone'),
	('ucsschool_demo_share', 'File Share', 'Tauschverzeichnis', 'File Share', 'Tauschverzeichnis', '/univention/ucsschool/demo_tiles.html', 'share', 'everyone'),
	('ucsschool_demo_workOnline', 'Work Online', 'Online Arbeiten', 'Work Online', 'Online Arbeiten', '/univention/ucsschool/demo_tiles.html', 'workOnline', 'everyone'),
	('ucsschool_demo_pwReset', 'Reset own Password', 'Eigenes Passwort zurücksetzen', 'Reset own Password', 'Eigenes Passwort zurücksetzen', '/univention/ucsschool/demo_tiles.html', 'pwReset_1', 'everyone'),
	('ucsschool_demo_users', 'User Management', 'Benutzerverwaltung', 'User Management', 'Benutzerverwaltung', '/univention/management/#module=schoolwizards:schoolwizards/users:0:', 'contacts', 'schooladmin'),
	('ucsschool_demo_admin', 'Administration', 'Administration', 'Administration', 'Administration', '/univention/management/', 'admin', 'everyone')
]


def create_school():
	school_exists = False
	schools = School.from_binddn(lo)
	for school in schools:
		if school.name == SCHOOL[0]:
			print('WARNING: A school with name {} already exists!'.format(SCHOOL[0]))
			school_exists = True
			break
	if not school_exists:
		try:
			subprocess.check_call(['python', '/usr/share/ucs-school-import/scripts/create_ou', '--displayName={}'.format(SCHOOL[1]), '--alter-dhcpd-base=false', SCHOOL[0], hostname_demoschool])
		except subprocess.CalledProcessError as e:
			print('The following error occured while creating the Demo School object: \n')
			print(e)
			sys.exit(1)
	kls = SchoolClass(name='{}-Democlass'.format(SCHOOL[0]), school=SCHOOL[0])
	kls.create(lo)
	student = Student(firstname='Demo', lastname='Student', name='demo_student', password=demo_password, school=SCHOOL[0])
	student.school_classes[SCHOOL[0]] = ['Democlass']
	student.create(lo)
	teacher = Teacher(firstname='Demo', lastname='Teacher', name='demo_teacher', password=demo_password, school=SCHOOL[0])
	teacher.create(lo)
	staff = Staff(firstname='Demo', lastname='Staff', name='demo_staff', password=demo_password, school=SCHOOL[0])
	staff.create(lo)
	# create school admin from teacher
	admin = Teacher(firstname='Demo', lastname='Admin', name='demo_admin', password=demo_password, school=SCHOOL[0])
	admin.create(lo)
	admin_group = module_groups.lookup(None, lo, 'name=admins-{}'.format(SCHOOL[0]), pos.getBase())[0].dn
	admin_udm = admin.get_udm_object(lo)
	admin_udm.options.append('ucsschoolAdministrator')
	admin_udm['groups'].append(admin_group)
	admin_udm['description'] = 'School Admin for {} created from teacher account.'.format(SCHOOL[0])
	admin_udm.modify()


def create_portal():
	to_create = list()
	pos_portal = position(pos.getBase())
	pos_category = position(pos.getBase())

	entry_groups = dict(
		domainadmin='',
		schooladmin='',
		teacher='',
		everyone=''
		)
	try:
		entry_groups['domainadmin'] = module_groups.lookup(None, lo, 'name=Domain Admins', pos.getBase())[0].dn
		entry_groups['schooladmin'] = module_groups.lookup(None, lo, 'name=admins-{}'.format(SCHOOL[0]), pos.getBase())[0].dn
		entry_groups['teacher'] = module_groups.lookup(None, lo, 'name=lehrer-{}'.format(SCHOOL[0]), pos.getBase())[0].dn
	except IndexError as e:
		print('Could not find all necessary user groups to create demo portal. Something must have gone wrong with the school creation!')
		sys.exit(1)

	pos_portal.setDn('cn=portal,cn=univention')
	for name, en, de, descr_en, descr_de, link, icon, group in ENTRIES:
		iconpath = '/usr/share/ucs-school-metapackage/ucsschool_demo_pictures/ucsschool_demo_{}.png'.format(icon)
		entry_obj = module_portal_e.object(None, lo, pos_portal)
		entry_obj.open()
		entry_obj['name'] = name
		entry_obj['displayName'] = [('en_US', en), ('de_DE', de)]
		entry_obj['description'] = [('en_US', descr_en), ('de_DE', descr_de)]
		entry_obj['link'] = link
		with open(iconpath, 'r') as fd:
			content = fd.read()
			entry_obj['icon'] = base64.b64encode(content)
		entry_obj['allowedGroups'] = [entry_groups[group]]
		to_create.append(entry_obj)

	pos_category.setDn('cn=categories,cn=portal,cn=univention')
	for dn, en, de in CATEGORIES:
		category_obj = module_portal_c.object(None, lo, pos_category)
		category_obj.open()
		category_obj['name'] = dn
		category_obj['displayName'] = [('en_US', en), ('de_DE', de)]
		to_create.append(category_obj)

	portal_obj = module_portal.object(None, lo, pos_portal)
	portal_obj.open()
	portal_obj['name'] = 'ucsschool_demo_portal'
	portal_obj['displayName'] = [('en_US', 'UCS@school Demo Portal'), ('de_DE', 'UCS@school Demo Portal')]
	portal_obj['showApps'] = 'FALSE'
	portal_obj['portalComputers'] = hostdn
	portal_content = [
		[
			'cn=ucsschool_demo_collaboration_communication,{}'.format(pos_category.getDn()),
			[
				'cn=ucsschool_demo_mail,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_chat,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_calendar,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_bookResources,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_subPlan,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_eduFunctions,{}'.format(pos_portal.getDn())
			]
		],
		[
			'cn=ucsschool_demo_creativity,{}'.format(pos_category.getDn()),
			[
				'cn=ucsschool_demo_home,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_share,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_workOnline,{}'.format(pos_portal.getDn())
			]
		],
		[
			'cn=ucsschool_demo_admin,{}'.format(pos_category.getDn()),
			[
				'cn=ucsschool_demo_pwReset,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_users,{}'.format(pos_portal.getDn()),
				'cn=ucsschool_demo_admin,{}'.format(pos_portal.getDn())
			]
		]
	]
	portal_obj['content'] = json.dumps(portal_content)
	with open('/usr/share/ucs-school-metapackage/ucsschool_demo_pictures/background.jpg', 'r') as fd:
		content = fd.read()
		portal_obj['background'] = base64.b64encode(content)
	to_create.append(portal_obj)

	for o in to_create:
		if not already_exists(o):
			o.create()


def run():
	"""
	This function creates a demo school and demo portal for testing and demonstration purposes
	"""
	create_school()
	create_portal()
	sys.exit(0)


def already_exists(check_obj):
	"""
	Checks if a given object already exists in the LDAP
	(works only with portal, portal categories and portal entries)
	"""
	obj_type = type(check_obj)
	if obj_type == module_portal.object:
		return len(module_portal.lookup(None, lo, 'name={}'.format(check_obj.get('name')), base=check_obj.position.getBase())) > 0
	elif obj_type == module_portal_c.object:
		return len(module_portal_c.lookup(None, lo, 'name={}'.format(check_obj.get('name')), base=check_obj.position.getBase())) > 0
	elif obj_type == module_portal_e.object:
		return len(module_portal_e.lookup(None, lo, 'name={}'.format(check_obj.get('name')), base=check_obj.position.getBase())) > 0
	else:
		raise ValueError('The checked object is no portal[_entry|_category] object!')


if __name__ == '__main__':
	run()
