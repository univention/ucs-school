<!--
SPDX-FileCopyrightText: 2025 Univention GmbH
SPDX-License-Identifier: AGPL-3.0-only
-->

# UCS@school documentation

The UCS@school documentation uses the Sphinx tool chain and the reStructedText
lightweight markup.

## Versioning

All documents, except the changelog, use the major and minor version numbers
for the deployment path and within the document.

### General documents

You configure the document target version with `DOC_TARGET_VERSION` in
[base-doc.yml](./../.gitlab-ci/base-doc.yml).

You **must** update the `DOC_TARGET_VERSION` upon a new minor release for UCS@school.

### Changelog

The version for the UCS@school changelog goes down to the errata level.

## General Makefile

In the documentation root directory `doc/` there is a Makefile. You can use it
to run the Sphinx make targets over all documentation.

Examples. Run the commands from the UCS repository `/doc` directory.

* Cleanup all build artifacts: `make clean`

* Build all HTML files: `make html`

* Build all PDF files: `make latexpdf`. Build PDF files requires the
  full Sphinx Docker image, which is about twice the size of the Sphinx base
  image.

### livehtml

You can run a livehtml doc website from the documentation root directory `doc/` like this:

`make livehtml-$TARGET_DIR`

For example `make livehtml-ucsschool-manual`
