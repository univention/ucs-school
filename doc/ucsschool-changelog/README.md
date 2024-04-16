# Changelog for UCS@school

<!--
SPDX-FileCopyrightText: 2021-2024 Univention GmbH

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

**NOTE:** If you correct anything, please do so in the advisories, not in the `changelog.rst`.

## Create and translate a changelog

This document uses Sphinx for building the artifacts from the reStructeredText
(reST) documents. To extract the content from the errata YAML files, Sphinx
uses the custom builder [Univention Sphinx
Changelog](https://git.knut.univention.de/univention/documentation/univention_sphinx_changelog).

### Update configuration settings

**NOTE:** If you are doing an errata release, skip this step.

The following example illustrates the procedure on the example for the
UCS@school 5.0 v6 release version.

Update configuration settings in `conf.py`:

* Set `univention_changelog_previous_release` to `"5.0 v5"`.
* Set `release` to `5.0 v6`. It may also have to be adapted in [base-doc.yml](../../.gitlab-ci/base-doc.yml).
* Keep `version` at `5.0`.

If there are still advisories in `published` from the previous app release, remove them with `git rm`.

Add additional update information in the `*.rst` files. It might help to run `make clean` inside the docker container when your are doing a release.

### Build the changelog

**NOTE:** For the commands in this section, be sure to pay attention to whether the command should be run inside or outside the docker container.

1. Change to the root of the `ucsschool` directory and start a docker container.

   ```console
   docker run -ti --rm -v "$PWD:/project" -w /project --network=host -u $UID docker-registry.knut.univention.de/knut/sphinx-base:latest /bin/bash
   ```

2. **Inside** the docker container, extract the changes from the errata YAML files to create a reST changelog. Run:

   ```console
   cd doc/ucsschool-changelog
   make changelog
   ```

   To create the changelog content only from a subset of files, use the following command:

   ```console
   cd doc/ucsschool-changelog
   sphinx-build -b changelog . _build/changelog ../errata/published/<file1> ../errata/published/<file-filter>
   ```

   For example: `sphinx-build -b changelog . _build/changelog ../errata/published/2022-08*`

3. **Outside** of docker, review the content of `_build/changelog/changelog.rst` and add reST semantics to the advisories where it is sensible. Check the style with the
   [Univention Documentation
   Styleguide](https://univention.gitpages.knut.univention.de/documentation/styleguide/).
   Remember to only change the advisories, not the `changelog.rst`, and then rerun step 2 after making changes.

4. **Inside** docker, run the spell checker for the English changelog. From the `doc/ucsschool-changelog` directory, run:

   ```console
   make -C . -e SPHINXOPTS="-W --keep-going -D language='en'" -e BUILDDIR="_build/en" spelling
   ```

   Remember to only change the advisories, not the `changelog.rst`.
   If you run into any words that you know are correct, and you want to ignore them in the spellcheck, update `doc/ucsschool-changelog/spelling_wordlist` to include those words.

5. **Outside** of docker, use your text editor of choice to copy over just the changelog entry for the release date, from `doc/ucsschool-changelog/_build/changelog/changelog.rst` to `doc/ucsschool-changelog/changelog.rst`.

   **NOTE:** The automatic generation of the changelog can modify past entries of the changelog, so it is not safe to copy over the generated changelog file directly.

6. **Inside** of docker, generate the `.po` translation files for German. From `doc/ucsschool-changelog` run:

   ```console
   make gettext
   sphinx-intl update -p _build/gettext/ -l "de"
   ```

7. **Outside** of docker, edit the `locales/de/LC_MESSAGES/changelog.po` file.
   Add a German translation for each string, and remove any comments with `fuzzy` when you have manually confirmed that the package name and version are correct. You can use [Deepl](https://www.deepl.com) if you are a non-native speaker.

   For more information, see the  [Translate Sphinx
   documents](https://hutten.knut.univention.de/mediawiki/index.php/Translate_Sphinx_documents#Translation).

8. **Inside** of docker, run the spell checker for the German changelog. From `doc/ucsschool-changelog`, run:

   ```console
   make -C . -e SPHINXOPTS="-W --keep-going -D language='de'" -e BUILDDIR="_build/de" spelling
   ```

   If the spell check fails, aside from actual spelling errors, you might also still have `fuzzy` or empty strings in the `.po` files.

9. Still **inside** of docker, build the `.mo` files.

   ```console
   make -C . -e SPHINXOPTS="-D language='de'" -e BUILDDIR="./_build/de" livehtml
   ```

   Proofread the changes in [your browser](http://127.0.0.1:8000).

10. **Outside** of docker, after everything looks good, commit the changelog and translations to git.

### Build the documentation

1. Follow the `ucsschool` CI/CD pipeline for the changelog and translations until it pauses at the `doc-pipeline`.
2. Manually approve the `doc-pipeline`, then follow the downstream pipeline until it gets to `docs-merge-to-one-artifact`.
3. Manually approve `docs-merge-to-one-artifact`, then follow the `docs.univention.de` pipeline.

Once all pipelines are complete, you should visit the changelog pages and verify that the changes are there:

* [English changelog](https://docs.software-univention.de/ucsschool-changelog/5.0v5/en/changelog.html)
* [German changelog](https://docs.software-univention.de/ucsschool-changelog/5.0v5/de/changelog.html)
