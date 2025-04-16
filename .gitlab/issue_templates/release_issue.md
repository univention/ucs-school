# UCS@school release issue

## Accounting

- Univention GmbH (424)
- Development: UCS@school Development (22605)

## Context/description

UCS@school {{ version }} has to be released...

## Packages to be released

{{ packages }}

## Acceptance criteria

- [ ] Prepare a VM for testing
- [ ] Check packages for readiness
  - [ ] Create release issue (if not created)
  - [ ] Create Bugzilla bug
  - [ ] Verify Jenkins tests
  - [ ] Verify YAML advisories
  - [ ] Tag an appropriate commit with the `release-<version>` tag
- [ ] Create new changelog
- [ ] Create new version in Test Appcenter
  - [ ] Adjust the version in the README files in the test appcenter
- [ ] Publish to Test Appcenter
- [ ] Verify release in Selfservice Center
- [ ] Publish to production Appcenter
- [ ] Publish manual
- [ ] Update public documentation
  - [ ] Update bugzilla bugs
- [ ] QA the release
- [ ] Create new target milestone in bugzilla
- [ ] Create next errata release issue
- [ ] Update README release documentation (both full and errata) so that bash commands and html links point to the correct versions of UCS@school.
- [ ] Check if the maintenance information has to be updated (https://docs.software-univention.de/n/en/maintenance/ucsschool.html#maintenance-ucsschool)
  - [ ] Create a new link on the UCS changelog pages
  - See READMEs on https://git.knut.univention.de/univention/dist/release-dates and https://git.knut.univention.de/univention/documentation/ucs-doc-overview-pages
  - [ ] If a new document has been added, add it to `docsearch.config.json` in repository https://git.knut.univention.de/univention/documentation/docsearch/
- [ ] Send announcement email

## Guidelines

How an issue is finished is defined in the [Definition of done](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/dod.html). Always adhere to our [general review guidelines](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/review.html) and the [UCS@school specific guidelines](https://univention.gitpages.knut.univention.de/internal/dev-handbook/dev-workflow/review.html#qa-of-ucs-school-bugs).

/label ~"Team::UCS@school"
/label ~"Status::Ready"
/label ~Release
