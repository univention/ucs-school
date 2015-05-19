#!/usr/bin/make -f
MAIN := release-notes-ucsschool-3.2v2-de release-notes-ucsschool-3.2-de
STYLESHEET := univention_extdocs
OPTIONS += --stringparam ulink.show 0

COMMON_DIR := ../../../doc-common/docbook
include $(COMMON_DIR)/Makefile

OPTIONS += --stringparam front.cover "$(CURDIR)/illustrations/page-background-title-page-ucsschool.jpg"

$(addsuffix .epub,$(MAIN)): %.epub: $(SOURCES)
$(addsuffix .html,$(MAIN)): %.html: $(SOURCES)
$(addsuffix .fo,$(MAIN)): %.fo: $(SOURCES)

check:: $(addsuffix .xml,$(MAIN))
	XML_CATALOG_FILES="$(COMMON_DIR)/catalog.xml" \
	xsltproc --xinclude $(COMMON_DIR)/stylesheets/check-bug.xsl $^
