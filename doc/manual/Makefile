#!/usr/bin/make -f
MAIN := ucsschool-handbuch-3.1R2 ucsschool-lehrer-handbuch-3.1R2

STYLESHEETS_DIR := /usr/share/xml/docbook/stylesheet

SOURCES := $(shell find . ../stylesheets -name \*.xml -o -name \*.ent -o -name \*.xsl)
IMAGES := $(shell find . ../stylesheets -name \*.png -o -name \*.jpg)

.PHONY: all
all: html pdf export

.PHONY: epub
epub: $(addsuffix .epub,$(MAIN))
%.epub: %.xml $(SOURCES) $(IMAGES)
	dbtoepub $< -o $@

.PHONY: html
html: $(addsuffix .html,$(MAIN))
%.html: %.xml $(SOURCES)
	xsltproc \
		--stringparam collect.xref.targets yes \
		--stringparam targets.filename $*.db.tmp \
		--stringparam current.docid $* \
		-o $@ $(OPTIONS) ../stylesheets/ucsschool_html.xsl $<
	if ! diff $@.db $*.db.tmp >/dev/null 2>&1; then mv $*.db.tmp $@.db; else $(RM) $*.db.tmp; fi

.PHONY: fo
fo: $(addsuffix .fo,$(MAIN))
%.fo: %.xml $(SOURCES)
	xsltproc \
		--stringparam collect.xref.targets yes \
		--stringparam targets.filename $*.db.tmp \
		--stringparam current.docid $* \
		-o $@ $(OPTIONS) ../stylesheets/ucsschool_fo.xsl $<
	if ! diff $@.db $*.db.tmp >/dev/null 2>&1; then mv $*.db.tmp $@.db; else $(RM) $*.db.tmp; fi

.PHONY: pdf
pdf: $(addsuffix .pdf,$(MAIN))
%.pdf: %.fo $(IMAGES)
	fop -pdf $@ -fo $<

.PHONY: export
export: pdf html
	install -m755 -d ../webroot
	install -m755 -d ../webroot/illustrations
	install -m644 -t ../webroot/illustrations illustrations/*.png illustrations/*.svg
#	install -m644 -t ../webroot/illustrations illustrations/*.jpg
	install -m644 -t ../webroot *.pdf
	install -m644 -t ../webroot *.html
	cp -d symlinks/* ../webroot

.PHONY: clean
clean:
	$(RM) $(addsuffix .epub,$(MAIN))
	$(RM) $(addsuffix .html,$(MAIN))
	$(RM) $(addsuffix .fo,$(MAIN))
	$(RM) $(addsuffix .pdf,$(MAIN))
	$(RM) $(patsubst %,../webroot/%.html,$(MAIN))
	$(RM) *.db

.PHONY: check
check: $(addsuffix .xml,$(MAIN))
	xmllint --noout --valid $^
