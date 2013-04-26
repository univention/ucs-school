#!/bin/bash
#
#
# ### SETTINGS ##############################
#

REPOUSER=""
REPODIR="/root/mingw-repo"
BUILDDIR="/root/src/italc"
CROSSCOMPILER="192.168.0.10:/var/univention/buildsystem2/contrib/iTALC-mingw/*/*.deb"
SVN_ITALC="svn+ssh://192.168.0.3/var/svn/dev/branches/ucs-3.1/ucs-school-r2/italc-windows"
TIMESERVER="192.168.0.3"

#
# ###########################################
#

if [ -z "$1" -a -z "$REPOUSER" ] || [ "$1" = "--help" -o "$1" = "-h" ] ; then
	echo "$(basename "$0") <USERNAME>"
	echo "Please pass an username as first argument for login on server	omar"
	exit 1
fi

[ -z "$REPOUSER" ] && REPOUSER="$1"

#
# prepare local repo
#
if [ ! -d "$REPODIR" ] ; then
	mkdir -p "$REPODIR"
	scp "${REPOUSER}@${CROSSCOMPILER}" "$REPODIR"
	cd "$REPODIR"
	apt-ftparchive packages . > Packages
	gzip < Packages > Packages.gz
	echo "# repo for cross compiler" >> /etc/apt/sources.list.d/italc-crosscompiler.list
	echo "deb file://${REPODIR}/ ./" >> /etc/apt/sources.list.d/italc-crosscompiler.list
fi

#
# prepare build environment
#
apt-get update
apt-get install -y --force-yes git subversion cmake nsis tofrodos mingw32-x-gcc mingw32-x-qt mingw32-x-zlib mingw32-x-openssl mingw32-x-libjpeg mingw32-x-pthreads mingw64-x-gcc mingw64-x-qt mingw64-x-zlib mingw64-x-openssl mingw64-x-libjpeg  mingw64-x-pthreads gcj-jdk make

#
# get source
#
rm -Rf "$BUILDDIR"
mkdir -p "$(dirname "$BUILDDIR")"
svn checkout --username "$REPOUSER" "${SVN_ITALC}" "$BUILDDIR"

#
# build win32 version
#
cd "$BUILDDIR/italc.git/"
rm -Rf build32
mkdir -p build32
cd build32
../build_mingw32
make win-nsi
cp *.exe ..

#
# build win64 version
#
cd "$BUILDDIR/italc.git/"
rm -Rf build64
mkdir -p build64
cd build64
../build_mingw64
make win-nsi
cp *.exe ..
