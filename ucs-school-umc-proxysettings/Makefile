#!/usr/bin/make -f
#
# UCS@School
#  UMC module for file distribution
#
# Copyright (C) 2008-2010 Univention GmbH
#
# http://www.univention.de/
# 
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Binary versions of this file provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

DESTDIR=debian/tmp/
MODULES=$(shell find modules/univention -name '*.py')
MO_FILES_BACKEND=$(shell find modules/univention -name '*.po' | sed 's/\.po/\.mo/g')
IMAGES=$(shell find images -name '*.gif' -o -name '*.png')

%.mo:	%.po
	msgfmt -o $@ $<

all:	$(MODULES) $(MO_FILES_BACKEND)

modules: $(MODULES)

clean:
	@find modules/ -name '*.mo' -exec rm \{\} \;

install-modules: modules
	@for i in $(MODULES); do\
		o=debian/$(PACKAGE)/usr/share/pyshared/$${i#modules};\
		install -d "`dirname $$o`";\
		install -m755 $$i $$o;\
	done

install-images:
	@for i in $(IMAGES); do\
		o=debian/$(PACKAGE)/usr/share/univention-management-console/www/themes/$$i;\
		install -d "`dirname $$o`";\
		install -m755 $$i $$o;\
	done

install-locales-backend: $(MO_FILES_BACKEND)
	@for i in $(MO_FILES_BACKEND); do\
		lang=`basename $$i .mo`;\
		domain=`dirname $$i | sed 's,^modules/,,;s,/,-,g'`;\
		o=debian/$(PACKAGE)/usr/share/locale/$$lang/LC_MESSAGES/$$domain.mo;\
		install -d "`dirname $$o`";\
		install -m 644 $$i $$o;\
	done
