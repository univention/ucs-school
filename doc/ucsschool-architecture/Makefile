# SPDX-FileCopyrightText: 2025-2026 Univention GmbH
#
# SPDX-License-Identifier: AGPL-3.0-only

# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Diagram sources live in images/*.puml. The Smetana layout engine avoids the
# dependency on GraphViz and keeps the rendered images reproducible.
PLANTUML      ?= plantuml
PLANTUMLOPTS  ?= -Playout=smetana

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

livehtml:
	sphinx-autobuild "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Rebuild the SVG and PNG diagrams from their PlantUML sources. Run this target
# after you changed a file in images/ and commit the rendered images with it.
# The rendered images get a license file each, because PlantUML doesn't keep
# copyright headers in its output.
diagrams:
	$(PLANTUML) $(PLANTUMLOPTS) -tsvg images/*.puml
	$(PLANTUML) $(PLANTUMLOPTS) -tpng images/*.puml
	set -e; for image in images/*.svg images/*.png; do \
		printf 'SPDX-FileCopyrightText: 2025-2026 Univention GmbH\n\nSPDX-License-Identifier: AGPL-3.0-only\n' > "$$image.license"; \
	done

.PHONY: help livehtml diagrams Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
