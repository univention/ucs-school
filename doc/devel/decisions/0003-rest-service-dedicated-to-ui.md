
# REST service dedicated to the UI

---

- status: accepted
- deciders: Ingo, Marie
- consulted: UCS@school team

---

## Context and Problem Statement

In  [ADR 0001 change-ui-architecture](0001-change-ui-architecture.md) we decided for an architecture where the JavaScript frontend gets data from REST APIs.

Existing REST APIs for UCS@school domain objects lack required information:

- UI layout
- Data types (although it may be possible to extract it from the OpenAPI schema)
- Attribute access permissions
- Action permissions
- Sorting
- Pagination
- User preferences (columns, filters, …)

## Decision Drivers

- Layout and behavior of the UI is highly configurable (layout, attributes, permissions, preferences).
- High scalability requirements.
- Make recruitment and integration of new frontend and backend developers easier, using a modern, non-proprietary software architecture.
- Improve development speed through separation of frontend and backend development.

## Considered Options

- Very smart frontend:
  - Retrieve data types from the OpenAPI schema of the Kelvin REST API and the UDM REST API.
  - Access [Open Policy Agent](https://www.openpolicyagent.org/) (OPA) directly to get permission and attribute information.
  - Sort and paginate lists of users and groups in the frontend.
  - Access the [Configuration database for distributed Systems](https://git.knut.univention.de/groups/univention/dev-issues/-/epics/19) to retrieve user preferences and layout information.
- Less smart frontend plus "Backend for frontend" (BFF) API:
  - One or more dedicated REST API services offer the above data in a format specifically adapted to the requirements of each UI module.
  - The BFF service(s) contact further backend services (Kelvin REST API, UDM REST API, OPA, Configuration database), collect, sort, merge and transform the data according to the requests from the UI.

## Decision Outcome

Chosen option: "Less smart frontend plus BFF", because

- It is easier to contact, collect, sort, merge and transform data in Python.
- The backend services do not need to be exposed to the public internet (the UI is running in an endusers browser).
  This reduces the authentication and authorization requirements of those services. (A "zero trust" security model would still be better.)
- Changing the interfaces of backend services does not affect the UI, as only the BFF must be adapted.
- The BFF can be written by both frontend and backend developers.

The BFF for the "Users" and "Groups" modules for the RAM/BSB project will be called "Rankine API".

The Rankine API will be implemented according to the [REST API stack for Univention](https://git.knut.univention.de/univention/internal/research-library/-/blob/main/personal/dtroeder/api_stack.md) using FastAPI, Gunicorn etc.

Access to the Rankine API must be authenticated by an external service (see [ADR 0005 authentication-in-the-new-UI-architecture](0005-authentication-in-the-new-UI-architecture)).

### Positive Consequences

- If a second UI (e.g. native mobile client) would be created, adapted BFF routed could be created for it, reusing the bulk of the business logic.
- Improved UI development speed, as the business logic (in the BFF) can be written in parallel to the fronend.
- REST backend are easy to benchmark.
- When the requirements of the UI change, frontend developers can adapt the BFF themselves, making frontend teams more independent of backend teams.

### Negative Consequences

- The additional REST API intermediary adds request latency.
- Single point of failure.

## Validation

- Retro regarding development process (separation of UI and BFF).
- Benchmark concurrent users.

## More Information

Links to related decisions and resources:

- [ADR 0001 change-ui-architecture](0001-change-ui-architecture.md)
- [ADR 0002 js-framework](0002-js-framework.md)
- [Epic "BFF for school portal modules"](https://git.knut.univention.de/groups/univention/-/epics/279)
- [Configuration database for distributed Systems](https://git.knut.univention.de/groups/univention/dev-issues/-/epics/19)
