<!--
SPDX-FileCopyrightText: 2025-2026 Univention GmbH
SPDX-License-Identifier: AGPL-3.0-only
-->

# UCS@school package update issue

| Product Value || Reasoning |
|-|-|-|
| User Impact | 0 | + covered by other issues  |
| Product Enablement | 0 | + only release |

## Accounting

- Univention GmbH (424)
- Development: Product Maintenance (14954)

kaze://localhost/14954?desc=UCS%40school+Release

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

/label ~"Team::ByteBenders"

/label ~Release

/status "Planned"
