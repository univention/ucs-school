#!/usr/bin/env python3
import pathlib
import urllib

import requests
import yaml
from debian.deb822 import Deb822

STAGING_PATH = pathlib.Path("doc/errata/staging")
DOTFILE = pathlib.Path(".dotenv")
REPO = "https://omar.knut.univention.de/build2/{scope}/"


def is_build(source, fix, scope):
    for arch in ("all", "amd64"):
        packages_link = urllib.parse.urljoin(REPO.format(scope=scope), f"{arch}/Packages")
        for package in Deb822.iter_paragraphs(
            requests.get(packages_link, verify=False).text  # noqa: S501 # nosec: B501
        ):
            src_name = package.get("Source", package["Package"])
            if src_name == source and package["Version"] == fix:
                return True
    return False


def main():
    bugs = set()
    source_packages = set()
    for file_path in STAGING_PATH.glob("*.yaml"):
        print(f"Processing {file_path}")
        with open(file_path) as yaml_file:
            content = yaml.safe_load(yaml_file)
        bugs = bugs.union(set(content.get("bug", [])))
        source = content.get("src", None)
        scope = content.get("scope", None)
        fix = content.get("fix", None)
        if not scope or not source or not fix:
            continue
        if not is_build(source, fix, scope):
            print(f"Adding {source} to DEBIAN_SOURCE_DIRECTORIES")
            source_packages.add(source)

    DOTFILE.write_text(
        f"RELEASE_BUGS={' '.join(str(bug) for bug in bugs)}"
        f"\nDEBIAN_SOURCE_DIRECTORIES={' '.join(source_packages)}"
    )


if __name__ == "__main__":
    main()
