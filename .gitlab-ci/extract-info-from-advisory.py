#!/usr/bin/env python3
import pathlib

import yaml

STAGING_PATH = pathlib.Path("doc/errata/staging")
DOTFILE = pathlib.Path(".dotenv")

bugs = set()
source_packages = set()
for file_path in STAGING_PATH.glob("*.yaml"):
    print(f"Processing {file_path}")
    with open(file_path) as yaml_file:
        content = yaml.safe_load(yaml_file)
        bugs = bugs.union(set(content.get("bug", [])))
        if source := content.get("src", None):
            source_packages.add(source)

DOTFILE.write_text(
    f"RELEASE_BUGS={' '.join(str(bug) for bug in bugs)}"
    f"\nDEBIAN_SOURCE_DIRECTORIES={' '.join(source_packages)}"
)
