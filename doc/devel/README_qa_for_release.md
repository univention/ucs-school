## QA for a Release

<!--
SPDX-FileCopyrightText: 2023-2024 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

These steps should be completed as QA after finishing either a
[full release](README_Releases.md) or an [errata_release](README_Erratum.md).

**QA Checklist:** (Copy into gitlab issue)

- [ ] All packages have been uploaded to the [public appcenter](http://appcenter.software-univention.de/univention-repository/5.0/maintained/component/ucsschool_20230802094418/).
- [ ] Using an existing [UCS@school multi-server env](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Environments/job/SchoolMultiserverEnvironment/) verify that you can update the Primary Directory Node and the Replica Directory Node successfully, and that changelog output is correct.
- [ ] All Bugzilla bugs have been closed.
- [ ] All yaml files have been renamed (`doc/errata/published/2021-05-26-*`)
- [ ] The [manuals](https://docs.software-univention.de/index.html) have been updated for German and (if applicable) English.
- [ ] The changelog for [German](https://docs.software-univention.de/ucsschool-changelog/5.0v4/de/changelog.html) and [English](https://docs.software-univention.de/ucsschool-changelog/5.0v4/en/changelog.html) has been built and uploaded.
- [ ] [help.univention.com](https://help.univention.com/t/release-ankundigungen-fur-ucs-school-5-0-stand-17-11-2022/20184) text updated.
- [ ] Internal announcement mail.
- [ ] Created gitlab issue for the next errata release.

### How to verify apps in production

Prior to doing a release, you should have set up a [UCS@school multi-server env](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Environments/job/SchoolMultiserverEnvironment/).

On the VMs that you created for testing, verify that you can update each of the nodes to the latest production version.
You can run an update on each node with the following command:

```shell
echo univention > /tmp/pass
univention-upgrade --ignoressh --noninteractive --enable-app-updates --username Administrator --pwdfile /tmp/pass
```

Watch the update messages and verify that any release notes are what you expect.

Then verify that all packages you released are present and match their current release version. For example:

```shell
apt search ucs-school-lib
```

If anything is missing, you can verify it visually in the [production AppCenter](https://appcenter.software-univention.de/meta-inf/5.0/ucsschool/).

