# Update the Veyon exe

1. Log into a build system, e.g. with:

        ssh omar

2. Change into the directory `/var/univention/buildsystem2/mirror/ftp/download/large-build-files/ucsschool` and download the veyon executable (here the `4.7.3` version):

        cd /var/univention/buildsystem2/mirror/ftp/download/large-build-files/ucsschool
        wget https://github.com/veyon/veyon/releases/download/v4.7.3/veyon-4.7.3.0-win64-setup.exe
        sha512sum veyon-4.7.3.0-win64-setup.exe > veyon-4.7.3.0-win64-setup.SHA512

3. Test the mirror update in a dry-run mode:

        sudo update_mirror.sh -d download/large-build-files/ucsschool

4. If everything is alright, update the mirror without the `-d` (dry-run) flag:

        sudo update_mirror.sh download/large-build-files/ucsschool
