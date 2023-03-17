
# Create and maintain english translations for end user documentation

---
<!-- These are optional elements. Feel free to remove any of them. -->

- status: accepted
- date: 09.03.2022
- deciders: Nico Gulden, Ole Schwiegert
- consulted: UCS@school Team, Marie Aurich
- informed: PM, UCS@school Team

---

## Context and Problem Statement

We have an increasing number of English speaking colleagues, which participate in the development of UCS@school.
A huge amount of knowledge about and implicit requirements towards the software are encoded in the administrative
manual as well as the teacher manual. These documents exist only in German and cannot be used or maintained by
non-German speakers.

## Decision Drivers

<!-- This is an optional element. Feel free to remove. -->

- Ease of maintaining documentation
- Ease of onboarding new colleagues
- Message sent by publishing the English documentation

## Considered Options

- Keeping German only end user documentation
- English translation without publishing
- English translation published at GitHub pages
- English translation published on our website

## Decision Outcome

Chosen option: "English translation published on our website", because
it was decided that an English translation is absolutely necessary for our english speaking colleagues alone. It was also
decided that this work should be shared with our customers in case they face similar problems or are interested in our
product coming from outside Germany.

The English documentation is not relevant for the target market and the target audience of UCS@school as currently seen from the product strategy, because UCS@school targets the German market.

The additional maintenance effort for the translation can be handled and the team takes care to keep the English translation synchronized with the German source content.

### Positive Consequences

<!-- This is an optional element. Feel free to remove. -->

- Colleagues not speaking German have access to all information regarding UCS@school
- Interested parties from outside Germany have access to our documentation as well
- We improve parity with the other documents at Univention (UCS manual)

### Negative Consequences

<!-- This is an optional element. Feel free to remove. -->

- We have to maintain the English translation
- Validation of initial translation is work of a couple of hours

## More Information

<!-- This is an optional element. Feel free to remove. -->

The documents that are being translated are:

- UCS@school manual for administrators
- UCS@school manual for teachers
- Quickstart Guide
- UCS@school scenarios
- Import manual
- UMC Import manual

Some mechanisms help us keep parity between the two versions of our documents:

- The doc pipeline fails if translation is missing
- A disclaimer on the English documents makes it clear that for any difference between the German and English versions,
  the former has precedence.
