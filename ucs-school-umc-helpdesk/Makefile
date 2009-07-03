#!/usr/bin/make -f
#
# UCS@School
#
# Copyright (C) 2008-2009 Univention GmbH
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
ADMIN_MODULES=$(shell find modules/univention/admin -name '*.py')
MO_FILES_ADMIN=$(shell find modules/univention/admin -name '*.po' | sed 's/\.po/\.mo/g')
MODULES=$(shell find modules/univention/management -name '*.py')
MO_FILES_BACKEND=$(shell find modules/univention/management -name '*.po' | sed 's/\.po/\.mo/g')
IMAGES=$(shell find images -name '*.gif' -o -name '*.png')

MODULENAME=$(PACKAGE:ucs-school-umc-%=%)

%.mo:	%.po
	msgfmt -o $@ $<

all:	$(ADMIN_MODULES) $(MO_FILES_ADMIN) $(MODULES) $(MO_FILES_BACKEND) 

modules: $(MODULES)

admin-modules: $(ADMIN_MODULES)

install-admin-modules: admin-modules
	install -d debian/$(PACKAGE)/usr/share/pycentral/$(PACKAGE)/site-packages
	@for i in $(ADMIN_MODULES); do\
		o=debian/$(PACKAGE)/usr/share/pycentral/$(PACKAGE)/site-packages/$${i#modules};\
		install -d "`dirname $$o`";\
		install -m644 $$i $$o;\
	done

install-locales-admin: $(MO_FILES_ADMIN)
	@for i in $(MO_FILES_ADMIN); do\
		domain=`dirname $$i | sed 's,^modules/,,;s,/,-,g'`-$(MODULENAME);\
		o=debian/$(PACKAGE)/usr/share/locale/$(LANGUAGE)/LC_MESSAGES/$$domain.mo;\
		install -d "`dirname $$o`";\
		install -m 644 $$i $$o;\
	done

clean:
	@find modules/ -name '*.mo' -exec rm \{\} \;

install-modules: modules
	install -d debian/$(PACKAGE)/usr/share/pycentral/$(PACKAGE)/site-packages
	@for i in $(MODULES); do\
		o=debian/$(PACKAGE)/usr/share/pycentral/$(PACKAGE)/site-packages/$${i#modules};\
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
