<!--
SPDX-FileCopyrightText: 2025-2026 Univention GmbH
SPDX-License-Identifier: AGPL-3.0-only
-->

# Developer information

This README contains information for developing withing the `ucsschool` respository.

## Architectural/Any Decision Records (ADR)

ADRs for the UCS@school product are in https://git.knut.univention.de/univention/decision-records/

## Pre-commit

This repository uses pre-commit for formatting, linting and other checks.
Python3.11 is required for the pre-commit hooks.

To install the pre-commit hooks, you can run `pre-commit install`.

A Gitlab pipeline job runs the pre-commit hooks and prevents merging MRs, where any pre-commit hook fails.

## Releasing UCS@school

Releasing UCS@school is documented in the [Release README](doc/devel/README_Releases.md).
