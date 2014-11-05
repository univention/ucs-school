#!/usr/bin/make -f
#
# UCS@School
#
# Copyright 2008-2014 Univention GmbH
#
# http://www.univention.de/
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
# <http://www.gnu.org/licenses/>.

DESTDIR=debian/tmp/
ADMIN_MODULES=$(shell find modules/univention/admin -name '*.py')
MO_FILES_ADMIN=$(shell find modules/univention/admin -name '*.po' | sed 's/\.po/\.mo/g')

MODULENAME=$(PACKAGE:ucs-school-umc-%=%)

%.mo:	%.po
	msgfmt -o $@ $<

all:	$(ADMIN_MODULES) $(MO_FILES_ADMIN) 

admin-modules: $(ADMIN_MODULES)

install-admin-modules: admin-modules
	@for i in $(ADMIN_MODULES); do\
		o=debian/$(PACKAGE)/usr/share/pyshared/$${i#modules};\
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
