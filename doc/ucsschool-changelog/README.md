# Changelog for UCS@school

This directory contains the release notes and changelog document for
UCS@school. It's a distinct document that lists all the changes for the
respective version since the last version.

The content for the changelog comes from the errata updates described in the
errata YAML files in the directory
[/doc/errata/published](../errata/published). The changelog associates the
changes in their respective section in the changelog.

## Create a changelog

This document uses Sphinx for building the artifacts from the reStructeredText
(reST) documents. To extract the content from the errata YAML files, Sphinx
uses the custom builder [Univention Sphinx
Changelog](https://git.knut.univention.de/univention/documentation/univention_sphinx_changelog).

The following example illustrates the procedure in detail on the example for
the UCS@school 5.0 v4 release version.

1. Update configuration settings in `conf.py`:

   * Set `univention_changelog_previous_release` to `"5.0 v3"`.

   * Set `release` to `5.0 v4`.

   * Keep `version` at `5.0`.

1. Extract the changes from the errata YAML files and create a reST document:
   `make changelog`.

   To create the changelog content only from a subset of files, use the following command:

   ```console
   sphinx-build -b changelog . _build/changelog ../errata/published/<file1> ../errata/published/<file-filter>
   ```

   For example: `sphinx-build -b changelog . _build/changelog ../errata/published/2022-08*`

1. Replace the `changelog.rst` file with the content from the generated reST
   document at `_build/changelog/changelog.rst`.

1. Review the content and add reST semantics to it. Check the style with the
   [Univention Documentation
   Styleguide](https://univention.gitpages.knut.univention.de/documentation/styleguide/).

1. Commit the changes to the repository and let the CI/CD pipeline build the
   artifacts.

## Translate the changelog

For the UCS@school target group we also translate the release notes with
changelog to German. To translate the document, follow the steps outline in
[Translate Sphinx
documents](https://hutten.knut.univention.de/mediawiki/index.php/Translate_Sphinx_documents#Translation).