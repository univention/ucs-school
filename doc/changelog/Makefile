#!/usr/bin/make -f
MAIN := release-notes-ucsschool-4.0r2v1-de release-notes-ucsschool-4.0r2v4-de release-notes-ucsschool-4.0r2v5-de
STYLESHEET := univention_extdocs
OPTIONS += --stringparam ulink.show 0

COMMON_DIR := ../../../doc-common/docbook
include $(COMMON_DIR)/Makefile

OPTIONS += --stringparam front.cover "$(CURDIR)/illustrations/page-background-title-page-ucsschool.jpg"

check:: $(addsuffix .xml,$(MAIN))
	XML_CATALOG_FILES="$(subst $(SPACE),%20,$(XML_CATALOG_FILES))" \
	xsltproc --xinclude "$(COMMON_DIR)/stylesheets/check-bug.xsl" $^
