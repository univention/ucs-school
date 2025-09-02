# UCS@school release issue

## Accounting

- Univention GmbH (424)
- Development: UCS@school Development (22605)

## Context/description

UCS@school {{ version }} has to be released...

## Packages to be released

{{ packages }}

## Acceptance criteria

- [ ] Pre-Release Preparation
  - [ ] Check the minimum required UCS errata version
  - [ ] Prepare a VM for testing
  - [ ] Verify Jenkins tests
- [ ] Tag the commit which should be released with the `release-<version>` tag
- [ ] Publish Application with the `do_release` job in the tag pipeline
- [ ] Publish documentation with the `docs-merge-to-one-artifact` job
- [ ] Update other public information
  - [ ] Update/Close bugzilla bugs
  - [ ] Create new target milestone in bugzilla
  - [ ] Update the maintenance information in the `ucsschool.yaml` in repo [univention/dist/release-dates](https://git.knut.univention.de/univention/dist/release-dates) (For https://docs.software-univention.de/n/en/maintenance/ucsschool.html#maintenance-ucsschool)
  - [ ] Update the [overview pages](https://git.knut.univention.de/univention/documentation/ucs-doc-overview-pages)
  - [ ] Add the new changelog document to `docsearch.config.json` in the [docsearch repository](https://git.knut.univention.de/univention/documentation/docsearch/)
  - [ ] Update the `latest` link in [docs.univention.de](https://git.knut.univention.de/univention/docs.univention.de/-/blob/master/ucsschool-changelog/latest)
- [ ] QA the release

## Guidelines

How an issue is finished is defined in the [Definition of done](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/dod.html). Always adhere to our [general review guidelines](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/review.html) and the [UCS@school specific guidelines](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/review.html#qa-of-ucs-school-bugs).

/label ~"Team::UCS@school"
/label ~"Status::Ready"
/label ~Release
