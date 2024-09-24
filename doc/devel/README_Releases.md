# Release instructions for a UCS@school App Release

<!--
SPDX-FileCopyrightText: 2020-2024 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

This document describes how to prepare and execute a full release for the UCS@school App.

**Overview Checklist:** (Can be copied into gitlab release issue)

- [ ] Prepare a VM for testing
- [ ] Check packages for readiness
  - [ ] Create release issue (if not created)
  - [ ] Create Bugzilla bug
  - [ ] Verify Jenkins tests
  - [ ] Verify YAML advisories
  - [ ] Tag an appropriate commit with the `release-<version>` tag
- [ ] Create new changelog
  - [ ] Create a new link on the UCS changelog pages
- [ ] Create new version in Test Appcenter
  - [ ] Adjust the version in the README files in the test appcenter
- [ ] Publish to Test Appcenter
- [ ] Verify release in Selfservice Center
- [ ] Publish to production Appcenter
- [ ] Publish manual
- [ ] Update public documentation
  - [ ] Update release wiki
  - [ ] Update bugzilla bugs
- [ ] QA the release
- [ ] Create new target milestone in bugzilla
- [ ] Create next errata release issue
- [ ] Update README release documentation (both full and errata) so that bash commands and html links point to the correct versions of UCS@school.
- [ ] Check if the maintenance information has to be updated (https://docs.software-univention.de/n/en/maintenance/ucsschool.html#maintenance-ucsschool)
    - See READMEs on https://git.knut.univention.de/univention/dist/release-dates and https://git.knut.univention.de/univention/documentation/ucs-doc-overview-pages
    - [ ] If a new document has been added, add it to `docsearch.config.json` in repository https://git.knut.univention.de/univention/documentation/docsearch/
- [ ] Send announcement email

**NOTE:** If you are a new developer doing the release for the first time,
you should also follow the [First Time Preparation](README_manual_release.md#first-time-preparations)
section in the manual release documentation.

### Prepare a VM for testing

If you don't have one already, create a [UCS@school multi-server env](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Environments/job/SchoolMultiserverEnvironment/) to use for testing when [doing QA](README_qa_for_release.md).

## Before you begin

### Check the minimum required UCS errata version

If needed for any package/feature, the minimum required UCS errata version can
be set in the UCS@school App Center App configuration.

Keep in mind that the required errata level must not exceed the latest patch
level release of UCS. This is due to the fact that customers should be able to
join secondary nodes without updating them first. More info at
https://help.univention.com/t/release-modalities-of-ucs-school/21861

### Check packages for readiness

Before doing a release, [check packages for readiness](README_check_release_packages.md).

## Create new changelog

### Remove old advisories

The new changelog should not include any of the advisories from previous releases.
To remove them:

```shell
cd ~/git/ucsschool/doc/errata/published
git rm *
```

### Move the advisories to published

You will need the list of YAML files you edited in the [Verify YAML Advisories](README_check_release_packages.md#verify-yaml-advisories) step.

In your local `ucsschool` repository, move the YAML advisories into the `doc/errata/published` folder, renamed with the current date:

```shell
cd ~/git/ucsschool/doc/errata/staging
release_files=( "ucs-school-lib.yaml" "ucs-school-umc-users.yaml" )
for file in "${release_files[@]}"; do git mv "$file" "$(echo $file | sed "s/^/..\/published\/$(date +%Y-%m-%d)-/")"; done
```

Commit the changes to git, and `cd` to the root of the `ucsschool` repository.

### Generate the changelog

Open up a second terminal for running docker commands.
Follow the instructions in the changelog [README](../../doc/ucsschool-changelog/README.md).

```shell
git add -u
git commit -m "Bug #${BUGNUMBER}: ucsschool 5.0v6 changelog"
git push
```

Check the [Doc Pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines) from the automatic
commit from Jenkins and check the [staged documentation](http://univention-repository.knut.univention.de/download/docs/).

Then add a link to the new `docs.univention.de` overview page:

```shell
git clone git@git.knut.univention.de:documentation/ucs-doc-overview-pages.git
cd ~/git/ucs-doc-overview-pages
vi documentation/ucs-doc-overview-pages/navigation/docs/ucsschool-changelog.rst
```

Search for `v6` and create similar entries for `v7`. Then commit and create an MR.

After merging the MR, follow the [doc pipeline](https://git.knut.univention.de/univention/documentation/ucs-doc-overview-pages/-/pipelines),
and then check that the links appear under the [UCS@school changelogs](https://docs.software-univention.de/release-notes_5.0.html.en).

Finally, you should update [docs.univention.de](https://git.knut.univention.de/univention/docs.univention.de/-/blob/master/ucsschool-changelog/latest) to point to the latest version.

## Create new version in Test AppCenter and publish new packages

The following commands can be run on `omar` to create a new release version:

```shell
univention-appcenter-control new-version "5.0/ucsschool=5.0 v6" "5.0/ucsschool=5.0 v7"
```

Then publish the packages to Test Appcenter:

```shell
# copy_app_binaries -r <ucs-major-minor> -v <app-version> -u <yaml-datei> ...
# For example:
cd ~/git/ucsschool/doc/errata/staging
copy_app_binaries -r 5.0 -v "5.0 v6" -u ucs-school-lib.yaml ucs-school-umc-diagnostic.yaml
```

The `ucs-test-ucsschool` package should also be released, if it is safe to do so.
Please see the instructions in the [manual release](README_manual_release.md#ucs-test-ucsschool-updates), being sure to use `v6` instead of `v4` in the commands.

## Verify information in the Selfservice Center

**NOTE:** You will want to do this step before publishing to production.
If you need to make any changes after publishing, you will need to re-run the publishing steps again.

Go to the [Selfservice Center](https://selfservice.software-univention.de/univention/management/#module=appcenter-selfservice) and search for the UCS@school app.

Click on the UCS@school app and look for the current "unpublished" version.
The "unpublished" version should match your expected release target.
(If it does not exist, go back to the search screen, right click on the UCS@school
icon, and select "New app version" to create one).

Choose "Additional texts" from the menu on the left side. Read all of the texts
and verify that the links/texts are correct and they point to the correct
version of the release (and not the previous version).

## Publish packages to production AppCenter

This code should be run `dimma` or `omar`.
First, determine the `COMPONENT` id for the next step:

```shell
univention-appcenter-control status ucsschool
```

Then publish to the production Appcenter:

```shell
cd /mnt/omar/vmwares/mirror/appcenter
# copy the given version to public app center on local mirror. Use the COMPONENT id.
./copy_from_appcenter.test.sh 5.0 ucsschool_20230804115933
# syncs the local mirror to the public download server
sudo update_mirror.sh -v appcenter
```

## Publish UCS@school manual

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
```
To: app-announcement@univention.de
Subject: App Center: UCS@school 5.0 v6 released

Hello all,

the following app update has just been released:
- UCS@school 5.0 v6

The changelog is available here:

- https://docs.software-univention.de/ucsschool-changelog/5.0v6/en/changelog.html
- https://docs.software-univention.de/ucsschool-changelog/5.0v6/de/changelog.html

Excerpts from the changelog:
- ...
- ...

Greetings,

 $NAME
```

### Close Bugzilla bugs

Set all Bugs published with this release to *CLOSED*.
You can get the bug numbers with this snippet:

```shell
cd ~/git/doc/errata/published/
grep bug: 2019-04-11-*.yaml | cut -d: -f2- | tr -d 'bug: []' | tr ',' '\n' | sort -u | tr '\n' ',' ; echo
```
List the bugs in Bugzilla in the extended search by pasting the list in *Bugs numbered*.
Now click on *Change Several Bugs at Once* underneath the columns.
This will enable you to select and modify the bugs you need.


Use this text as the comment for closing the mentioned bugs:
```
UCS@school 5.0 v6 has been released.

- https://docs.software-univention.de/ucsschool-changelog/5.0v6/en/changelog.html
- https://docs.software-univention.de/ucsschool-changelog/5.0v6/de/changelog.html

If this error occurs again, please clone this bug.
```

### Make an announcement in chat

Drop a message in `#ucsschool` in RocketChat, to let people know who might be
waiting for the release to finish.


## QA Release

Follow the steps for [QAing the release](README_qa_for_release.md).
