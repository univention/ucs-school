#!/usr/share/ucs-test/runner python
## desc: Test if share-access don't leave permission change open for class members.
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_base1,mysharetest]
## exposure: dangerous
## packages: []
## bugs: [42182]

import re
import subprocess
import univention.testing.udm as udm_test

import univention.testing.ucsschool.ucs_test_school as utu
import univention.testing.utils as utils
from ucsschool.lib.models import School, Share


def main():
	with udm_test.UCSTestUDM() as udm:
		with utu.UCSTestSchool() as schoolenv:

			# school, oudn = schoolenv.create_ou()
			# klasse_name = '%s-AA1' % school
			# klasse_dn = udm.create_object('groups/group', name=klasse_name,
			#                               position="cn=klassen,cn=schueler,cn=groups,%s" % oudn)
			# share_dn = 'cn={},cn=klassen,cn=shares,{}'.format(klasse_name, schoolenv.get_ou_base_dn(school))
			# path = "/home/{}/groups/klassen/{}".format(school, klasse_name)
			#
			# share_dn = udm.create_object('shares/share', name='test-share',
			#                              position="cn=klassen,cn=shares,%s" % oudn,
			#                              host=schoolenv.ucr['hostname'],
			#                              path=path)
			# utils.verify_ldap_object(share_dn, strict=True, should_exist=True)

			# # # is the share not created? didn't work.
			# group_sid = schoolenv.lo.get(klasse_dn)['sambaSID'][0]
			#
			# print(path)
			# proc = subprocess.Popen(['samba-tool', 'ntacl', 'get', '--as-sddl', path], stdout=subprocess.PIPE)
			# stdout, stderr = proc.communicate()

			for school in School.get_all(schoolenv.lo):

				# for already existing classes.
				for share in Share.get_all(schoolenv.lo, school.name):
					share_udm = share.get_udm_object(schoolenv.lo)
					if share.name in ["Marktplatz", "iTALC-Installation"]:
						print("*** Ignoring //{}/{} (Bug #42514)".format(school.name, share.name))
					else:
						# better test -> if permissions can be altered
						proc = subprocess.Popen(['samba-tool', 'ntacl', 'get', '--as-sddl', share_udm["path"]], stdout=subprocess.PIPE)
						stdout, stderr = proc.communicate()
						sid_map = [
							('S-1-1-0', 'everyone'),
							('S-1-5-21', 'group'),
						]
						for sid, name in sid_map:
							if re.match(r'.*?(A.+?0x001f01ff[^)]+?{}.*?).*'.format(sid), stdout):
								# Full control is ok, if it is stripped by the permission to change permissions.
								if not re.match(r'.*?(D;OICI;WOWD[^)]+?{}.*?).*'.format(sid), stdout):
									utils.fail("The permissions of share {} can be changed.".format(share_udm["path"], name))





if __name__ == '__main__':
	main()
