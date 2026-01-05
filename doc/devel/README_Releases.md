# Release instructions for a UCS@school App Release

<!--
SPDX-FileCopyrightText: 2020-2026 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

There are two modes of release for UCS@school at the moment: A application release and a Debian package update for an _already published_ app version.
This document describes how to prepare and execute a application release for the UCS@school App. For a Debian package update, see [README_Erratum.md](./README_Erratum.md).
A checklist is provided in the [release issue template](https://git.knut.univention.de/univention/dev/education/ucsschool/-/blob/5.2/.gitlab/issue_templates/release_issue.md)
each item in that checklist corresponds to a subsection in this document.

## Pre-Release Preparation

### Prepare a VM for testing

If you don't have one already, create a VM with the [UCS@school images repository](https://git.knut.univention.de/univention/dev/internal/ucsschool-images).

### Check the minimum required UCS errata version

If needed for any package/feature, the minimum required UCS errata version can
be set in the UCS@school App Center App configuration.

Keep in mind that the required errata level must not exceed the latest patch
level release of UCS. This is due to the fact that customers should be able to
join secondary nodes without updating them first. More info at
https://help.univention.com/t/release-modalities-of-ucs-school/21861

## Verify Jenkins Tests

Check the following Jenkins Tests for errors related to the changes that are to be published.

- [Install Multiserver Test](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.2/view/Daily%20Tests/job/Install%20Multiserver/)
- [Install Singleserver Test](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.2/view/Daily%20Tests/job/Install%20Singleserver/)
- [Upgrade Multiserver Test](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.2/job/Upgrade%20Multiserver/)
- [Upgrade Singleserver Test](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.2/job/Upgrade%20Singleserver/)

## Tag an appropriate commit with the `release-<version>` tag

A tag of the form `release-<version>` will trigger a release pipeline.
The release pipeline will always contain a `doc-pipeline` in the `build` stage,
which can be used to publish the documentation for the specific `<version>`.
Additionally, the `release` stage contains a `do_release` job, which, when triggered,
will publish the app with version `<version>`.

## Publish Application with the `do_release` job in the tag pipeline

Click on the `do_release` job in the tag pipeline.
This will publish the UCS@school app and, if successful,
will also send an email announcement and rocket chat message.

## Publish manual with the manual with the `docs-merge-to-one-artifact` job

Clicking on `docs-merge-to-one-artifact` will trigger the creation of a merge request in another repository,
https://git.knut.univention.de/univention/docs.univention.de, which contains the documentation
changes made in the UCS@school repository. The merge request is set to merge automatically, the only manual thing
to do is, for technical reasons, to restart the `trigger search-index-update` job in the deploy stage on the merge pipeline.

## Update other public documentation

### Update/Close bugzilla bugs

Set all Bugs published with this release to *CLOSED*.
You can get the bug numbers with this snippet:

```shell
cd ~/git/doc/errata/published/
grep bug: 2019-04-11-*.yaml | cut -d: -f2- | tr -d 'bug: []' | tr ',' '\n' | sort -u | tr '\n' ',' ; echo
```
List the bugs in Bugzilla in the extended search by pasting the list in *Bugs numbered*.
Now click on *Change Several Bugs at Once* underneath the columns.
This will enable you to select and modify the bugs you need.

Adjust and use this text as the comment for closing the mentioned bugs:

```
UCS@school <version> has been released.

- https://docs.software-univention.de/ucsschool-changelog/<version>/en/changelog.html
- https://docs.software-univention.de/ucsschool-changelog/<version>/de/changelog.html

If this error occurs again, please clone this bug.
```

For new features, omit the last line.

### Create new target milestone in bugzilla

There are only some people with the permission to do so.
Ask one of the following persons to do it: Sönke, Florian, Arvid, Felix or Nico.

### Update the maintenance information

See [release-dates](https://git.knut.univention.de/univention/dist/release-dates) and the [ucsschool.yaml](https://git.knut.univention.de/univention/infrastructure/private/release-dates/-/blob/master/src/release_dates/products/ucsschool.yaml).
Adjust the previous release by adding the `date_maintenance` item.

### Update the overview pages

The [overview pages](https://git.knut.univention.de/univention/documentation/ucs-doc-overview-pages) need to be updated when a new app version has been released.
See the README in that repository. You'll need to update the `conf.py`, `ucsschool-changelog.rst` and `ucsschool-maintained.txt`.

Additionally, update the translation:

```bash
docker run -ti --rm -v "$PWD:/project" -w /project -u $UID --network=host --pull always docker-registry.knut.univention.de/sphinx:latest make -C navigation gettext
docker run -ti --rm -v "$PWD:/project" -w /project -u $UID --network=host --pull always docker-registry.knut.univention.de/sphinx:latest bash -c 'cd navigation && sphinx-intl update -l de'
```

A commit that shows the necessary changes is [50442cff63066603b3fbc4e7f73cb39c26ea8e72](https://git.knut.univention.de/univention/dev/docs/docs-overview-pages/-/commit/50442cff63066603b3fbc4e7f73cb39c26ea8e72).

After merging the MR, follow the [doc pipeline](https://git.knut.univention.de/univention/documentation/ucs-doc-overview-pages/-/pipelines),
and then check that the links appear under the [UCS@school changelogs](https://docs.software-univention.de/release-notes_5.2.html.en).

### Add new document to search index

Update the `docsearch.config.json` in the [docsearch repository](https://git.knut.univention.de/univention/documentation/docsearch/) with the new changelog document.
If any other new document or document-version was added with this release, also add that document to the `docsearch.config.json`.

### Update the latest link

Finally, you should update [docs.univention.de](https://git.knut.univention.de/univention/docs.univention.de/-/blob/master/ucsschool-changelog/latest) to point to the latest version.
```
# in the repo root
cd ucsschool-changelog
rm latest
ln -s <version> latest
```

## QA the release

On the previously prepared VM, update to the new UCS@school version and do a smoke test.

Follow the steps for [QAing the release](README_qa_for_release.md).
