# Release instructions for a UCS@school Package Update

<!--
SPDX-FileCopyrightText: 2020-2025 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

This document describes how to prepare and execute an Errata Release for the UCS@school App.
A checklist is provided in the [package update issue template](https://git.knut.univention.de/univention/dev/education/ucsschool/-/blob/5.2/.gitlab/issue_templates/package_update_issue.md)
each item in that checklist corresponds to a subsection in this document.
For an application release, refer to [README_Releases.md](./README_Releases.md).

**NOTE:** If you are a new developer doing the release for the first time,
you should also follow the [First Time Preparation](README_manual_release.md#first-time-preparations)
section in the manual release documentation.

## Pre-Release Preparation

### Prepare a VM for testing

If you don't have one already, create a VM with the [UCS@school images repository](https://git.knut.univention.de/univention/dev/internal/ucsschool-images).

### Verify you can do an errata release, not a full release

Not every package should be released as a package update, but instead needs to be released within a full [UCS@school App release](README_Releases.md).
Consider the [ucs rules](https://univention.gitpages.knut.univention.de/internal/dev-handbook/guidelines/stability.html#errata-updates) as a guideline to help you decide if a package can be released as an errata.
Basically you should ensure an administrator doesn't need to take manual steps during the update.

For example:
* No join script updates
* No backwards-incompatible API changes

If you had planned to do an errata release, but now realize you need to do full release, please update the release issue and notify the team of the change of plans.

### Verify Jenkins tests

Check the following Jenkins jobs for any unusual failures that might be connected to the release:

- [Install Multiserver Test](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.2/view/Daily%20Tests/job/Install%20Multiserver/)
- [Install Singleserver Test](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.2/view/Daily%20Tests/job/Install%20Singleserver/)
- [Upgrade Multiserver Test](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.2/job/Upgrade%20Multiserver/)
- [Upgrade Singleserver Test](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.2/job/Upgrade%20Singleserver/)

## Push changes to Test Appcenter

**NOTE:** If you are doing the release for `4.4`, execute the following steps on `dimma`.
Otherwise, execute the steps on `ladda`.

Make sure you have the current version of `ucsschool` and release scripts:

```shell
for DIR in ~/git/*; do (cd $DIR; git pull); done
```

Now push the changes to the Test Appcenter.
For example, to upload `ucs-school-import ucs-school-umc-internetrules` and `ucs-school-import` to UCS@school 5.2 v1:

```shell
cd ~/git/ucsschool/doc/errata/staging
copy_app_binaries --yes-i-really-want-to-upload-to-published-components -r 5.2 -v "5.2v4" -u \
    ucs-school-import.yaml \
    ucs-school-umc-internetrules.yaml
```

## Publish to production App Center

The following code can be executed on `omar`.

The correct version string, for example `ucsschool_20230802094418`, can be found in the [Test AppCenter](https://appcenter-test.software-univention.de/meta-inf/5.2/ucsschool/) by navigating to the last (published) version.

```shell
cd /mnt/omar/vmwares/mirror/appcenter
./copy_from_appcenter.test.sh 5.2 ucsschool_20240318112841  # copies the given version to public app center on local mirror!
sudo update_mirror.sh -v appcenter  # syncs the local mirror to the public download server!
```

## Move the advisories to published

You will need the list of YAML files you edited in the [Verify YAML Advisories](README_check_release_packages.md#verify-yaml-advisories) step.
In your local `ucsschool` repository, move the YAML advisories into the `doc/errata/published` folder, renamed with the current date:

```shell
cd doc/errata/staging
release_files=( "ucs-school-lib.yaml" "ucs-school-umc-users.yaml" )
for file in "${release_files[@]}"; do git mv "$file" "$(echo $file | sed "s/^/..\/published\/$(date +%Y-%m-%d)-/")"; done
```

:warning: Make sure that all moved yaml files contain a line `released: <VERSION>` with your specific UCS\@school version, for example `5.2v4`.

Commit the changes to git, and `cd` to the root of the `ucsschool` repository.

## Publish UCS@school documentation

To publish UCS@school documentation, follow these steps:

The documentation is built by a [gitlab pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines)
that has to be triggered manually: Please do the following:

1. [Create a new pipeline](https://git.knut.univention.de/univention/dev/education/ucsschool/-/pipelines/new)
2. Set FORCE_DOCS and `RUN_DOCS` to `yes`.
3. Set `CHANGELOG_TARGET_VERSION` to the target App release version you need, for example `5.2v5`
4. Run the pipeline.
5. Trigger the `docs-merge-to-one-artifact` job manually

Check the [Doc Pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines) from the automatic
commit from Jenkins and check the [staged documentation](http://univention-repository.knut.univention.de/download/docs/).

## Update public information

### Send the release announcement email

Send an internal announcement mail with the following text (**Adapt version and name**):

```
To: app-announcement@univention.de
Subject: App Center: UCS@school updated

Hello everyone,

Errata have just been released for UCS@school 5.2v4.

The changelog is available here:

- https://docs.software-univention.de/ucsschool-changelog/5.2v4/en/changelog.html
- https://docs.software-univention.de/ucsschool-changelog/5.2v4/de/changelog.html

Excerpts from the changelog:

- ...
- ...

Best regards,
UCS@school Team
```

### Close Bugzilla bugs

Set all Bugs published with this package update to *CLOSED*.
You can get the bug numbers with this snippet (they should match the bugs you released):
```shell
cd doc/errata/published/
grep bug: $(date +%Y-%m-%d)-*.yaml | cut -d: -f2- | tr -d 'bug: []' | tr ',' '\n' | sort -u | tr '\n' ',' ; echo
```

List the bugs in Bugzilla in the extended search by pasting the list in *Bugs numbered*.
Now click on *Change Several Bugs at Once* underneath the columns.
This will enable you to select and modify the bugs you need.

Use this text as the comment for closing the mentioned bugs:

```
Errata updates for UCS@school 5.2v4 have been released.

https://docs.software-univention.de/ucsschool-changelog/5.2v4/en/changelog.html
https://docs.software-univention.de/ucsschool-changelog/5.2v4/de/changelog.html

If this error occurs again, please clone this bug.
```

### Make an announcement in chat

Drop a message in `#ucsschool` in RocketChat, to let people know who might be
waiting for the release to finish.

## QA Errata Release

Follow the steps for [QAing the release](README_qa_for_release.md).
