
# Workflow for splitting up issues

---

- status: accepted
- date: 2022-08-24
- deciders: UCS@school
- consulted: UCS@school

---

## Context and Problem Statement

Sometimes fulfilling the acceptance criteria of an issue requires work, that
was not anticipated during the estimation meeting. For those cases, where the
amount of unexpected work is significant, we want to define what should be done
about it.

## Decision Drivers

- We want to keep track of our work and make visible what each team member is
  working on.
- We want to improve our efficiency resolving issues.
- We want to keep improving at making effort estimations.

## Considered Options

- **An issue cannot be split**.
  Whatever is needed to fulfill its acceptance
  criteria must be done in order to close the issue, even if it takes more
  effort than planned.
- **An issue can be split in some cases**.
  If in order to fulfill the acceptance criteria of the issue an unconsidered
  effort needs to be done and it can be implemented and QA'd independently, a
  new issue should be created.

## Decision Outcome

Chosen option: "An issue can be split in some cases.", because of the
advantages listed below.

### Positive Consequences

- Smaller issues.
- Easier work parallelization.
- More accurate effort tracking.
- Reduced developer “pain”/“frustration” when an issue explodes (is way larger
  in effort than expected).

### Negative Consequences

- Overhead of creating more issues.

### Workflow for the selected option

1. According to a developer, an issue requires some unplanned work in order to
   fulfill its acceptance criteria and that work can happen independently from
   the original issue.
1. The developer creates a new issue for that work and marks the original issue
   as blocked by it.
1. The developer informs the team in the team chat group or during the next
   daily.

   - If there are any vetos, the new task is removed and the work it
     represented is done as part of the original task.
   - If there aren't, the PO decides if the new task should be refined.
