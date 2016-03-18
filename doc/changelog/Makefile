#!/usr/bin/make -f
MAIN := changelog-ucsschool-4.1v5-de
STYLESHEET := univention_extdocs
OPTIONS += --stringparam ulink.show 0

COMMON_DIR := ../../../doc-common/docbook
include $(COMMON_DIR)/Makefile

OPTIONS += --stringparam front.cover "$(CURDIR)/page-background-title-page-ucsschool.jpg"

check:: $(addsuffix .xml,$(MAIN))
	XML_CATALOG_FILES="$(subst $(SPACE),%20,$(XML_CATALOG_FILES))" \
	xsltproc --xinclude "$(COMMON_DIR)/stylesheets/check-bug.xsl" $^
