
# JavaScript framework for the UI of the new UCS@school frontend modules

---

- status: accepted
- deciders: Ingo, Marie, Johannes
- consulted: UCS@school team

---

## Context and Problem Statement

- We want to replace the old "Dojo Toolkit" JavaScript UI framework with a modern UI framework.
- In its current version it makes a lot of work to improve accessibility aspects.
- It is also not very popular amongst frontend developers, which makes current employees unhappy and recruitment difficult.
- The new JS framework will have to implement the architecture decided upon in [ADR 0001 change-ui-architecture](0001-change-ui-architecture.md):
  Instead of communicating with a UMC Python backend, it'll call REST APIs.

## Decision Drivers

- UI framework is very old and must be updated.
- Accessibility requirements.
- Make recruitment of new frontend developers easier, as they will be presented with a modern framework.

## Considered Options

- [Vue](https://vuejs.org/)
- [Dojo Toolkit](https://dojotoolkit.org/)
- TODO - more?

## Decision Outcome

Chosen option: "Vue", because
TODO - {justification. e.g., only option, which meets k.o. criterion decision driver | which resolves force {force} | … | comes out best (see below)}.

### Positive Consequences

- TODO -{e.g., improvement of one or more desired qualities, …}
- Vue is currently popular amongst frontend developers, which will make Univention a desirable employer.

### Negative Consequences

- TODO - {e.g., compromising one or more desired qualities, …}
- Using Vue instead of Dojo means, that the currently employed developers must learn a new web framework.
- Using Vue instead of Dojo means, that existing widgets etc. cannot be reused, but must be newly created.

## Validation

<!-- This is an optional element. Feel free to remove. -->

{describe how the implementation of/compliance with the ADR is validated. E.g., by a review or an ArchUnit test}

## Pros and Cons of the Options

<!-- This is an optional element. Feel free to remove. -->

### {title of option 1}

<!-- This is an optional element. Feel free to remove. -->

{example | description | pointer to more information | …}

- Good, because {argument a}
- Good, because {argument b}
- Neutral, because {argument c}  <!-- use "neutral" if the given argument weights neither for good nor bad -->
- Bad, because {argument d}
- … <!-- numbers of pros and cons can vary -->

### {title of other option}

{example | description | pointer to more information | …}

- Good, because {argument a}
- Good, because {argument b}
- Neutral, because {argument c}
- Bad, because {argument d}
- …

## More Information

Links to related decisions and resources:

- [ADR 0001 change-ui-architecture](0001-change-ui-architecture.md)
- [ADR 0003 rest-service-dedicated-to-ui](0003-rest-service-dedicated-to-ui.md)
- [Epic "Widget library for portal modules"](https://git.knut.univention.de/groups/univention/-/epics/262)
- [Epic "Create UI Design for (UCS@school) portal modules"](https://git.knut.univention.de/groups/univention/-/epics/261)
