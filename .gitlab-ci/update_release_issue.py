#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import gzip
import json
import os
import re
import urllib
from configparser import ConfigParser
from pathlib import Path

import requests
import yaml
from debian.changelog import Changelog
from debian.deb822 import Deb822
from debian.debian_support import version_compare

RELEASE_EXCEPTIONS = ["ucs-test-ucsschool"]


class RelaeseIssue:
    context_re = r"## Context\/description[^#]*\n\n#"
    packages_re = r"## Packages to be released[^#]*\n\n#"

    context_template = "## Context/description\n\n UCS@school {version} has to be released...\n\n#"
    packages_template = "## Packages to be released\n\n{packages}\n\n#"

    version_regex = r"(?P<ucsversion>\d+.\d+) ?v(?P<schoolversion>\d+)"

    def __init__(self):
        token = os.environ["GITLAB_PROJECT_TOKEN"]
        self.headers = {"PRIVATE-TOKEN": token}
        self.changelogs = Path("../ucsschool").glob("**/debian/changelog")
        self.ucsversion = os.environ["CI_COMMIT_BRANCH"]
        self.apps_index_link = (
            f"https://appcenter.software-univention.de/meta-inf/{self.ucsversion}/index.json.gz"
        )
        self.app_repo = f"https://appcenter.software-univention.de/univention-repository/{self.ucsversion}/maintained/component/"
        self.latest_app = self._get_latest_app()
        self.unreleased_packages = self._get_unreleased_packages()

    def update(self):
        if not [pkg for pkg in self.unreleased_packages if pkg not in RELEASE_EXCEPTIONS]:
            return
        issue = self._get_release_issue()
        self._update_release_issue(issue)

    def _get_latest_app(self):
        index_appcenter = json.loads(gzip.decompress(requests.get(self.apps_index_link).content))
        latest_app = None
        for component_id, app in index_appcenter.items():
            if component_id.startswith("ucsschool_"):
                app_config = ConfigParser()
                app_config.read_string(requests.get(app["ini"]["url"]).text)
                version = app_config.get("Application", "Version")
                m = re.match(self.version_regex, version)
                schoolversion = m.group("schoolversion")
                ucsversion = m.group("ucsversion")
                if ucsversion != self.ucsversion:
                    continue
                if not latest_app or int(latest_app["schoolversion"]) < int(schoolversion):
                    latest_app = {
                        "version": version,
                        "app_config": app_config,
                        "component_id": component_id,
                        "schoolversion": schoolversion,
                        "ucsversion": ucsversion,
                    }
        if not latest_app:
            err_msg = "Could not find app version"
            raise ValueError(err_msg)
        return latest_app

    def _get_latest_school_package_source(self):
        return urllib.parse.urljoin(self.app_repo, f"{self.latest_app['component_id']}/")

    def _get_released_sources_pkgs(self, latest_school_link):
        src_pkgs = {}
        for arch in ("all", "amd64"):
            packages_link = urllib.parse.urljoin(latest_school_link, f"{arch}/Packages")
            for package in Deb822.iter_paragraphs(requests.get(packages_link).text):
                src_name = package.get("Source", package["Package"])
                if (
                    src_name not in src_pkgs
                    or version_compare(package["Version"], src_pkgs[src_name]) == 1
                ):
                    src_pkgs[src_name] = package["Version"]
        return src_pkgs

    def _get_unreleased_packages(self):
        latest_school_package_source = self._get_latest_school_package_source()
        released_sources_pkgs = self._get_released_sources_pkgs(latest_school_package_source)
        unreleased_packages = {}
        for changelog_path in self.changelogs:
            changelog = Changelog(changelog_path.read_text())
            pkg_name = changelog.get_package()
            if pkg_name in unreleased_packages:
                double_package_name_error = f"Package: {pkg_name} exists multiple times!"
                raise RuntimeError(double_package_name_error)
            # A brand-new source package is not part of any published app version,
            # so it has no "old" version (None) instead of raising a KeyError.
            old_version = released_sources_pkgs.get(pkg_name)
            if old_version is None or not old_version.startswith(changelog.full_version):
                unreleased_packages[pkg_name] = {
                    "old": old_version,
                    "new": changelog.full_version,
                    "bugs": self._get_bugs(pkg_name),
                }
        return unreleased_packages

    def _get_bugs(self, pkg_name):
        try:
            with open(f"doc/errata/staging/{pkg_name}.yaml") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            return []
        return list(data.get("bugs", {}).keys())

    def _update_type(self):
        return "APP" if self._has_major_update() else "PACKAGE"

    def _get_issue_title(self):
        schoolversion = self.latest_app["schoolversion"]
        if self._update_type() == "APP":
            schoolversion = str(int(schoolversion) + 1)
        version = f"{self.latest_app['ucsversion']}v{schoolversion}"
        return f"[{self._update_type()}] Release UCS@school {version}"

    def _issue_template(self):
        template = "package_update_issue" if self._update_type() == "PACKAGE" else "release_issue"
        resp = requests.get(
            f"https://git.knut.univention.de/api/v4/projects/1574/templates/issues/{template}",
            headers=self.headers,
        )
        resp.raise_for_status()
        return resp.json()["content"]

    def _find_existing_release_issue(self):
        """
        Return the open release issue for this UCS version, regardless of update type.

        Both update types share the same identity (one release being assembled per
        UCS version), so we match on the title pattern instead of the exact title.
        This lets us find a `[PACKAGE]` issue even when the release has meanwhile
        escalated to `[APP]` (and vice versa), so it can be converted in place
        instead of creating a duplicate and losing its comments.
        """
        title_re = re.compile(
            rf"^\[(?:APP|PACKAGE)\] Release UCS@school {re.escape(self.ucsversion)}v\d+$"
        )
        resp = requests.get(
            "https://git.knut.univention.de/api/v4/projects/1574/issues",
            headers=self.headers,
            params={
                "state": "opened",
                "search": "Release UCS@school",
                "in": "title",
                "per_page": "100",
            },
        )
        resp.raise_for_status()
        for issue in resp.json():
            if title_re.match(issue["title"]):
                return issue
        return None

    def _get_release_issue(self):
        desired_title = self._get_issue_title()
        issue = self._find_existing_release_issue()
        if issue is None:
            return self._create_new_issue()
        if issue["title"] != desired_title:
            issue = self._convert_issue(issue, desired_title)
        return issue

    def _convert_issue(self, issue, desired_title):
        """
        Convert an existing issue between a package update and an app release.

        The issue is kept (so its comments and discussion are preserved); only the
        title and the description template are swapped and an explanatory note is
        added. The context/packages sections are filled in afterwards by
        `_update_release_issue`.
        """
        print(f"Converting release issue '{issue['title']}' -> '{desired_title}'")
        kind = "an app release" if self._update_type() == "APP" else "a package update"
        self._add_note(
            issue["iid"],
            f"This release issue was automatically converted from **{issue['title']}** to "
            f"**{desired_title}**, because the set of unreleased packages now requires {kind}.",
        )
        resp = requests.put(
            f"https://git.knut.univention.de/api/v4/projects/1574/issues/{issue['iid']}",
            headers=self.headers,
            data={"title": desired_title},
        )
        resp.raise_for_status()
        issue = resp.json()
        # Swap the body to the template that matches the new update type.
        issue["description"] = self._issue_template()
        return issue

    def _add_note(self, iid, body):
        resp = requests.post(
            f"https://git.knut.univention.de/api/v4/projects/1574/issues/{iid}/notes",
            headers=self.headers,
            data={"body": body},
        )
        resp.raise_for_status()

    def _create_new_issue(self):
        resp = requests.post(
            "https://git.knut.univention.de/api/v4/projects/1574/issues",
            headers=self.headers,
            data={
                "title": self._get_issue_title(),
                "description": self._issue_template(),
            },
        )
        resp.raise_for_status()
        # A status can only be set on a WorkItem
        # The rest api doesn't support WorkItems :(
        mutation = """
mutation($noteableId: NoteableID!, $body: String!) {
  createNote(input: { noteableId: $noteableId, body: $body }) {
    note {
      id
      body
      createdAt
    }
    errors
  }
}
"""
        variables = {
            "noteableId": f"gid://gitlab/WorkItem/{resp.json()['id']}",
            "body": '/status "Planned" ',
        }
        headers = {
            "Authorization": f"Bearer {self.headers['PRIVATE-TOKEN']}",
            "Content-Type": "application/json",
        }
        note_resp = requests.post(
            "https://git.knut.univention.de/api/graphql",
            json={"query": mutation, "variables": variables},
            headers=headers,
        )
        note_resp.raise_for_status()
        print(note_resp.json())
        return resp.json()

    def _update_release_issue(self, issue):
        schoolversion = self.latest_app["schoolversion"]
        if self._update_type() == "APP":
            schoolversion = str(int(schoolversion) + 1)
        description = re.sub(
            self.context_re,
            self.context_template.format(version=f"{self.latest_app['ucsversion']}v{schoolversion}"),
            issue["description"],
        )
        description = re.sub(
            self.packages_re,
            self.packages_template.format(
                packages="\n".join(
                    f"- `{package}`: **{v['old'] if v['old'] is not None else 'new package'}** "
                    f"-> **{v['new']}** ({self._get_bug_string(package)})"
                    for package, v in self.unreleased_packages.items()
                )
            ),
            description,
        )
        resp = requests.put(
            f"https://git.knut.univention.de/api/v4/projects/1574/issues/{issue['iid']}",
            headers=self.headers,
            data={
                "description": description,
            },
        )
        resp.raise_for_status()

    def _get_bug_string(self, pkg_name):
        bugs = self.unreleased_packages[pkg_name]["bugs"]
        if not bugs:
            return "⚠ No valid yaml ⚠"
        return ", ".join(
            f"[{bug}](https://forge.univention.org/bugzilla/show_bug.cgi?id={bug})" for bug in bugs
        )

    @staticmethod
    def _major_version(version):
        # Drop a Debian epoch ("4:5.2" -> "5.2") and take the leading number of
        # the upstream version. Returns 0 if no leading digit is present.
        upstream = version.split(":", 1)[-1]
        match = re.match(r"\d+", upstream)
        return int(match.group()) if match else 0

    def _has_major_update(self):
        for version in self.unreleased_packages.values():
            # A new source package cannot be shipped as an errata into an
            # existing app version, so it always requires a full app release.
            if version["old"] is None:
                return True
            if self._major_version(version["old"]) < self._major_version(version["new"]):
                return True
        return False


if __name__ == "__main__":
    releaseIssue = RelaeseIssue()
    releaseIssue.update()
