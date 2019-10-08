# -*- coding: utf-8 -*-

import io
from email.utils import parseaddr
from debian.changelog import Changelog
from debian.deb822 import Deb822
import setuptools

dch = Changelog(io.open("debian/changelog", "r", encoding="utf-8"))
dsc = Deb822(io.open("debian/control", "r", encoding="utf-8"))
realname, email_address = parseaddr(dsc["Maintainer"])

with open("requirements.txt") as fp:
    requirements = fp.read().splitlines()

setuptools.setup(
    name=dch.package,
    version=dch.version.full_version,
    maintainer=realname,
    maintainer_email=email_address,
    description="Common UCS@school Python modules",
    long_description="Common UCS@school Python modules",
    url="https://www.univention.de/",
    install_requires=requirements,
    packages=["ucsschool.lib", "ucsschool.lib.models", "ucsschool.lib.pyhooks"],
    package_dir={"": "modules"},
    license="GNU Affero General Public License v3",
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Topic :: Education",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration :: Authentication/Directory :: LDAP",
    ],
)
