# UCS@school package update issue

## Accounting

- Univention GmbH (424)
- Development: UCS@school Development (22605)

## Context/description

UCS@school {{ version }} has to be released...

## Packages to be released

{{ packages }}

## Acceptance criteria

- Pre-Release Preparation
  - [ ] Prepare a VM for testing
  - [ ] Verify you can do an errata release, not a full release
  - [ ] Verify Jenkins tests
- [ ] Update Test Appcenter
- [ ] Publish to production App Center
- [ ] Publish changelog and manual
- [ ] Update public documentation
  - [ ] Send announcement email
  - [ ] Update bugzilla bugs
  - [ ] Make announcement in chat
- [ ] QA the release

## Guidelines

How an issue is finished is defined in the [Definition of done](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/dod.html). Always adhere to our [general review guidelines](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/review.html) and the [UCS@school specific guidelines](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/review.html#qa-of-ucs-school-bugs).

/label ~"Team::UCS@school"
/status "Planned"
/label ~Release
