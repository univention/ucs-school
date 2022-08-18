# Release instructions for a UCS@school App Release

This document describes how to prepare and execute a full Release for the UCS@school App.

Before starting the release, check if there are any tests failing connected with the to be released changes.


## Preparations
See Preparation section in [Manual release](README_manual_release.md).

Last step for preparations is to create a Bug for the release commits.

## Check packages for readiness

- Collect the YAML files for all packages that are to be released in the new app version.
- Check errata texts for mistakes and unclear content. Correct if need be.
- Run [Errata Checks](https://jenkins.knut.univention.de:8181/job/Mitarbeiter/job/schwardt/job/UCSschool%20CheckErrataForRelease)
  to verify that all selected packages are ready for release.

## Create new version in Test AppCenter and push new packages

```shell
univention-appcenter-control new-version "5.0/ucsschool=5.0 v4" "5.0/ucsschool=5.0 v4"
univention-appcenter-control status ucsschool  # Determine component_id for next step
# appcenter-modify-README -a ucsschool -r 5.0 -v "5.0 v4" # does not exist (?)
# copy_app_binaries -r <ucs-major-minor> -v <app-version> --upload <yaml-datei> ...
# For example:
cd git/ucsschool/doc/errata/staging
copy_app_binaries -r 5.0 -v "5.0 v4" -u ucs-school-radius-802.1x.yaml ucs-school-umc-wizards.yaml
# Upload current ucs-test-ucsschool package to Testappcenter
univention-appcenter-control upload --upload-packages-although-published '5.0/ucsschool=5.0 v4' $(find /var/univention/buildsystem2/apt/ucs_5.0-0-ucs-school-5.0/ -name 'ucs-test-ucsschool*.deb')
```

## Create new changelog
The following code should be executed on your machine to create the XML from advisories:
    (on your PC) create XML from advisories (YAML files):
```shell
cd ucsschool/doc/errata/staging
create_app_changelog -r <ucs-major-minor> -v <app-version> <yaml-datei> ...
```

For example:
```shell
create_app_changelog -r 5.0 -v "5.0 v4" ucs-school-umc-wizards.yaml ucs-school-radius-802.1x.yaml
```

Update git/ucsschool/doc/changelog/Makefile and add the new changelog XML filename:

```shell
vi ../../changelog/Makefile
```

<pre>
- MAIN := changelog-ucsschool-5.0-de
+ MAIN := changelog-ucsschool-5.0v4-de
</pre>

```shell
git add ../../changelog/changelog-ucsschool-5.0v4-de.xml ../../changelog/Makefile
git commit -m "Bug #${BUGNUMBER}: preliminary changelog"
git push
```

- Create a PDF from the XML with [Release Notes Job](https://jenkins.knut.univention.de:8181/job/UCSschool-4.3/job/ReleaseNotes/)
- upload PDF & HTML to docs.univention.de
    - checkout `git@git.knut.univention.de:univention/docs.univention.de.git`
    - copy content of `doc-common/webframe/` to working copy of `docs.univention.de/`
    - fetch the new PDF and HTML files created by the above jenkins job (ReleaseNotes) and place them in working copy of `docs.univention.de/`
    - commit new index files and new HTML and PDF files
    - push to repo (be aware that another coworker may now push the current repo state to the public web server!)
- generate docs.u.de overview pages:
```shell
git clone git@git.knut.univention.de:documentation/ucs-doc-overview-pages.git
apt install python3-jinja2 python3-yaml python3-pycountry
vi src/content.yaml
python3 src/model.py src/content.yaml .../docs.software-univention.de
git add src/content.yaml
git commit -m 'Bug #xxxxx: Added xxxx'
git push
cd ~/git/docs.software-univention.de
git add release-notes_5.0.html.*
git commit -m 'Bug #xxxxx: Added xxxx'
git push
```

Check the [Doc Pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines) from the automatic
commit from Jenkins and check the [staged documentation](http://univention-repository.knut.univention.de/download/docs/).

If everything is in order run the deploy job to publish the new documentation.

## Publish packages from TestAppCenter

The correct version string, for example `ucsschool_20180112151618` can be found here
https://appcenter-test.software-univention.de/meta-inf/5.0/ucsschool/ by navigating to the last (published) version.

This code should be run **on dimma or omar**:
```shell
cd /mnt/omar/vmwares/mirror/appcenter
./copy_from_appcenter.test.sh 5.0 ucsschool_20180112151618  # copies the given version to public app center on local mirror!
sudo update_mirror.sh -v appcenter  # syncs the local mirror to the public download server!
```

## Update public information

Update [Release Ankündigungen für UCS@school 5.0](https://help.univention.com/t/release-ankundigungen-fur-ucs-school-4-4-stand-12-10-2020/12064)
by adding a new section **above** the existing ones.

Send an internal announcement mail with the following text (**Adapt version and name**):
<pre>
To: app-announcement@univention.de
Subject: App Center: UCS@school aktualisiert

Hello all,

the following app update has just been released:
- UCS@school 5.0 v4

The changelog is available here:
http://docs.software-univention.de/changelog-ucsschool-5.0v4-de.html

Excerpts from the changelog:
- ...
- ...

Greetings,

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
UCS@school 5.0 v4 has been released.

https://docs.software-univention.de/changelog-ucsschool-5.0v4-de.html

If this error occurs again, please clone this bug.
</pre>