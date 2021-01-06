#!/usr/bin/make -f

# Copyright 2021 Univention GmbH
#
# https://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <https://www.gnu.org/licenses/>.

PACKAGE := ucs-school-veyon-windows
SOURCE := veyon-4.5.2.0-win64-setup.exe
TARGET := veyon-4.5.2.0-win64-setup.exe

empty :=
space := $(empty) $(empty)
INSTALL ?= install

.PHONY: all
all:

.PHONY: install
install: $(SOURCE)
	$(INSTALL) -m755 -d $(DESTDIR)/usr/share/$(PACKAGE)
	$(INSTALL) -m644 "$<" "$(DESTDIR)/usr/share/$(PACKAGE)/$(subst _,$(space),$(TARGET))"

.PHONY: get-orig-source
get-orig-source: $(SOURCE)
veyon-%-win64-setup.exe:
	wget -O "$@" "https://updates.software-univention.de/download/large-build-files/ucsschool/$@"
	echo "5ac169c8d70da049e532f0a306652c50b892b3ed562f6a18f9f947103fd8f6d5c9748834c8289e79726730653a0be5082c352c972d661e6eaf9515103bd75fa8 $@" | sha512sum -c

clean:
	rm -f veyon-*-win64-setup.exe
