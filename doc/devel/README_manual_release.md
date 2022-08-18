# Non-automatic Release


## Preparations

The manual release process needs access to some commands. The easiest way is to set up an environment
like this **on dimma**:

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

# Push changes to Test Appcenter

For example, to upload `ucs-school-import ucs-school-umc-internetrules` to UCS@school 5.0 v3:

```
`~/git/jenkins/ucsschool-errata-announce/copy_app_binaries --yes-i-really-want-to-upload-to-published-components -r 5.0 -v "5.0 v3" -u ucs-school-import.yaml ucs-school-umc-internetrules.yaml`
```

- Check if the displayed packages and versions are OK
- You will have to confirm in a funny way.
- If the package version can't be found, rebuilding can help, e.g. `b50-scope ucs-school-5.0 ucs-school-lib`