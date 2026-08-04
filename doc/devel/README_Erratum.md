# Release instructions for a UCS@school Package Update

<!--
SPDX-FileCopyrightText: 2020-2026 Univention GmbH

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
Consider the [ucs rules](https://univention.gitpages.knut.univention.de/dev/internal/dev-handbook/guidelines/stability.html#errata-updates) as a guideline to help you decide if a package can be released as an errata.
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

## Trigger the errata release with a tag

A package update (errata) is published into an **already published** app version (for example
`5.2v4`) without creating a new app version. This is triggered by pushing a git tag of the form
`release-<app_version>-errata<N>`, where `<app_version>` is the existing version and `<N>` is an
incrementing counter so that several errata can be shipped into the same app version:

```shell
# first errata into 5.2v4
git tag release-5.2v4-errata1
git push origin release-5.2v4-errata1
```

The tag pipeline then automatically:

- resolves the app version to `5.2v4` and verifies it already exists (it never creates a new
  version and never touches the existing version's `ini`/`README` metafiles);
- builds the source packages referenced by the advisories in `doc/errata/staging/` on the UCS
  build system and uploads the resulting `.deb`s into the existing version in the **test** App
  Center (`--upload-packages-although-published`);
- runs `validate-advisories` and `check-bugzilla-bugs` on the staged advisories.

If the version part of the tag does not already exist in the App Center, `create_app_version`
fails fast — an errata can only update a published version. For a brand-new app version, do a
full [application release](README_Releases.md) (`release-<version>` without the `-errataN` suffix)
instead.

## Publish to production App Center

In the tag pipeline, trigger the manual `do_release` job. It copies the updated component from the
test App Center to production on `omar` and syncs the mirror. The subsequent `check_release` job
verifies the published `ini`.

Once `do_release` succeeds, the pipeline automatically:

- sends the announcement email (`send_mail`) and the chat message (`send_chat_message`);
- creates the GitLab release (`create_gitlab_release`);
- opens a merge request (`rename-advisories`) that moves the released advisories from
  `doc/errata/staging/` to `doc/errata/published/`, renamed with the current date and with
  `released: <app_version>` filled in. Review and merge that MR.

The "Update public information" steps below are largely automated by these jobs — the sections are
kept for reference and for the steps that still need a human (closing the Bugzilla bugs and QA).

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

This is done automatically by the `send_mail` job after `do_release` succeeds. The body is
rendered from the `.render_release_text` template in `.gitlab-ci/release.yml`; for an errata it
reads (with the version filled in from the tag):

```
To: app-announcement@univention.de
Subject: UCS@school package update for 5.2v4

Hello,

Errata have just been released for UCS@school 5.2v4.

The changelog is available here:

- https://docs.software-univention.de/ucsschool-changelog/5.2v4/en/changelog.html
- https://docs.software-univention.de/ucsschool-changelog/5.2v4/de/changelog.html

Best regards
UCS@school Team
```

If you need to highlight specific changelog excerpts, edit `.render_release_text` before tagging,
or send a manual follow-up mail.

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

This is done automatically by the `send_chat_message` job (same rendered text as the email),
posting to `#product-announcements` in RocketChat after `do_release` succeeds.

## QA Errata Release

Follow the steps for [QAing the release](README_qa_for_release.md).
