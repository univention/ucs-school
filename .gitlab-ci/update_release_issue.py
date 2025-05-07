#!/usr/bin/env python3

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
            if (
                pkg_name not in released_sources_pkgs
                or released_sources_pkgs[pkg_name] != changelog.full_version
            ):
                unreleased_packages[pkg_name] = {
                    "old": released_sources_pkgs[pkg_name],
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

    def _get_issue_title(self):
        schoolversion = self.latest_app["schoolversion"]
        update_type = "PACKAGE"
        if self._has_major_update():
            schoolversion = str(int(schoolversion) + 1)
            update_type = "APP"
        return f"[{update_type}] Release UCS@school {self.latest_app['ucsversion']}v{schoolversion}"

    def _get_release_issue(self):
        resp = requests.get(
            "https://git.knut.univention.de/api/v4/projects/4/search",
            data={
                "scope": "issues",
                "search": self._get_issue_title(),
                "state": "opened",
                "fields": "title",
            },
            headers=self.headers,
        )
        if resp.status_code != 200 or len(resp.json()) == 0:
            resp = requests.get(
                "https://git.knut.univention.de/api/v4/projects/4/templates/issues/release_issue",
                headers=self.headers,
            )
            resp = requests.post(
                "https://git.knut.univention.de/api/v4/projects/4/issues",
                headers=self.headers,
                data={
                    "title": self._get_issue_title(),
                    "description": resp.json()["content"],
                },
            )
            resp.raise_for_status()
            return resp.json()
        else:
            return resp.json()[0]

    def _update_release_issue(self, issue):
        schoolversion = self.latest_app["schoolversion"]
        if self._has_major_update():
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
                    f"- `{package}`: **{v['old']}** -> **{v['new']}** ({self._get_bug_string(package)})"
                    for package, v in self.unreleased_packages.items()
                )
            ),
            description,
        )
        resp = requests.put(
            f"https://git.knut.univention.de/api/v4/projects/4/issues/{issue['iid']}",
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

    def _has_major_update(self):
        for version in self.unreleased_packages.values():
            if version["old"].split(".")[0] < version["new"].split(".")[0]:
                return True
        return False


if __name__ == "__main__":
    releaseIssue = RelaeseIssue()
    releaseIssue.update()
