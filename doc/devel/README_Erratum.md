# Release instructions for a UCS@school Errata Release

This document describes how to prepare and execute an Errata Release for the UCS@school App.

## First Time Preparation

**NOTE:** These are instructions for new developers running the release for the first time.
They do not need to be run each time the errata release is done.

See "Preparation" section in the documentation for [manual release to Test Appcenter](README_manual_release.md) to set up your environment on ``dimma``.
The same preparations will also be available on ``omar`` for later steps.

You should also make sure that you have access to the [Self Service Center](https://selfservice.software-univention.de/univention/management/#module=appcenter-selfservice).
If you are unable to access it, please contact [helpdesk](mailto:helpdesk@univention.de) for access.

## Prepare a VM for testing

If you don't have one already, create a [UCS@school multi-server env](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Environments/job/SchoolMultiserverEnvironment/) to use for testing in the **Verify production apps** section.

## Check packages for readiness

Before starting, ensure that there is an errata release issue. The issue must
include as blocking issues, all updates to `ucsschool` since the last errata
release. Use this errata release issue for all steps in this section.

### Check if packages can be released as an errata

Not every package should be released as an errata but needs to be released within a full [UCS@school App release](README_Releases.md). Consider the [ucs rules](https://univention.gitpages.knut.univention.de/internal/dev-onboarding/guidelines/stability.html#errata-updates) as a guideline to help you decide if a package can be released as an errata.
Basically you should ensure an administrator doesn't need to take manual steps during the update.

For example:
* No join script updates
* No backwards-incompatible API changes

### Verify tests

Check the following Jenkins jobs for any unusual failures that might be connected to the release:

* [Install U@S 5.0 Singleserver](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Daily%20Tests/job/Install%20Singleserver/)
* [Install U@S 5.0 Multiserver](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Daily%20Tests/job/Install%20Multiserver/)

### Verify Gitlab Issues and Bugzilla Bugs

On the gitlab errata release issue, there should be a list of issues blocking the errata release.
Every issue should be in a closed status; if it isn't, it needs to be removed from the current release and put into the next release.

Log into [Bugzilla](https://forge.univention.org/bugzilla/index.cgi), and do a comma-separated search for each of the bugs in the release (e.g. `55986,55751,50841`).
For each bug:

- Status should be "VERIFIED FIXED".
- Should have an assignee + QA person listed.
- Target milestone should be set (e.g., UCS@school 5.0 v3 errata).

### Verify YAML advisories

For each bug in the errata release, you need to verify the YAML advisories in the `ucsschool` repository.
On in your local `ucsschool` repository:

```shell
git checkout main
git pull
cd doc/errata/staging
```

First, make sure that all files are correctly labeled with the `*.yaml` extension and fix anything that is `.yml`.
This ensures that scripts in these docs work as expected:

```shell
find . -name "*.yml" -exec bash -c 'mv "$0" "${0%.yml}.yaml"' {} \;
```

Commit the changes to git.

In order to release a package, you have to verify that:

- The advisory is in the correct format. Use [this script](https://git.knut.univention.de/univention/internal/research-library/-/blob/main/personal/twenzel/scripts/check_yamls.py) to verify mistakes.
- The advisory's description is in clear language, without spelling errors.
- The advisory does not contain other bugs that are not part of the release.
  You can use [this script](https://git.knut.univention.de/univention/internal/research-library/-/blob/main/personal/jleadbetter/scripts/find_advisories) to automatically check which bugs are safe to release, and to find all advisory files you need to include in the release.
  Make a note of the advisory files found for the release.
  You will need them later for
  [pushing changes to Test AppCenter](README_manual_release.md#push-changes-to-test-appcenter)
  and [updating the advisories](#move-the-advisories-to-published).

In your editor of choice, do a manual inspection of each of the advisories, based on the corresponding bugzilla bug:

- Are the advisory messages for each bug in good English, easy to understand, and without spelling errors?
- Is the advisory message in the right file (e.g., sometimes we confuse `ucs-school-import` and `ucs-school-umc-import`)?
- Compare the debian-changelog version and the advisory `fix` version.
- Compare the advisory `fix` version with build details in the gitlab issue.

### Double-check what has changed

You may want to do a rough visual check of which packages have changed, to verify that the advisories found in the previous step match what is expected:

```shell
cd ucsschool
ls -lt  # ordered by time last changed
```

If you see any recent package changes that don't correspond to advisories, you may need to ask about them in `#ucsschool-dev` chat.

## Update Test AppCenter

### General updates

If you are doing the release for `4.4`, execute the following steps on `dimma`.
Otherwise, execute the steps on `omar`.

Follow the instructions for [manual release to Test AppCenter](README_manual_release.md#push-changes-to-test-appcenter).
Keep in mind:

* You will need the list of YAML files you edited in the previous verification steps.
* You should make a note of the packages that get uploaded from the `copy_app_binaries` command.

### ucs-test-ucsschool updates

The `ucs-test-ucsshool` package is unique in that it doesn't include a `.yaml` file and isn't supported by us for the customer.
Additionally, `ucs-test-ucsschool` is not guaranteed to work for the set of packages that are part of the release.
It may contain tests for packages that have been excluded.

**NOTE:** You do not always need to release `ucs-test-ucsschool`.
Please use your discretion based on whether or not it has changed, and whether those changes match all the packages you released in the previous step.

To release `ucs-test-ucsschool`:

```shell
univention-appcenter-control upload --upload-packages-although-published '5.0/ucsschool=5.0 v3' $(find /var/univention/buildsystem2/apt/ucs_5.0-0-ucs-school-5.0/ -name 'ucs-test-ucsschool*.deb')
```

## Publish to production App Center

The following code should be executed on `omar`:

The correct version string, for example `ucsschool_20220727135154`, can be found in the [Test AppCenter](https://appcenter-test.software-univention.de/meta-inf/5.0/ucsschool/) by navigating to the last (published) version.

```shell
cd /mnt/omar/vmwares/mirror/appcenter
./copy_from_appcenter.test.sh 5.0 ucsschool_20220727135154  # copies the given version to public app center on local mirror!
sudo update_mirror.sh -v appcenter  # syncs the local mirror to the public download server!
```

### Verify production apps

Using the UCS@school multi-server env you created during **Prepare a VM for testing**, verify that you can update the Primary Directory Node and Replica Directory Node to the latest production version.

You can run an update on each node with the following command:

```shell
echo univention > /tmp/pass
univention-upgrade --ignoressh --noninteractive --enable-app-updates --username Administrator --pwdfile /tmp/pass
```

Verify that the versions you noted in the **Update TestAppCenter** are now present on each of the servers.

If anything is missing, you can verify it visually in the [production AppCenter](https://appcenter.software-univention.de/meta-inf/5.0/ucsschool/).

## Update Changelog

### Move the advisories to published

You will need the list of YAML files you edited in the **Verify YAML advisories** step.

In your local `ucsschool` repository, move the YAML advisories into the `doc/errata/published` folder, renamed with the current date:

```shell
cd doc/errata/staging
release_files=( "ucs-school-lib.yaml" "ucs-school-umc-users.yaml" )
for file in "${release_files[@]}"; do git mv "$file" "$(echo $file | sed "s/^/..\/published\/$(date +%Y-%m-%d)-/")"; done
```

Commit the changes to git, and `cd` to the root of the `ucsschool` repository.

### Generate the changelog

Open up a second terminal for running docker commands.
Then follow the instructions in the [changelog README](../ucsschool-changelog/README.md).

## Publish manual

The documentation is built in a gitlab pipeline. When it's merged to main the documentation, which
was changed can be published by manually triggering the production job.

Afterwards, check the [Doc Pipeline](https://git.knut.univention.de/univention/docs.univention.de/-/pipelines) from the automatic commit from Jenkins and check the [staged documentation](http://univention-repository.knut.univention.de/download/docs/).

If everything is in order, run the `deploy job` to publish the new documentation.

## Update public information

### Update the release announcement wiki

Update [Release Ankündigungen für UCS@school 5.0](https://help.univention.com/t/release-ankundigungen-fur-ucs-school-5-0-stand-17-11-2022/20184)
by adding a new section below the existing ones.

### Send the release announcement email

Send an internal announcement mail with the following text (**Adapt version and name**):

<pre>
To: app-announcement@univention.de
Subject: App Center: UCS@school updated

Hello everyone,

Errata have just been released for UCS@school 5.0 v3.

The changelog is available here:
https://docs.software-univention.de/ucsschool-changelog/5.0v3/en/changelog.html

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
Errata updates for UCS@school 5.0 v3 have been released.

https://docs.software-univention.de/ucsschool-changelog/5.0v3/de/changelog.html

If this error occurs again, please clone this bug.
</pre>

## QA Errata Release

Do the following checks and document the result in Taiga/Bugzilla/Gitlab:

* OK: all packages have been uploaded to the [public appcenter](http://appcenter.software-univention.de/univention-repository/5.0/maintained/component/ucsschool_20201208103021/)
* OK: using an existing [UCS@school multi-server env](https://jenkins2022.knut.univention.de/view/UCS@school/job/UCSschool-5.0/view/Environments/job/SchoolMultiserverEnvironment/) verify that you can update the Primary Directory Node and the Replica Directory Node successfully.
* OK: all Bugzilla bugs have been closed.
* OK: all yaml files have been renamed (`doc/errata/published/2021-05-26-*`)
* OK: manuals have been updated (e.g. https://docs.software-univention.de/ucsschool-handbuch-5.0.html).
* OK: the [changelog](https://docs.software-univention.de/ucsschool-changelog/5.0v3/en/changelog.html) has been built and uploaded
* OK: [help.univention.com](https://help.univention.com/t/release-ankundigungen-fur-ucs-school-5-0-stand-17-11-2022/20184) text updated.
* OK: internal announcement mail.
* OK: created gitlab issue for the next errata release.

