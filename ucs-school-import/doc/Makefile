#!/usr/bin/make -f
# Downloaded from http://plantuml.com/
# Direct download URL http://sourceforge.net/projects/plantuml/files/plantuml.jar/download

FORMATS := png svg
INPUT := import-pyhooks.md

all: $(foreach i,$(INPUT),$(foreach f,$(FORMATS), $(addsuffix .$f,$(basename $i))))

%.png: %.md
	java -jar plantuml.jar -nbthread auto -failfast2 -tpng $<

%.svg: %.md
	java -jar plantuml.jar -nbthread auto -failfast2 -tsvg $<
