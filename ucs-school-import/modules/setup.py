# -*- coding: utf-8 -*-

#
# Use only Python 2 and 3 compatible code here!
#

#
# Install: pip3 install -e .
#

import os
import re
import sys
import tempfile
try:
    from urllib import urlretrieve  # py2
except ImportError:
    from urllib.request import urlretrieve  # py3
import setuptools

dir_here = os.path.dirname(os.path.abspath(__file__))
changelog_path = os.path.join(os.path.dirname(dir_here), "debian", "changelog")
chlog_regex = re.compile(r"^(?P<package>.+?) \((?P<version>.+?)\) \w+;")
PIP_FALLBACK_URL = "https://raw.githubusercontent.com/univention/ucs-school/4.4/ucs-school-import/debian/changelog"

# when installing using "setup.py install ." the directory is not changed, when using pip, work is done in /tmp
if not os.path.exists(changelog_path):
    _fp, changelog_path = tempfile.mkstemp()
    urlretrieve(PIP_FALLBACK_URL, changelog_path)

with open(changelog_path) as fp:
    for line in fp:
        m = chlog_regex.match(line)
        if m:
            break
    else:
        print("Could not parse find package name and version in {}.".format(changelog_path))
        sys.exit(1)

with open(os.path.join(dir_here, "requirements.txt")) as fp:
    requirements = fp.read().splitlines()

setuptools.setup(
    name=m.groupdict()["package"],
    version=m.groupdict()["version"],
    author="Univention GmbH",
    author_email="packages@univention.de",
    description="UCS@school Import python modules",
    long_description="UCS@school Import python modules",
    url="https://www.univention.de/",
    install_requires=requirements,
    packages=[
        'ucsschool.importer',
        'ucsschool.importer.contrib',
        'ucsschool.importer.frontend',
        'ucsschool.importer.legacy',
        'ucsschool.importer.mass_import',
        'ucsschool.importer.models',
        'ucsschool.importer.reader',
        'ucsschool.importer.utils',
        'ucsschool.importer.writer',
    ],
    license="GNU Affero General Public License v3",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: AsyncIO",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
