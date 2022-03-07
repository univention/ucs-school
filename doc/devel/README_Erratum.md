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
- Upload current *ucs-test-ucsschool* package to TestAppCenter with `univention-appcenter-control upload --upload-packages-although-published '5.0/ucsschool=5.0 v1' $(find /var/univention/buildsystem2/apt/ucs_5.0-0-ucs-school-5.0/ -name 'ucs-test-ucsschool*.deb')`.
  This has to be executed **on omar**.

## Publish to production App Center

The following code should be executed on omar:

The correct version string, for example `ucsschool_20180112151618` can be found here
https://appcenter-test.software-univention.de/meta-inf/4.4/ucsschool/ by navigating to the last (published) version.

```shell
cd /mnt/omar/vmwares/mirror/appcenter
./copy_from_appcenter.test.sh 5.0 ucsschool_20180112151618  # copies the given version to public app center on local mirror!
sudo update_mirror.sh -v appcenter  # syncs the local mirror to the public download server!
```

## Publish manual

Check the [Doc Pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines) from the automatic
commit from Jenkins and check the [staged documentation](http://univention-repository.knut.univention.de/download/docs/).

If everything is in order run the deploy job to publish the new documentation.

## Update public information

Update [Release Ankündigungen für UCS@school 5.0](https://help.univention.com/t/release-ankundigungen-fur-ucs-school-4-4-stand-12-10-2020/12064)
by adding a new section **above** the existing ones.

Send an internal announcement mail with the following text (**Adapt version and name**):
<pre>
To: app-announcement@univention.de
Subject: App Center: UCS@school aktualisiert

Hallo zusammen,

für UCS@school 5.0 v1 wurden soeben Errata freigegeben.

Das Changelog ist hier abrufbar:
http://docs.software-univention.de/changelog-ucsschool-5.0v1-de.html

Auszüge aus dem Changelog:
- ...
- ...

Viele Grüße,

 $NAME
</pre>

Set all Bugs published with this Erratum to *CLOSED*.
You can get the bug numbers with this snippet:
```shell
cd doc/errata/published/
grep bug: 2019-04-11-*.yaml | cut -d: -f2- | tr -d 'bug: []' | tr ',' '\n' | sort -u | tr '\n' ',' ; echo
```

List the bugs in Bugzilla in the extended search by pasting the list in *Bugs numbered*.
Now click on *Change Several Bugs at Once* underneath the columns.
This will enable you to select and modify the bugs you need.


Use this text as the comment for closing the mentioned bugs:
<pre>
Errata updates for UCS@school 5.0 v1 have been released.

https://docs.software-univention.de/changelog-ucsschool-5.0v1-de.html

If this error occurs again, please clone this bug.
</pre>

## QA Errata Release

Do the following checks and document the result in Taiga/Bugzilla/Gitlab:

* OK: all packages have been uploaded to the public appcenter (http://appcenter.software-univention.de/univention-repository/5.0/maintained/component/ucsschool_20201208103021/)
* OK: successfully updated in a multi-server env Primary Directory Node and Replica Directory Node
* OK: all bugs have been closed (52945, 49102, 49557)
* OK: all yaml files have been renamed (`doc/errata/published/2021-05-26-*`)
* OK: manual updated (https://docs.software-univention.de/ucsschool-handbuch-5.0.html)
* OK: the changelog has been build and uploaded (http://docs.software-univention.de/changelog-ucsschool-5.0v1-de.html)
* OK: help.univention.com text updated (https://help.univention.com/t/release-ankundigungen-fur-ucs-school-4-4-stand-26-05-2021/12064)
* OK: internal announcement mail
* OK: new git tag (`release-5.0v10`) OR no new git tag, as the apps version didn't change
