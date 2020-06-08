#!/usr/share/ucs-test/runner python
## desc: Check if all required and recommended packages for UCS@school are installed
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest,ucsschool]
## exposure: safe
## packages:
##    - ucs-school-master | ucs-school-singlemaster | ucs-school-slave

import apt
import univention.testing.utils as utils

METAPACKAGES = ['ucs-school-master', 'ucs-school-singlemaster', 'ucs-school-slave']


def main():
	apt_cache = apt.Cache()
	apt_cache.open()

	meta_found = 0
	for metapkg in METAPACKAGES:
		if metapkg in apt_cache and apt_cache[metapkg].is_installed:
			meta_found += 1

			for dependency in apt_cache[metapkg].candidate.dependencies + apt_cache[metapkg].candidate.recommends:
				pkglist = []
				found = 0
				for deppkg in dependency.or_dependencies:
					pkglist.append(deppkg.name)
					if deppkg.name in apt_cache and apt_cache[deppkg.name].is_installed:
						found += 1
				print 'Checking packages %r (pkg found=%d)' % (pkglist, found)
				if found == 0:
					utils.fail('Package %r is not installed but it should' % (deppkg,))
	if not meta_found:
		utils.fail('There is no meta package installed')


if __name__ == '__main__':
	main()
