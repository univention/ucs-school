
# Writing documentation in the context of the RAM project

---

- status: accepted
- deciders: UCS@school development team
- consulted: UCS@school development team

---

## Context and Problem Statement

As developers, we need a clear way of how and which things we need to document.

## Considered Options

- Deciding on a case by case basis.
- Each issue which yields documentation output connected to administration or the architecture must have a dedicated acceptance criteria to write a section about what is changed and what needs to be done. The very least is a TODO note. The rankine-APIs do not have a separate documentation as we think the swagger ui is sufficient. App center settings must be documented in the administrators' documentation.
 We add a dedicated task with three subtasks to each issue. The assignee then must explicitly state, that no documentation was necessary in each one. E.g. like

 ```text
 - Documentation
  - [ ] Architecture docs: nothing to report.
  - [ ] Administration docs: new UCRV xyz/abc was added to ...
  - [ ] Teacher docs: Search field ___ is now explained in section 3
 ```

## Decision Outcome

Chosen option: "Dedicated acceptance criteria for each required documentation"
