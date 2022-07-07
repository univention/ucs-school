
# Use npm packaging for JavaScript modules

---

- status: accepted
- deciders: Johannes
- consulted: Daniel

---

## Context and Problem Statement

We want to make (self developed) UI components installable the same way, public JavaScript software is added to our projects.

Our CI/CD system offers the internal [Gitlab npm registry](https://docs.gitlab.com/ee/user/packages/npm_registry/).

TODO - {Describe the context and problem statement, e.g., in free form using two to three sentences or in the form of an illustrative story.
 You may want to articulate the problem in form of a question and add links to collaboration boards or issue management systems.}

## Decision Drivers

<!-- This is an optional element. Feel free to remove. -->

- {decision driver 1, e.g., a force, facing concern, …}
- {decision driver 2, e.g., a force, facing concern, …}
- … <!-- numbers of drivers can vary -->

## Considered Options

- {title of option 1}
- {title of option 2}
- {title of option 3}
- … <!-- numbers of options can vary -->

## Decision Outcome

Chosen option: "{title of option 1}", because
{justification. e.g., only option, which meets k.o. criterion decision driver | which resolves force {force} | … | comes out best (see below)}.

### Positive Consequences

<!-- This is an optional element. Feel free to remove. -->

- {e.g., improvement of one or more desired qualities, …}
- …

### Negative Consequences

<!-- This is an optional element. Feel free to remove. -->

- {e.g., compromising one or more desired qualities, …}
- …

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

- [Issue "Create Gitlab pipeline to validate and push UI components into Gitlabs npm registry"](https://git.knut.univention.de/univention/internal/research-library/-/issues/6)
