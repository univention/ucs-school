DESTDIR=debian/tmp/
RELPATH_SRC=modules/UMC
MODULES=$(shell find $(RELPATH_SRC) -name '*.py')
MO_FILES_BACKEND=$(shell find $(RELPATH_SRC) -name '*.po' | sed 's/\.po/\.mo/g')
IMAGES=$(shell find images -name '*.gif' -o -name '*.png')

MODULENAME=$(PACKAGE:univention-management-console-%=%)
RELPATH_UMC=univention/management/console/handlers/$(MODULENAME)

%.mo:	%.po
	msgfmt -o $@ $<

all:	$(MODULES) $(MO_FILES_BACKEND)

modules: $(MODULES)

clean:
	@find modules/ -name '*.mo' -exec rm \{\} \;

install-modules: modules
	install -d debian/$(PACKAGE)/usr/share/pycentral/$(PACKAGE)/site-packages
	@for i in $(MODULES); do\
		relpath=$$(echo $$i | sed -e "s|$(RELPATH_SRC)|$(RELPATH_UMC)|"); \
		o=debian/$(PACKAGE)/usr/share/pycentral/$(PACKAGE)/site-packages/$${relpath}; \
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
		domain=`echo $(RELPATH_UMC) | sed 's,/,-,g'`;\
		o=debian/$(PACKAGE)/usr/share/locale/$$lang/LC_MESSAGES/$$domain.mo;\
		install -d "`dirname $$o`";\
		install -m 644 $$i $$o;\
	done
