## Accounting

- Univention GmbH (424)
- Development: UCS@school Development (22605)

## Story

As a \<role\><br/>
I can \<capability\>,<br/>
so that \<receive benefit\>.

## Context/description

A little context to the issue. Where does the task come from, what is needed for implementation. Everything which is important but doesn't fit the user story syntax can be written down here.

A user story should be self-contained and provide value when shipped. It should also contain a "single source of truth".

Additional points:

- If possible, list implementation constraints here (e.g. after a refinement)
- Separation to other user stories
- Desired artifacts (package, documentation, release, etc.)
- Specific requirements regarding documentation if required
- For UI-heavy stories: Mockups, wireframes, storyboards, etc.

## Acceptance criteria & steps for reproduction

- [ ]
- [ ]

- [ ] All changed lines are covered by a unit test, if possible.
  - [ ] Happy case.
  - [ ] Unhappy case (errors and edge cases).
- [ ] There is at least one end-to-end test that covers the changed lines.
- [ ] Evaluate performance of the change.
  - [ ] Read the parent epic and verify performance requirements.
  - [ ] If necessary, performance tests exist. See [Performance commitment](https://git.knut.univention.de/univention/internal/decision-records/-/blob/main/ucsschool/0008-performance-commitment.md)
  - [ ] If there are no specific performance requirements, improve or at least avoid worsening existing performance, if possible.
  - [ ] Document reasons for worse performance in the code and on the ticket, if applicable.

If the changes affect security features such as authentication or authorization:

- [ ] The affected security feature has a dedicated end to end integration test.

## QA

Please explicitly check off all steps performed in the QA process.
If a step does not apply, please apply ~strikethrough~ and note why the step was not performed.

## Technical QA

Technical QA is focused on the code code quality and basic runnability of the code.
All Technical QA steps should also be performed by the implementer before handing over to QA.

- [ ] Code review on the merge request:
  - [ ] Changelog and advisory are present.
  - [ ] Tests sufficiently cover the changed lines of code.
- [ ] Pipelines pass.
- [ ] Debian package builds on a test VM error messages. Watch out for suspicious warning messages.
- [ ] Installation succeeds on a test VM.
- [ ] Basic smoke test:
  - [ ] If a service was changed (added, modified) the service is running after the installation and restarting works without problems. If it was removed, it must not be running any more.
  - [ ] The application loads in the UCS portal.
  - [ ] Cron jobs, listeners, etc. actually run.
  - [ ] Permissions are checked for files (e.g., a script must be executable, right ownership of directories and created files in regards of data security).
- [ ] Manual test run:
  - [ ] New tests pass.
  - [ ] No unexpected tracebacks in log files; expected tracebacks are ignored by `01_var_log_tracebacks.py`.

## Functional QA

Functional QA focuses on the user experience (e.g., GUI or command line).

- [ ] Post a QA plan on the gitlab issue of what will be tested:
  - [ ] Include happy path and multiple non-happy path scenarios.
  - [ ] All modules that might be affected are tested in the UI, not just the code that was changed.
  - [ ] Verify that examples in the documentation still work.
  - [ ] Agree on QA plan with implementer.
- [ ] Manually run the QA plan:
  - [ ] Test on multiple server roles (Primary, Backup, Replica), when applicable.
  - [ ] Use multiple browsers and operating systems (e.g. Windows), when applicable.
  - [ ] Check the log files for unexpected warnings or errors.
- [ ] Document all reproduction steps of the QA plan:
  - [ ] What commands were used to test?
  - [ ] What input values were used to test? Why were these values chosen?
  - [ ] Get creative and try to break the implementation

## Before merge

- [ ] Verify again that branch tests and pipelines pass. No merge without passing.

## After Merge

- [ ] Debian package builds without errors. Watch out for suspicious warning messages.
- [ ] Daily Jenkins tests pass after build.
- [ ] Installation succeeds on a test VM.
- [ ] Smoke test installation:
  - [ ] If a service was changed (added, modified) the service is running after the installation and restarting works without problems. If it was removed, it must not be running any more.
  - [ ] The application loads in the UCS portal.
  - [ ] Cron jobs, listeners, etc. actually run.
  - [ ] Test both installation and upgrade (if applicable).
- [ ] Bugzilla is updated and ready for release.
- [ ] Gitlab issue is added to release issue.
