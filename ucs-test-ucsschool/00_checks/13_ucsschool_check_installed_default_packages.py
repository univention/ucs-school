#!/usr/share/ucs-test/runner pytest -s -l -v
## desc: Check if all required and recommended packages for UCS@school are installed
## roles: [domaincontroller_master, domaincontroller_backup, domaincontroller_slave]
## tags: [apptest,ucsschool]
## exposure: safe
## packages:
##    - ucs-school-master | ucs-school-singlemaster | ucs-school-slave

from __future__ import print_function

import apt

METAPACKAGES = ["ucs-school-master", "ucs-school-singlemaster", "ucs-school-slave"]


def test_installed_ucsschool_default_packages():
    apt_cache = apt.Cache()
    apt_cache.open()

    meta_found = 0
    for metapkg in METAPACKAGES:
        if metapkg in apt_cache and apt_cache[metapkg].is_installed:
            meta_found += 1

            for dependency in (
                apt_cache[metapkg].candidate.dependencies + apt_cache[metapkg].candidate.recommends
            ):
                pkglist = []
                found = 0
                for deppkg in dependency.or_dependencies:
                    pkglist.append(deppkg.name)
                    if deppkg.name in apt_cache and apt_cache[deppkg.name].is_installed:
                        found += 1
                print("Checking packages %r (pkg found=%d)" % (pkglist, found))
                assert found, "Package %r is not installed but it should" % (deppkg,)
    assert meta_found, "There is no meta package installed"
