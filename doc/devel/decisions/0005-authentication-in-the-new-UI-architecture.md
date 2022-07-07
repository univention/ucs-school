
# Authentication in the new UI architecture

---

- status: accepted
- deciders: Ingo, Marie
- consulted: UCS@school team, Dirk W.

---

## Context and Problem Statement

In our new UI architecture ([ADR 0001 change-ui-architecture](0001-change-ui-architecture.md)) the UI component (JavaScript running in the endusers browser, [ADR 0002 js-framework](0002-js-framework.md)) will have to present an authentication token to the Rankine API ([ADR 0003 use-rest-service-dedicated-to-ui](0003-use-rest-service-dedicated-to-ui.md)).

## Decision Drivers

- Use a standardized protocol, so that the artifacts (tokens) can be used by a wide range of services.
- Authentication is a central security concern, so use an existing, well maintained, trusted and documented product.

## Considered Options

- [Keycloak](https://www.keycloak.org/): use Keycloak as IdP that issues OAuth2 / OpenID Connect tokens.
- UMC session cookie: use the cookie created by the existing login page.

## Decision Outcome

Chosen option: "Keycloak", because

- we want to use standardized protocols
- all REST API frameworks support authentication using OAuth2 tokens
- authentication using UMC session cookies would have to be custom-built
- Keycloak is better documented than the UMC
- If the UMC is to be abandoned one day in favor of the new UI architecture, the IdP would be gone as well.

### Positive Consequences

- Knowledge and experience with Keycloak exists in the development and PS teams from a variety of projects.
- Keycloak is known to be highly scalable.
- The REST API framework used for the Rankine/BFF API already supports authentication using OAuth2 tokens.

### Negative Consequences

- An additional runtime requirement: the Keycloak service.

## More Information

Links to related decisions and resources:

- [ADR 0001 change-ui-architecture](0001-change-ui-architecture.md)
- [ADR 0002 js-framework](0002-js-framework.md)
- [ADR 0003 rest-service-dedicated-to-ui](0003-rest-service-dedicated-to-ui.md)
- [Keycloak](https://www.keycloak.org/)
- [UMC developer docs](https://docs.software-univention.de/developer-reference-5.0.html#chap:umc)
