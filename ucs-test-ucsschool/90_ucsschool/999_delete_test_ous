#!/usr/share/ucs-test/runner python
## desc: remove cached test OUs
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest,ucsschool,ucsschool_base1]
## exposure: dangerous

import univention.testing.ucsschool.ucs_test_school as utu


def main():
	with utu.UCSTestSchool() as schoolenv:
		schoolenv.delete_test_ous()


if __name__ == '__main__':
	main()
