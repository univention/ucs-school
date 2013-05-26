#!/usr/bin/make -f
MAIN := ucsschool-handbuch-3.1R2 ucsschool-lehrer-handbuch-3.1R2
STYLESHEET := ucsschool

COMMON_DIR := ../../../doc-common/docbook
include $(COMMON_DIR)/Makefile

OPTIONS += --stringparam front.cover "$(CURDIR)/page-background-title-page.jpg"

$(addsuffix .epub,$(MAIN)): %.epub: $(SOURCES)
$(addsuffix .html,$(MAIN)): %.html: $(SOURCES)
$(addsuffix .fo,$(MAIN)): %.fo: $(SOURCES)
