# Release instructions for a UCS@school Errata Release

This document describes how to prepare and execute an Errata Release for the UCS@school App.

## Check packages for readiness

- Collect the YAML files for all packages that are to be released in the erratum.
- Check errata texts for mistakes and unclear content. Correct if need be.
- Run [Errata Checks](https://jenkins.knut.univention.de:8181/job/Mitarbeiter/job/schwardt/job/UCSschool%20CheckErrataForRelease)
  to verify that all selected packages are ready for release.

## Update TestAppCenter

- Run [Errata Announce](https://jenkins.knut.univention.de:8181/job/UCSschool-4.3/job/Announce%20UCSschool%204.3%20Erratum/)
  with the chosen yaml files to release an Errata for the latest UCS@school version.
  - **This will need manual interaction to verify the changelog changes before committing!**
  - Changelog will be modified
  - Upload of binaries to TestAppCenter
  - Moving of advisories to published
- Upload current *ucs-test-ucsschool* package to TestAppCenter with `univention-appcenter-control upload --upload-packages-although-published '4.4/ucsschool=4.4 v9' $(find /var/univention/buildsystem2/apt/ucs_4.4-0-ucs-school-4.4/ -name 'ucs-test-ucsschool*.deb')`.
  This has to be executed **on omar**.

## Publish to production App Center

The following code should be executed on omar:

```shell
cd /mnt/omar/vmwares/mirror/appcenter
./copy_from_appcenter.test.sh 4.4  # copies current state of test app center to omar and lists all available app center repositories
./copy_from_appcenter.test.sh 4.4 ucsschool_20180112151618  # copies the given version to public app center on local mirror!
sudo update_mirror.sh -v appcenter  # syncs the local mirror to the public download server!
```

## Publish manual

Run [Publish Docs](https://jenkins.knut.univention.de:8181/view/Publish/job/Publish_docs.univention.de/).
This Jenkins job requires manual intervention to approve the new documentation in two instances!

## Update public information

Update [Release Ankündigungen für UCS@school 4.4](https://help.univention.com/t/release-ankundigungen-fur-ucs-school-4-4-stand-12-10-2020/12064)
by adding a new section **above** the existing ones.

Send an internal announcement mail with the following text (**Adapt version and name**):
<pre>
To: app-announcement@univention.de
Subject: App Center: UCS@school aktualisiert

Hallo zusammen,

für UCS@school 4.4 v9 wurden soeben Errata freigegeben.

Das Changelog ist hier abrufbar:
http://docs.software-univention.de/changelog-ucsschool-4.4v9-de.html

Auszüge aus dem Changelog:
- ...
- ...

Viele Grüße,

 $NAME
</pre>

Set all Bugs published with this Erratum to *CLOSED*. You can get all relevant bug numbers with this snippet:
```shell
cd doc/errata/published/
grep bug: 2019-04-11-*.yaml | cut -d: -f2- | tr -d 'bug: []' | tr ',' '\n' | sort -u | tr '\n' ',' ; echo
```

Use this text as the comment for closing the mentioned bugs:
<pre>
Errata updates for UCS@school 4.4 v9 have been released.

https://docs.software-univention.de/changelog-ucsschool-4.4v9-de.html

If this error occurs again, please clone this bug.
</pre>