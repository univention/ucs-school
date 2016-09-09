ADDITIONAL = $(DESTDIR)/usr/share/locale/fr/LC_MESSAGES/python-ucs-school.mo \
	$(DESTDIR)/usr/share/locale/fr/LC_MESSAGES/univention-admin-handlers-settings-helpdesk.mo

$(DESTDIR)/usr/share/locale/fr/LC_MESSAGES/python-ucs-school.mo: fr/ucs-school-lib/python/fr.po
$(DESTDIR)/usr/share/locale/fr/LC_MESSAGES/univention-admin-handlers-settings-helpdesk.mo: fr/ucs-school-umc-helpdesk/modules/univention/admin/handlers/settings/fr.po
