# Release instructions for a UCS@school App Release

This document describes how to prepare and execute a full Release for the UCS@school App.


## Preparations
The manual release process needs access to some commands. The easiest way is to set up an environment
like this on **dimma**:
```shell
cd git  # Or whatever folder you want to use for your repositories
git clone --depth 1 git@git.knut.univention.de:univention/ucsschool.git
git clone --depth 1 git@git.knut.univention.de:univention/jenkins.git
ln -s ~/git/jenkins/ucsschool-errata-announce/univention-appcenter-control ~/bin  # Or whatever other folder you have in your $PATH
ln -s ~/git/jenkins/ucsschool-errata-announce/copy_app_binaries ~/bin
echo $USER > ~/.univention-appcenter-user
vi ~/.univention-appcenter-pwd  # Save your appcenter account password here
chmod 400 ~/.univention-appcenter-user ~/.univention-appcenter-pwd
```

Check that it works properly:
```shell
univention-appcenter-control status ucsschool  # no username & password should be asked here
```

Every time you want to do another release make sure that the local repositories are up to date!
```shell
for DIR in ~/git/*; do (cd $DIR; git pull); done
```

Last step for preparations is to create a Bug for the release commits.

## Check packages for readiness

- Collect the YAML files for all packages that are to be released in the new app version.
- Check errata texts for mistakes and unclear content. Correct if need be.
- Run [Errata Checks](https://jenkins.knut.univention.de:8181/job/Mitarbeiter/job/schwardt/job/UCSschool%20CheckErrataForRelease)
  to verify that all selected packages are ready for release.

## Create new version in Test AppCenter and push new packages

```shell
univention-appcenter-control new-version "4.4/ucsschool=4.4 v8" "4.4/ucsschool=4.4 v9"
univention-appcenter-control status ucsschool  # Determine component_id for next step
appcenter-modify-README -a ucsschool -r 4.4 -v "4.4 v9"
# copy_app_binaries -r <ucs-major-minor> -v <app-version> --upload <yaml-datei> ...
# For example:
copy_app_binaries -r 4.4 -v "4.2 v9" -u ucs-school-radius-802.1x.yaml ucs-school-umc-wizards.yaml
# Upload current ucs-test-ucsschool package to Testappcenter 
univention-appcenter-control upload --upload-packages-although-published '4.4/ucsschool=4.4 v9' $(find /var/univention/buildsystem2/apt/ucs_4.4-0-ucs-school-4.4/ -name 'ucs-test-ucsschool*.deb')
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
create_app_changelog -r 4.4 -v "4.4 v2" ucs-school-umc-wizards.yaml ucs-school-radius-802.1x.yaml
```

Update git/ucsschool/doc/changelog/Makefile and add the new changelog XML filename:

```shell
vi ../../changelog/Makefile
```

<pre>
- MAIN := changelog-ucsschool-4.4-de
+ MAIN := changelog-ucsschool-4.4v2-de
</pre>

```shell
git add ../../changelog/changelog-ucsschool-4.4v2-de.xml ../../changelog/Makefile
git commit -m "Bug #${BUGNUMBER}: preliminary changelog"
git push
```

- Create a PDF from the XML with [Release Notes Job](https://jenkins.knut.univention.de:8181/job/UCSschool-4.3/job/ReleaseNotes/)
- upload PDF & HTML to docs.univention.de
    - checkout git@git.knut.univention.de:univention/docs.univention.de.git
    - copy content of doc-common/foobar/ to working copy of docs.univention.de/
    - fetch new PDF and HTML files created by above jenkins job (ReleaseNotes) and place them in working copy of docs.univention.de/
    - commit new index files and new HTML and PDF files
    - push to repo (be aware that another coworker may now push the current repo state to the public web server!)
- generate docs.u.de overview pages:
```shell
git clone git@git.knut.univention.de:documentation/ucs-doc-overview-pages.git
su -c "apt-get install python3-jinja2 python3-yaml python3-pycountry"
vi src/content.yaml
python3 src/model.py src/content.yaml .../docs.software-univention.de
git add src/content.yaml
git commit -m 'Bug #xxxxx: Added xxxx'
git push
cd ~/git/docs.software-univention.de
git add release-notes_4.4.html.*
git commit -m 'Bug #xxxxx: Added xxxx'
git push
```

Run [Publish Docs job](https://jenkins.knut.univention.de:8181/view/Publish/job/Publish_docs.univention.de/).
**Attention: This job needs manual intervention in two instances!**

## Publish packages from TestAppCenter

This code should be run on **dimma**:
```shell
cd /mnt/omar/vmwares/mirror/appcenter
./copy_from_appcenter.test.sh 4.4  # copies current state of test app center to dimma and lists all available app center repositories
./copy_from_appcenter.test.sh 4.4 ucsschool_20180112151618  # copies the given version to public app center on local mirror!
sudo update_mirror.sh -v appcenter  # syncs the local mirror to the public download server!
```

## Update public information

Update [Release Ankündigungen für UCS@school 4.4](https://help.univention.com/t/release-ankundigungen-fur-ucs-school-4-4-stand-12-10-2020/12064)
by adding a new section **above** the existing ones.

Send an internal announcement mail with the following text (**Adapt version and name**):
<pre>
To: app-announcement@univention.de
Subject: App Center: UCS@school aktualisiert
 
Hallo zusammen,
 
folgendes App-Update wurde eben freigegeben:
- UCS@school 4.4 v9
 
Das Changelog ist hier abrufbar:
http://docs.software-univention.de/changelog-ucsschool-4.4v9-de.html
 
Viele Grüße,
 
 $NAME
</pre>

Set all Bugs published with this release to *CLOSED*. You can get all relevant bug numbers with this snippet:
```shell
cd doc/errata/published/
grep bug: 2019-04-11-*.yaml | cut -d: -f2- | tr -d 'bug: []' | tr ',' '\n' | sort -u | tr '\n' ',' ; echo
```

Use this text to as the comment for closing the bug:
<pre>
UCS@school 4.4 v9 has been released.

https://docs.software-univention.de/changelog-ucsschool-4.4v9-de.html

If this error occurs again, please clone this bug.
</pre>