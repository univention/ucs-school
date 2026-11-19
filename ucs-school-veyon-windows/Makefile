#!/usr/bin/make -f

# SPDX-FileCopyrightText: 2021-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

PACKAGE := ucs-school-veyon-windows
SOURCE := veyon-4.11.4.0-win64-setup.exe
TARGET := veyon-4.11.4.0-win64-setup.exe

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
	echo "617fcde8a8bce0f71685bdabcd47055faba16884b9939f8e634a17f5615150971f949d4f9d25a021609d25820120640be36a7ee3cefc3908c13f27a9edfbdca1 $@" | sha512sum -c

clean:
	rm -f veyon-*-win64-setup.exe
