<!--
SPDX-FileCopyrightText: 2025-2026 Univention GmbH
SPDX-License-Identifier: AGPL-3.0-only
-->

# UCS@school Architecture View

This directory contains the living architecture documentation for UCS@school. It
uses the Sphinx tool chain and reStructuredText like all other documents in
`doc/`.

The document gives a reviewable architecture view for partners, technical
decision makers, architects, and integrators. It deliberately separates the
UCS/Nubus base platform from the UCS@school extensions.

## Build

Run the make targets from the documentation root directory `doc/`, so that the
Sphinx Docker image provides the tool chain:

* `make livehtml-ucsschool-architecture` for a live preview
* `make html` builds the HTML version of all documents
* `make latexpdf` builds the PDF version of all documents

## Live view

Run the tool `unidoc` in the local directory:

`./unidoc livehtml_de`

and open the URL `http://localhost:8000/` in your browser.

## Diagrams

The diagrams live in `images/` as PlantUML sources. Each source has a rendered
SVG file for HTML output and a rendered PNG file for PDF output. The documents
reference them without a file extension, for example
`.. figure:: /images/arch-layers.*`, so that Sphinx picks the format that fits
the builder.

After you changed a `*.puml` file, render the images again and commit them
together with the source:

```bash
make diagrams
```

The target needs PlantUML and Java. It uses the Smetana layout engine, so
GraphViz isn't required.

## Feedback

Give feedback directly on the affected pages, for example as merge request,
review comment, or issue that refers to a section and a proposed change.
