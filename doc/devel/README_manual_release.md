# Non-automatic Release

<!--
SPDX-FileCopyrightText: 2022-2024 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

**NOTE:** If this is your first time doing a manual release, please jump to the
section on **First Time Preparations** first. Then come back to **Push changes
to Test Appcenter**.

## Push changes to Test Appcenter

**NOTE:** If you are doing the release for `4.4`, execute the following steps on `dimma`.
Otherwise, execute the steps on `ladda`.

Make sure you have the current version of `ucsschool` and release scripts:

```shell
for DIR in ~/git/*; do (cd $DIR; git pull); done
```

Now push the changes to the Test Appcenter.
For example, to upload `ucs-school-import ucs-school-umc-internetrules` and `ucs-school-import` to UCS@school 5.0 v4:

```shell
cd ~/git/ucsschool/doc/errata/staging
copy_app_binaries --yes-i-really-want-to-upload-to-published-components -r 5.0 -v "5.0 v5" -u \
    ucs-school-import.yaml \
    ucs-school-umc-internetrules.yaml
```

- Check if the displayed packages and versions are OK
  - Copy the list of displayed packages, so you can use it for confirming the versions later in production.
- You will have to confirm in a funny way, by entering the numbers **backward**.
- If the package version can't be found, rebuilding can help, e.g. `b50-scope ucs-school-5.0 ucs-school-lib`

### ucs-test-ucsschool updates

The `ucs-test-ucsshool` package is unique in that it doesn't include a `.yaml` file and isn't supported by us for the customer.
Additionally, `ucs-test-ucsschool` is not guaranteed to work for the set of packages that are part of the release.
It may contain tests for packages that have been excluded.

**NOTE:** You do not always need to release `ucs-test-ucsschool`.
You should only release if:

* `ucs-test-ucsschool` has changed, and
* There are no tests for unreleased packages (releasing tests for unreleased packages will cause Jenkins to break).

To release `ucs-test-ucsschool`:

```shell
univention-appcenter-control upload --upload-packages-although-published '5.0/ucsschool=5.0 v4' $(find /var/univention/buildsystem2/apt/ucs_5.0-0-ucs-school-5.0/ -name 'ucs-test-ucsschool*.deb')
```

## First Time Preparations

**NOTE:** These are instructions for new developers running the release for the first time.
They do not need to be run each time the errata release is done.

### Selfservice Center

You should also make sure that you have access to the [Self Service Center](https://selfservice.software-univention.de/univention/management/#module=appcenter-selfservice).
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

