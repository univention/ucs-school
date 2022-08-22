
# Direct LDAP access in BFF users search endpoint

---

- status: accepted
- date: 2022-08-22
- deciders: UCS@school development Team
- consulted: Daniel Tröder, Ole Schwiegert, Carlos García-Mauriño, Felix Botner, Sönke Schwardt-Krummrich, Tobias Wenzel

---

## Context and Problem Statement

We need to retrieve and filter users for the BFF users search enpoint. The standard way of doing this would be through Kelvin but there are performance issues and not all needed attributes are available from Kelvin yet (e.g., when was the user modified last).

The question is whether to use direct LDAP access or Kelvin client to fetch users in the BFF search user endpoint.

## Decision Drivers

- time constrains
- performance
- prevention of code duplication

## Considered Options

### Direct LDAP access

Pros:
- Faster.
- We can currently get all needed attributes (including extended attributes by hardcoding them and last modified which is not currently available from UDM and thus Kelvin).
- Already implemented → smaller risk regarding the project.
Cons:
- Code duplication.
- Need to reimplement support for extended attributes.
- No improvement regarding the product.
- No support for kelvin hooks (or it has to be implemented manually).
Neutral:
- Unit tests take only 0.3 seconds → featureset is easy to compare with a different implementation.

### Kelvin

Pros:
- Reduces code duplication.
- Additional logic just in one place.
- No need for hardcoding extended attributes.
- Using kelvin already in MS1 gives us an idea regarding the actual performance and the need for improvement.
Cons:
- Attributes such as last modified are not yet available.
- The risk, that we cannot improve the performance to the extend we need it for the project.

## Decision Outcome

Chosen option: "Direct LDAP access", because is currently implemented, supports all needed attributes and is more performant. We will switch to Kelvin in MS2 (see https://luns.knut.univention.de/etherpad/p/RAMEpics) after the performance of Kelvin is improved and all required attributes can be fetched from it.
