# Non-automatic Release

## Preparations

The manual release process needs access to some commands. The easiest way is to set up an environment like this on ``omar``:

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

## Push changes to Test Appcenter

**NOTE:** The following commands should be run on `dimma`.

For example, to upload `ucs-school-import ucs-school-umc-internetrules` and `ucs-school-import` to UCS@school 5.0 v3:

```
cd ~/git/ucsschool/doc/errata/staging
copy_app_binaries --yes-i-really-want-to-upload-to-published-components -r 5.0 -v "5.0 v3" -u \
    ucs-school-import.yaml \
    ucs-school-umc-internetrules.yaml
```

- Check if the displayed packages and versions are OK
  - Copy the list of displayed packages, so you can use it for confirming the versions later in production.
- You will have to confirm in a funny way, by entering the numbers **backward**.
- If the package version can't be found, rebuilding can help, e.g. `b50-scope ucs-school-5.0 ucs-school-lib`
