# Non-automatic Release Steps

<!--
SPDX-FileCopyrightText: 2022-2026 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

For a UCS@school app release, the intended way is to use the automated release pipeline.
The steps are described in [README_Releases](./README_Releases.md).
If a step described there is not working and manual intervention is necessary, refer to this document.

**NOTE:** If you are a new developer doing the release for the first time, you should also follow the [First Time Preparation](README_manual_release.md#first-time-preparations)
section in the manual release documentation.

## Publish Application

### Create new version in Test AppCenter and publish new packages

The following commands can be run on `omar` to create a new release version:

```shell
univention-appcenter-control new-version "5.2/ucsschool=5.2 v1" "5.2/ucsschool=5.2 v2"
```

Then publish the packages to Test Appcenter:

```shell
# copy_app_binaries -r <ucs-major-minor> -v <app-version> -u <yaml-datei> ...
# For example:
cd ~/git/ucsschool/doc/errata/staging
copy_app_binaries -r 5.2 -v "5.2 v5" -u ucs-school-lib.yaml ucs-school-umc-diagnostic.yaml
```

- Check if the displayed packages and versions are OK
- Copy the list of displayed packages, so you can use it for confirming the versions later in production.
- You will have to confirm in a funny way, by entering the numbers **backward**.
- If the package version can't be found, rebuilding can help, e.g. `b52-scope ucs-school-5.2 ucs-school-lib`,
  though this might mean that this might mean that the package has not been correctly tested

### Verify information in the Selfservice Center

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

### Publish packages to production AppCenter

This code should be run `dimma` or `omar`.
First, determine the `COMPONENT` id for the next step:

```shell
univention-appcenter-control status ucsschool
```

Then publish to the production Appcenter:

```shell
cd /mnt/omar/vmwares/mirror/appcenter
# copy the given version to public app center on local mirror. Use the COMPONENT id.
./copy_from_appcenter.test.sh 5.2 ucsschool_20230804115933
# syncs the local mirror to the public download server
sudo update_mirror.sh -v appcenter
```

## Publish documentation

To publish UCS@school documentation, follow these steps:

1. [Create a new pipeline](https://git.knut.univention.de/univention/dev/education/ucsschool/-/pipelines/new)
2. Set FORCE_DOCS to `yes`.
3. Set `CHANGELOG_TARGET_VERSION` to the target App release version you need, for example `5.2v5`
4. Run the pipeline.
5. Trigger the `docs-merge-to-one-artifact` job manually

Check the [Doc Pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines) from the automatic
commit from Jenkins and check the [staged documentation](http://univention-repository.knut.univention.de/download/docs/).

## Announcement Mail

Send an internal announcement mail with the following text (**Adapt version and name**):

```
To: app-announcement@univention.de
Subject: App Center: UCS@school 5.2 v1 released

Hello all,

the following app update has just been released:
- UCS@school 5.2 v1

The changelog is available here:

- https://docs.software-univention.de/ucsschool-changelog/5.2v1/en/changelog.html
- https://docs.software-univention.de/ucsschool-changelog/5.2v1/de/changelog.html

Excerpts from the changelog:
- ...
- ...

Greetings,

 $NAME
```

## First Time Preparations

**NOTE:** These are instructions for new developers running the release for the first time.
They do not need to be run each time the errata release is done.

### Selfservice Center

You should make sure that you have access to the [Self Service Center](https://selfservice.software-univention.de/univention/management/#module=appcenter-selfservice).
If you are unable to access it, please contact [helpdesk](mailto:helpdesk@univention.de) for access.

### Release Server Environment

The manual release process needs access to some commands.
The easiest way is to set up an environment like this on `omar`, which will also make this available on `ladda` and `dimma` as well:

The instructions expect the following directories in your home directory (but feel free to adapt the instructions if you prefer different directories):

```shell
mkdir git  # where you'll store git repositories
mkdir bin  # where you'll keep symlinks to executables
```

You may also want to update your `PATH` variable:

```shell
echo "export PATH=\$PATH:\$HOME/bin" >> ~/.bashrc
```

Check out the git repositories (may require an `scp` of your gitlab SSH key to `omar`):

```shell
cd git
git clone --depth 1 git@git.knut.univention.de:univention/ucsschool.git
git clone --depth 1 git@git.knut.univention.de:univention/dist/jenkins.git
```

Create symlinks to the scripts:

```shell
ln -s ~/git/jenkins/ucsschool-errata-announce/univention-appcenter-control ~/bin/
ln -s ~/git/jenkins/ucsschool-errata-announce/copy_app_binaries ~/bin/
```

Set up credentials to be used with the two symlinked scripts:

```shell
echo $USER > ~/.univention-appcenter-user
vi ~/.univention-appcenter-pwd  # Save your appcenter account password here
chmod 400 ~/.univention-appcenter-user ~/.univention-appcenter-pwd
```

Check that it works properly:
```shell
univention-appcenter-control status ucsschool  # no username & password should be asked here
```

**NOTE:** If you get the following warning, it means you need to update `~/git/jenkins/ucsschool-errata-announce/univention-appcenter-control` to the latest version from the [provider portal](https://provider-portal.software-univention.de/appcenter-selfservice/univention-appcenter-control):

> The Self Service has been updated (LEVEL=5). Please update your script (LEVEL=4)

Every time you want to do another release make sure that the local repositories are up to date!

```shell
for DIR in ~/git/*; do (cd $DIR; git pull); done
```

