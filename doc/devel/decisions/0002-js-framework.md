
# JavaScript framework for the UI of the new UCS@school frontend modules

---

- status: accepted
- deciders: Ingo, Marie, Johannes
- consulted: UCS@school team

---

## Context and Problem Statement

- We want to replace the old "Dojo Toolkit" JavaScript UI framework with a modern UI framework.
- In its current version it makes a lot of work to improve accessibility aspects.
- It is also not a very popular amongst frontend developers, which makes current employees unhappy and recruitment difficult.
- The new JS framework will have to implement the architecture decided upon in [ADR 0001 change-ui-architecture](0001-change-ui-architecture.md):
  Instead of communicating with a UMC Python backend, it'll call REST APIs.

## Decision Drivers

- UI framework is very old and must be updated.
- Accessibility requirements.
- Make recruitment of new frontend developers easier, as they will be presented with a modern framework.

## Considered Options

- [Vue](https://vuejs.org/)
- [Dojo Toolkit](https://dojotoolkit.org/)
- [Dojo](https://dojo.io/home) (the rewrite of Dojo Toolkit)

## Decision Outcome

Chosen option: "Vue", because
In the Phoenix project the Univention Portal were to be reimplemented with accessibility in mind.
For that we chose [Vue](https://vuejs.org/) as framework to address the same issues and decision drivers as above.
We had time with rewriting the Portal in Vue to evaluate that decision. There are no major hurdles with working with
Vue, and it is also a popular modern framework which makes requiting easier.

We additionally chose Vue for this project also because we don't want to use multiple frontend frameworks for different
projects which would make development and consistency between the implementations unnecessarily harder.

### Positive Consequences

- Vue is currently popular amongst frontend developers, which will make Univention a desirable employer.
- Vue is already used in the Univention Portal.

### Negative Consequences

- Using Vue instead of Dojo means, that the currently employed developers must learn a new web framework.
- Using Vue instead of Dojo means, that existing widgets etc. cannot be reused, but must be newly created.

## More Information

Links to related decisions and resources:

- [ADR 0001 change-ui-architecture](0001-change-ui-architecture.md)
- [ADR 0003 rest-service-dedicated-to-ui](0003-rest-service-dedicated-to-ui.md)
- [Epic "Widget library for portal modules"](https://git.knut.univention.de/groups/univention/-/epics/262)
- [Epic "Create UI Design for (UCS@school) portal modules"](https://git.knut.univention.de/groups/univention/-/epics/261)
