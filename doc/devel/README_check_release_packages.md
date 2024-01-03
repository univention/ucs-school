# Check Release Packages for Readiness

<!--
SPDX-FileCopyrightText: 2023-2024 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

Before doing a release, you need to ensure that you know exactly which packages
need to be released, and whether those packages are ready to be released.

Here is a quick overview of what you need to do:

* Create a release ticket (if it doesn't already exist).
* Verify whether the release can be an errata release, or needs to be a full release.
* Verify Jenkins tests
* Verify YAML advisories

## Create a release ticket

Ideally, a release issue should already exist in gitlab, blocked by all of the
issues to be released. However, if it doesn't exist, you should create the
issue and add all relevant gitlab issues. Use this release issue for all steps
in this section.

If you are doing a [full release](README_Releases.md), you also need to create
a bugzilla bug and note the number on the release issue.

## Verify whether the release should be an errata release or a full release

Not every package should be released as an errata, but instead needs to be released within a full [UCS@school App release](README_Releases.md).
Consider the [ucs rules](https://univention.gitpages.knut.univention.de/internal/dev-handbook/guidelines/stability.html#errata-updates) as a guideline to help you decide if a package can be released as an errata.
Basically you should ensure an administrator doesn't need to take manual steps during the update.

For example:
* No join script updates
* No backwards-incompatible API changes

If you had planned to do an errata release, but now realize you need to do full release, please update the release issue and notify the team of the change of plans.

## Verify Jenkins tests

Check the following Jenkins jobs for any unusual failures that might be connected to the release:

* [Install U@S 5.0 Singleserver](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Daily%20Tests/job/Install%20Singleserver/)
* [Install U@S 5.0 Multiserver](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Daily%20Tests/job/Install%20Multiserver/)

## Verify Gitlab Issues and Bugzilla Bugs

On the gitlab errata release issue, there should be a list of issues blocking the errata release.
Every issue should be in a closed status; if it isn't, it needs to be removed from the current release and put into the next release.

Log into [Bugzilla](https://forge.univention.org/bugzilla/index.cgi), and do a comma-separated search for each of the bugs in the release (e.g. `55986,55751,50841`).
For each bug:

- Status should be "VERIFIED FIXED".
- Should have an assignee + QA person listed.
- Target milestone should be set (e.g., UCS@school 5.0 v4 errata).

## Verify YAML advisories

For each bug in the errata release, you need to verify the YAML advisories in the `ucsschool` repository.
In your local `ucsschool` repository:

```shell
git checkout main
git pull
cd ~/git/ucsschool/doc/errata/staging
```

First, make sure that all files are correctly labeled with the `*.yaml` extension and fix anything that is `.yml`.
This ensures that scripts in these docs work as expected:

```shell
find . -name "*.yml" -exec bash -c 'mv "$0" "${0%.yml}.yaml"' {} \;
```

Commit the changes to git.

In order to release a package, you have to verify that:

1. The advisory does not contain other bugs that are not part of the release.

   You can use [this script](https://git.knut.univention.de/univention/internal/research-library/-/blob/main/personal/jleadbetter/scripts/find_advisories) to automatically check which bugs are safe to release, and to find all advisory files you need to include in the release. Pass the bug numbers to the script:

   ```
   cd ~/git/ucsschool/doc/errata/staging
   ./find_advisories 12345 23456 34567
   ```

   Make a note of the advisory files found for the release.
   You will need them later for
   [pushing changes to Test AppCenter](README_manual_release.md#push-changes-to-test-appcenter)
   and when you move them to the `published` folder in preparation for
   [generating a changelog](../ucsschool-changelog/README.md).

2. The advisory is in the correct format.

   Use [this script](https://git.knut.univention.de/univention/internal/research-library/-/blob/main/personal/twenzel/scripts/check_yamls.py) to verify mistakes.

   ```
   cd ~/git/ucsschool/doc/errata/staging
   python3 check_yamls.py --folder .
   ```

3. In your editor of choice, do a manual inspection of each of the advisories:

  - Are the advisory messages for each bug in good English, easy to understand, and without spelling errors?
  - Is the advisory message in the right file (e.g., sometimes we confuse `ucs-school-import` and `ucs-school-umc-import`)?
  - Compare the debian-changelog version and the advisory `fix` version.
  - Compare the advisory `fix` version with build details in the gitlab issue and/or the bugzilla bug.

## One last check of what has changed

Ideally, the issues to be released will all be in the gitlab issue.
However, you may want to do a rough visual check of which packages have changed, to verify that you don't have additional packages that might have been forgotten.

```shell
cd ~/git/ucsschool
# order files by last changed in git
git ls-files -z | xargs -0 ls -lt
```

This command may catch:

* Unreleased issues you didn't know about, which should be included in the release.
* Where a released issue touched multiple packages, but forgot to update the changelog for all of them.

If you see any recent package changes that don't correspond to advisories, you may need to ask about them in `#ucsschool-dev` chat.

