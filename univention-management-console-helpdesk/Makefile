DESTDIR=debian/tmp/
ADMIN_MODULES=$(shell find modules/univention/admin -name '*.py')
MO_FILES_ADMIN=$(shell find modules/univention/admin -name '*.po' | sed 's/\.po/\.mo/g')
MODULES=$(shell find modules/univention/management -name '*.py')
MO_FILES_BACKEND=$(shell find modules/univention/management -name '*.po' | sed 's/\.po/\.mo/g')
IMAGES=$(shell find images -name '*.gif' -o -name '*.png')

MODULENAME=$(PACKAGE:univention-management-console-%=%)

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
