#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: computerroom two rooms settings
## roles: [domaincontroller_master, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous
## packages: [ucs-school-umc-computerroom]


from univention.testing.ucsschool.computerroom import Room, Computers, add_printer
from univention.testing.umc import Client
import datetime
from univention.testing import utils
import univention.testing.strings as uts
import univention.testing.ucsschool.ucs_test_school as utu


def main():
	with utu.UCSTestSchool() as schoolenv:
			ucr = schoolenv.ucr
			school, oudn = schoolenv.create_ou(name_edudc=ucr.get('hostname'))
			tea, tea_dn = schoolenv.create_user(school, is_teacher=True)
			open_ldap_co = schoolenv.open_ldap_connection()

			# importing random 3 computers
			computers = Computers(open_ldap_co, school, 3, 0, 0)
			created_computers = computers.create()
			computers_dns = computers.get_dns(created_computers)
			computers_ips = computers.get_ips(created_computers)

			# setting computer rooms contains the created computers
			room1 = Room(school, host_members=computers_dns[0])
			room2 = Room(school, host_members=computers_dns[1])
			room3 = Room(school, host_members=computers_dns[2])

			# Creating the rooms
			for room in [room1, room2, room3]:
				schoolenv.create_computerroom(
					school,
					name=room.name,
					description=room.description,
					host_members=room.host_members
				)

			client = Client(ucr.get('hostname'))
			client.authenticate(tea, 'univention')

			# Add new hardware printer
			printer_name = uts.random_string()
			add_printer(
				printer_name,
				school,
				ucr.get('hostname'),
				ucr.get('domainname'),
				ucr.get('ldap/base')
			)

			did_fail = False

			class settings(object):
				pass
			settings1 = settings()
			settings1.room = room1
			settings1.ip = computers_ips[0]
			settings2 = settings()
			settings2.room = room2
			settings2.ip = computers_ips[1]
			settings3 = settings()
			settings3.room = room3
			settings3.ip = computers_ips[2]

			def set_room_printmode(settings):
				settings.room.aquire_room(client)
				period = datetime.time.strftime((datetime.datetime.now() + datetime.timedelta(0, 600)).time(), '%H:%M')
				settings.room.set_room_settings(client, {'customRule': '', 'printMode': settings.printmode, 'internetRule': 'none', 'shareMode': 'all', 'period': period, })

			def ucr_check_both_values(settings):
				ucr.load()
				print '==> samba/printmode/hosts/all = %r' % ucr.get('samba/printmode/hosts/all')
				print '==> samba/printmode/hosts/none = %r' % ucr.get('samba/printmode/hosts/none')

				class NotOk(Exception):
					pass

				try:
					# if everything is on default, then no variable is set
					if all([(setting.printmode == 'default') for setting in settings]) and (ucr.get('samba/printmode/hosts/all') or ucr.get('samba/printmode/hosts/none')):
						raise NotOk()

					for setting in settings:
						if setting.printmode == 'none' and setting.ip[0] not in ucr.get('samba/printmode/hosts/none', ''):
							raise NotOk()
						elif setting.printmode == 'default' and (setting.ip[0] in ucr.get('samba/printmode/hosts/all', '') or setting.ip[0] in ucr.get('samba/printmode/hosts/none', '')):
							raise NotOk()
					print '---OK---'
				except NotOk:
					print '---FAIL---'
					return False
				return True

			# test with 2 rooms
			printmodes = ['default', 'none']
			settingslist = [settings1, settings2]
			for settings1.printmode in printmodes:
				set_room_printmode(settings1)
				for settings2.printmode in printmodes:
					print '---------------------------------------------'
					set_room_printmode(settings2)
					print 'Printmodes: %r' % ([x.printmode for x in settingslist],)
					if not ucr_check_both_values(settingslist):
						did_fail = True

			# test with 3 rooms
			settingslist = [settings1, settings2, settings3]
			for settings1.printmode in printmodes:
				set_room_printmode(settings1)
				for settings2.printmode in printmodes:
					set_room_printmode(settings2)
					for settings3.printmode in printmodes:
						print '---------------------------------------------'
						set_room_printmode(settings3)
						print 'Printmodes: %r' % ([x.printmode for x in settingslist],)
						if not ucr_check_both_values(settingslist):
							did_fail = True

			if did_fail:
				utils.fail('At least one combination failed!')


if __name__ == '__main__':
	main()
