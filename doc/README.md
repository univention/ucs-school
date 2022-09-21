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

For each new UCS@school errata release, you **must** update the
`CHANGELOG_TARGET_VERSION` in [base-doc.yml](./../.gitlab-ci/base-doc.yml), for
example `5.0v3`. The version string **must not** contain spaces. Keep in mind,
the version string is used for the deployment path of the document.
