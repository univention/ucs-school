# Changelog for UCS@school

<!--
SPDX-FileCopyrightText: 2021-2023 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

This directory contains the release notes and changelog document for
UCS@school. It's a distinct document that lists all the changes for the
respective version since the last version.

The content for the changelog comes from the errata updates described in the
errata YAML files in the directory
[/doc/errata/published](../errata/published). The changelog associates the
changes in their respective section in the changelog.
When doing a release, move the advisory files for the packages you want to release to `published` and name them e.g.
`2022-11-18-ucs-school-lib.yaml`. The format is important because it is used to create the `changelog.rst`.

If you correct anything, please do so in the advisories, not in the `changelog.rst`

## Create and translate a changelog

This document uses Sphinx for building the artifacts from the reStructeredText
(reST) documents. To extract the content from the errata YAML files, Sphinx
uses the custom builder [Univention Sphinx
Changelog](https://git.knut.univention.de/univention/documentation/univention_sphinx_changelog).

The following example illustrates the procedure in detail on the example for
the UCS@school 5.0 v4 release version. If you are doing an errata release,
do not do step 1.

1. Update configuration settings in `conf.py`:

   * Set `univention_changelog_previous_release` to `"5.0 v3"`.

   * Set `release` to `5.0 v4`.

   * Keep `version` at `5.0`.

2. Execute all commands in the following steps inside the docker container, which can be entered with this:

   ```console
   docker run -ti --rm -v "$PWD:/project" -w /project --network=host -u $UID docker-registry.knut.univention.de/knut/sphinx-base:latest /bin/bash
   ```

3. To extract the changes from the errata YAML files and create a reST document, run in the root of the ucsschool repository:

   ```console
   cd ./doc/ucsschool-changelog
   make changelog
   ```

   To create the changelog content only from a subset of files, use the following command:

   ```console
   sphinx-build -b changelog . _build/changelog ../errata/published/<file1> ../errata/published/<file-filter>
   ```

   For example: `sphinx-build -b changelog . _build/changelog ../errata/published/2022-08*`

   Note: If the automatic generation of the changelog modifies past entries or if you just generate the changelog for a subset of files, please manually modify `changelog.rst` and add the contents from `_build/changelog/changelog.rst` instead of copying it over.

4. Review the content of `_build/changelog/changelog.rst` and add reST semantics to the advisories where it is sensible. Check the style with the
   [Univention Documentation
   Styleguide](https://univention.gitpages.knut.univention.de/documentation/styleguide/).
   Remember to only change the advisories, not the `changelog.rst`.

5. To run the spell checker for the english changelog, run this in the `doc/ucsschool-changelog` directory, in the docker container:

   ```console
   make -C . -e SPHINXOPTS="-W --keep-going -D language='en'" -e BUILDDIR="_build/en" spelling
   ```

6. Replace the `changelog.rst` file with the content from the generated reST
   document at `_build/changelog/changelog.rst`. You might have to add the heading (`Changelog`) again:

   ```console
   cp ./_build/changelog/changelog.rst changelog.rst
   ```

7. Translate the changelog to German. Run the following command in the ucsschool repository root directory:

   ```console
   cd doc/ucsschool-changelog
   make gettext
   sphinx-intl update -p _build/gettext/ -l "de"
   ```

   Now you can adapt the updated `.po` files. For more information, see the  [Translate Sphinx
   documents](https://hutten.knut.univention.de/mediawiki/index.php/Translate_Sphinx_documents#Translation).
   If you want to look at the html output, run the following in the docker container:

   ```console
   export language="de"
   make -C . -e SPHINXOPTS="-D language=$language" -e BUILDDIR="./_build/$language" livehtml
   ```

8. To run the spell checker for the german changelog, run this in the `doc/ucsschool-changelog` directory, in the docker container:

   ```console
   make -C . -e SPHINXOPTS="-W --keep-going -D language='de'" -e BUILDDIR="_build/de" spelling
   ```

9. Commit the changes to the repository and let the CI/CD pipeline build the
   artifacts.

10. Trigger the production step of the pipeline from step 8.

11. Trigger the production step of the `docs.univention.de` pipeline
