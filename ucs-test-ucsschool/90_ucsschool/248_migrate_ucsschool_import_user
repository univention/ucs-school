#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: Test migration from legacy/manual import to new import
## tags: [apptest,ucsschool,ucsschool_import2]
## roles: [domaincontroller_master]
## exposure: dangerous
## packages:
##   - ucs-school-import
## bugs: [50321]

from __future__ import absolute_import, print_function
import subprocess
import random
import os
import attr
import csv
import tempfile
import univention.testing.ucr
import univention.testing.utils as utils
import univention.testing.strings as uts
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool
from ucsschool.lib.models.user import User
try:
	from typing import List
except ImportError:
	pass


@attr.s
class MyUser(object):
	username = attr.ib()  # type: str
	dn = attr.ib()  # type: str
	firstname = attr.ib()  # type: str
	lastname = attr.ib()  # type: str
	record_uid = attr.ib()  # type: str


def main():
	with univention.testing.ucr.UCSTestConfigRegistry() as ucr, UCSTestSchool() as schoolenv:
		ou_name, ou_dn = schoolenv.create_ou(name_edudc=ucr.get("hostname"))
		lo = schoolenv.open_ldap_connection(admin=True)

		next_record_uid = random.randint(100000, 950000)

		unambiguous_users = []  # type: List[MyUser]
		ambiguous_users = []  # type: List[MyUser]
		# create 4 unique users
		for func in [
				schoolenv.create_student,
				schoolenv.create_teacher,
				schoolenv.create_teacher_and_staff,
				schoolenv.create_staff]:
			user_name, user_dn = func(ou_name, use_cli=False, wait_for_replication=False)
			user = User.from_dn(user_dn, None, lo)
			unambiguous_users.append(MyUser(
				user_name,
				user_dn,
				user.firstname,
				user.lastname,
				str(next_record_uid)))
			next_record_uid += 1

		# create 4x3 users with same first/last name
		for func in [
				schoolenv.create_student,
				schoolenv.create_teacher,
				schoolenv.create_teacher_and_staff,
				schoolenv.create_staff]:
			user_name, user_dn = func(ou_name, use_cli=False, wait_for_replication=False)
			user = User.from_dn(user_dn, None, lo)
			ambiguous_users.append(MyUser(
				'',
				user_dn,
				user.firstname,
				user.lastname,
				str(next_record_uid)))
			next_record_uid += 1
			for i in range(2):
				user2_name, user2_dn = func(
					ou_name,
					firstname=user.firstname,
					lastname=user.lastname,
					use_cli=False,
					wait_for_replication=False)
				user2 = User.from_dn(user2_dn, None, lo)
				ambiguous_users.append(MyUser(
					'',
					user2_dn,
					user2.firstname,
					user2.lastname,
					str(next_record_uid)))
				next_record_uid += 1

		utils.wait_for()

		# create entry without matching username
		ambiguous_users.append(MyUser('', '', 'Kevin', 'Kenichnett', str(next_record_uid)))
		next_record_uid += 1
		ambiguous_users.append(MyUser('', '', 'Ursula', 'Unbekannt', str(next_record_uid)))
		next_record_uid += 1

		# create CSV file for guessing
		with tempfile.NamedTemporaryFile(mode='wb') as fd_guess, tempfile.NamedTemporaryFile(mode='rb') as fd_target, tempfile.NamedTemporaryFile(mode='wb') as fd_migrate:
			os.remove(fd_target.name)

			writer = csv.writer(fd_guess, dialect='excel')
			writer.writerow(['Firstname', 'Lastname', 'Some Stuff', 'record_uid'])
			for user in unambiguous_users + ambiguous_users:
				writer.writerow([user.firstname, user.lastname, uts.random_string(), user.record_uid])
			fd_guess.flush()

			# test user guessing
			subprocess.call([
				'/usr/share/ucs-school-import/scripts/migrate_ucsschool_import_user',
				'--guess-usernames',
				'--input-file={}'.format(fd_guess.name),
				'--column-firstname=1',
				'--column-lastname=2',
				'--column-record-uid=4',
				'--output-file={}'.format(fd_target.name)])

			print('******** RESULT OF GUESSING ***********')
			print(open(fd_target.name, 'r').read())
			print('*******************')

			# check CSV file from guessing
			fd_target2 = open(fd_target.name, 'rb')
			reader = csv.reader(fd_target2, dialect='excel')
			# drop CSV header and comments
			row = reader.next()
			while row[0] != 'username':
				row = reader.next()
			# check lines against expected content
			for i, user in enumerate(ambiguous_users + unambiguous_users):
				row = reader.next()
				print('Reading entry {:2d}: {!r}'.format(i, row))
				print('  Expected entry: {}'.format(user))
				if not user.username:  # no or multiple matches
					assert user.firstname in row[3]
					assert user.lastname in row[3]
					assert user.record_uid in row[3]
				else:
					assert row[2] == ''
					assert row[3] == ''
					assert user.username == row[0]
					assert user.record_uid == row[1]

			print("*\n*** Performing user migration with and without source_uid argument...\n*")

			writer = csv.writer(fd_migrate, dialect='excel')
			writer.writerow(['username', 'record_uid'])
			for user in unambiguous_users:
				writer.writerow([user.username, user.record_uid])
			fd_migrate.flush()

			# test user guessing
			for dry_run in ('--dry-run', ''):
				for source_uid in (None, uts.random_string()):
					cmd = [
						'/usr/share/ucs-school-import/scripts/migrate_ucsschool_import_user',
						'--modify-record-uid',
						'--input-file={}'.format(fd_migrate.name),
					]
					if source_uid is not None:
						cmd.append('--source-uid={}'.format(source_uid))
					if dry_run:
						cmd.append(dry_run)
					subprocess.call(cmd)

					# check users
					for user in unambiguous_users:
						result = lo.search(base=user.dn)
						assert result, 'Could not find {} in LDAP'.format(user.dn)
						if dry_run:
							assert result[0][1].get('ucsschoolSourceUID', [''])[0] != source_uid
							assert result[0][1].get('ucsschoolRecordUID', [''])[0] != user.record_uid
							assert result[0][1].get('uid', [''])[0] == user.username
						else:
							if source_uid is not None:
								assert result[0][1].get('ucsschoolSourceUID', [''])[0] == source_uid
							else:
								assert result[0][1].get('ucsschoolSourceUID', [''])[0] != source_uid
							assert result[0][1].get('ucsschoolRecordUID', [''])[0] == user.record_uid
							assert result[0][1].get('uid', [''])[0] == user.username

			print("*\n*** Test was successful.\n*")


if __name__ == '__main__':
	main()
