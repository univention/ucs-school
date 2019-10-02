# -*- coding: utf-8 -*-

#
# Install: pip3 install -e .
#

from pathlib import Path
from subprocess import check_call
from typing import Iterable
from ucsschool.kelvin import __version__

import os
import setuptools
import shutil

with open(Path(__file__).parent / "requirements.txt") as fp:
    requirements = fp.read().splitlines()

with open(Path(__file__).parent / "requirements_test.txt") as fp:
    requirements_test = fp.read().splitlines()


class BuildHTMLCommand(setuptools.Command):
    description = "generate HTML from RST"
    user_options = [("input-file=", "i", "input file")]

    def initialize_options(self):
        self.input_file = None

    def finalize_options(self):
        pass

    def run(self):
        for name in ("rst2html5.py", "rst2html5-3.py", "rst2html5", "rst2html5-3"):
            rst2_html5_exe = shutil.which(name)
            if rst2_html5_exe:
                break
        else:
            raise RuntimeError("Cannot find 'rst2html5'.")
        if self.input_file:
            self.check_call(
                [rst2_html5_exe, self.input_file, f"{str(self.input_file)[:-3]}html"]
            )
        else:
            for entry in self.recursive_scandir(Path(__file__).parent):
                if entry.is_file() and entry.name.endswith(".rst"):
                    self.check_call(
                        [rst2_html5_exe, entry.path, f"{str(entry.path)[:-3]}html"]
                    )

    @classmethod
    def recursive_scandir(cls, path: Path) -> Iterable[os.DirEntry]:
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                yield from cls.recursive_scandir(entry.path)
            yield entry

    @classmethod
    def check_call(cls, cmd):
        print(f"Executing: {cmd!r}")
        check_call(cmd)


setuptools.setup(
    name="ucs-school-kelvin-api",
    version=__version__,
    author="Univention GmbH",
    author_email="packages@univention.de",
    description="UCS@school objects HTTP API (aka 'Kelvin API')",
    long_description="UCS@school objects HTTP API (aka 'Kelvin API')",
    url="https://www.univention.de/",
    install_requires=requirements,
    setup_requires=["docutils", "pytest-runner"],
    tests_require=requirements_test,
    packages=["ucsschool.kelvin", "ucsschool.kelvin.routers"],
    python_requires=">=3.7",
    license="GNU Affero General Public License v3",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
    ],
    cmdclass={"build_html": BuildHTMLCommand},
)
