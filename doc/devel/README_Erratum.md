# Release instructions for a UCS@school Errata Release

<!--
SPDX-FileCopyrightText: 2020-2024 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

This document describes how to prepare and execute an Errata Release for the UCS@school App.

**Overview Checklist:** (Can be copied into gitlab release issue)

- [ ] Prepare a VM for testing
- [ ] Check packages for readiness
  - [ ] Create release issue (if not created)
  - [ ] Verify you can do an errata release, not a full release
  - [ ] Verify Jenkins tests
  - [ ] Verify YAML advisories
- [ ] Update Test Appcenter
- [ ] Publish to production App Center
- [ ] Publish changelog and manual
- [ ] Update public documentation
  - [ ] Send announcement email
  - [ ] Update bugzilla bugs
- [ ] QA the release
- [ ] Create next errata release issue

**NOTE:** If you are a new developer doing the release for the first time,
you should also follow the [First Time Preparation](README_manual_release.md#first-time-preparations)
section in the manual release documentation.

## Prepare a VM for testing

If you don't have one already, create a [UCS@school multi-server env](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Environments/job/SchoolMultiserverEnvironment/) to use for testing when [doing QA](README_qa_for_release.md).

## Prerequisites

### Check packages for readiness

Before starting the release, [check packages for readiness](README_check_release_packages.md).

## Update Test AppCenter

### General updates

Follow the instructions for [manual release to Test AppCenter](README_manual_release.md#push-changes-to-test-appcenter).
Keep in mind:

* You will need the list of YAML files you edited in the [previous verification steps](README_check_release_packages.md#verify-yaml-advisories).
* You should make a note of the packages that get uploaded from the `copy_app_binaries` command.

## Publish to production App Center

The following code can be executed on `omar`.

The correct version string, for example `ucsschool_20230802094418`, can be found in the [Test AppCenter](https://appcenter-test.software-univention.de/meta-inf/5.0/ucsschool/) by navigating to the last (published) version.

```shell
cd /mnt/omar/vmwares/mirror/appcenter
./copy_from_appcenter.test.sh 5.0 ucsschool_20240318112841  # copies the given version to public app center on local mirror!
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

Commit the changes to git, and `cd` to the root of the `ucsschool` repository.

## Publish UCS@school documentation

Note: If you want to publish only a subset of the debian packages, you will need to edit the changelog manually and store the entries
for the packages which are not published somewhere.

The documentation is built by a [gitlab pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines)
that is triggered by a merge from `ucsschool`.
Follow the pipeline to be sure it completes correctly, and then check the
[published documentation](http://univention-repository.knut.univention.de/download/docs/).

## Update public information

### Update the release announcement wiki

Update [Release Ankündigungen für UCS@school 5.0](https://help.univention.com/t/release-ankundigungen-fur-ucs-school-5-0-stand-17-11-2022/20184)
by adding a new section below the existing ones and updating the change date in
the headline.

### Send the release announcement email

Send an internal announcement mail with the following text (**Adapt version and name**):

<pre>
To: app-announcement@univention.de
Subject: App Center: UCS@school updated

Hello everyone,

Errata have just been released for UCS@school 5.0 v4.

The changelog is available here:

- https://docs.software-univention.de/ucsschool-changelog/5.0v4/en/changelog.html
- https://docs.software-univention.de/ucsschool-changelog/5.0v4/de/changelog.html

Excerpts from the changelog:

- ...
- ...

Best regards,
UCS@school Team
</pre>

### Close Bugzilla bugs

Set all Bugs published with this Erratum to *CLOSED*.
You can get the bug numbers with this snippet (they should match the bugs you released):
```shell
cd doc/errata/published/
grep bug: $(date +%Y-%m-%d)-*.yaml | cut -d: -f2- | tr -d 'bug: []' | tr ',' '\n' | sort -u | tr '\n' ',' ; echo
```

List the bugs in Bugzilla in the extended search by pasting the list in *Bugs numbered*.
Now click on *Change Several Bugs at Once* underneath the columns.
This will enable you to select and modify the bugs you need.

Use this text as the comment for closing the mentioned bugs:
<pre>
Errata updates for UCS@school 5.0 v5 have been released.

https://docs.software-univention.de/ucsschool-changelog/5.0v5/en/changelog.html
https://docs.software-univention.de/ucsschool-changelog/5.0v5/de/changelog.html

If this error occurs again, please clone this bug.
</pre>

### Make an announcement in chat

Drop a message in `#ucsschool` in RocketChat, to let people know who might be
waiting for the release to finish.

## QA Errata Release

Follow the steps for [QAing the release](README_qa_for_release.md).
