#!/usr/bin/make -f

# SPDX-FileCopyrightText: 2021-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

PACKAGE := ucs-school-veyon-windows
SOURCE := veyon-4.9.1.0-win64-setup.exe
TARGET := veyon-4.9.1.0-win64-setup.exe

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
	echo "4684f045d5c6fdd8c1b2551932d73320ea2d28351b8d5625f7d1ec824796f682035492c3e1f7d6531b6cb81b2e9057dcbf473d0f8a80657ecd03dc31f62e47cb $@" | sha512sum -c

clean:
	rm -f veyon-*-win64-setup.exe
