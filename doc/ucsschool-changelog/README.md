# Changelog for UCS@school

<!--
SPDX-FileCopyrightText: 2021-2024 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

This directory contains the release notes and changelog document for
UCS@school. It's a distinct document that lists all the changes for the
respective version since the last version.

The changelog is manually written as opposed to the past when it was automatically generated from YAML files in the [/doc/errata/published](../errata/published) directory.
The changelog is now independent of the advisories.
During the work on an issue, the implementer uses this guide to update the changelog.

## Create and translate a changelog

This document uses Sphinx for building the artifacts from the reStructeredText
(reST) documents.

### Update configuration settings

**NOTE:** If you are doing an errata release, skip this step.

The following example illustrates the procedure on the example for the
UCS@school 5.0 v6 release version.

Update configuration settings in `doc/ucsschool-changelog/conf.py`:

* Set `univention_changelog_previous_release` to `"5.0 v5"`.
* Set `release` to `5.0 v6`. It may also have to be adapted in [base-doc.yml](../../.gitlab-ci/base-doc.yml).
* Keep `version` at `5.0`.

Add additional update information in the `*.rst` files. It might help to run `make clean` inside the docker container when your are doing a release.

### Editing and building the changelog

The commands in this section are aliases, use `source ./doc/ucsschool-changelog/changelog_commands.sh` to load them.

1. Add the entry for your current issue to the `changelog.rst`.

   **Note: Currently, the new `pre-commit` hooks have some known limitations which will be fixed with https://git.knut.univention.de/univention/ucsschool/-/issues/1262 . Therefore, manual double checking of the existence of changes within the following files is advised:**

   * `<__PACKAGE__>/debian/changelog`
   * `doc/errata/staging/<__PACKAGE__>.yml`
   * `changelog.rst`

2. From the repository root, generate the English livehtml with

   ```console
   livehtml_en
   ```

   You will be able to look at the rendered changes on http://127.0.0.1:8000.
   Tip: Run `clean` before building, if you want to be sure sphinx starts from scratch:

   ```console
   clean
   ```

3. To run the spell checker for the English changelog, enter in the repository root directory:

   ```console
   spelling_en
   ```

   If you run into any words that you know are correct, and you want to ignore them in the spellcheck, update `doc/ucsschool-changelog/spelling_wordlist` to include those words.
   If you think the English changelog is good, move to the translation.

4. Generate the `.po` translation files for German. From the repository root directory, run:

   ```console
   translate
   ```

5. Edit the `locales/de/LC_MESSAGES/changelog.po` file.
   Add a German translation for each string, and remove any comments with `fuzzy` when you have manually confirmed that the package name and version are correct.
   For more information, see the  [Translate Sphinx documents](https://hutten.knut.univention.de/mediawiki/index.php/Translate_Sphinx_documents#Translation).

6. Run the spell checker for the German changelog. From the repository root directory, run:

   ```console
   spelling_de
   ```

   If the spell check fails, aside from actual spelling errors, you might also still have `fuzzy` or empty strings in the `.po` files.

7. You can render the German changelog with the following command:

   ```console
   livehtml_de
   ```

   Proofread the changes in [your browser](http://127.0.0.1:8000).
   If you change something in the English changelog, you will have to do these steps again.

8. When everything looks good, commit the changelog and translations to git.

### Publish the documentation

This section is only needed during a Release.
The pipeline runs on an MR automatically and will tell you if something is wrong.

1. Follow the `ucsschool` CI/CD pipeline for the changelog and translations until it pauses at the `doc-pipeline`.
2. Manually approve the `doc-pipeline`, then follow the downstream pipeline until it gets to `docs-merge-to-one-artifact`.
3. Manually approve `docs-merge-to-one-artifact`, then follow the `docs.univention.de` pipeline.

Once all pipelines are complete, you should visit the changelog pages and verify that the changes are there:

* [English changelog](https://docs.software-univention.de/ucsschool-changelog/5.0v5/en/changelog.html)
* [German changelog](https://docs.software-univention.de/ucsschool-changelog/5.0v5/de/changelog.html)
