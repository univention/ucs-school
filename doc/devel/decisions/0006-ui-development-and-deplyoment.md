
# UI development and deployment

---

- status: superseded by [ADR 0014](0014-component-deployments.md)
- deciders: UCS@school development team
- consulted: UCS@school development team
- informed: Ingo, Marie

---

## Context and Problem Statement

---

**Note**: In the following text, `backend` means the backend to the UI - the Rankine (BFF) API.
It does *not* mean a "real" backend API like the Kelvin or UDM REST APIs.

---

The frontend ([ADR 0002 js-framework](0002-js-framework.md)) is executed in the end users browser, the backend ([ADR 0003 rest-service-dedicated-to-ui](0003-rest-service-dedicated-to-ui.md)) in a Docker container on a central UCS node.

The frontend and the backend code can be developed and deployed separately or together.

When developed in the same git repository, related changes are easier to track.
When developed in separate git repositories, all the backend code can be in one place.

When deployed together it must mean, that the UI code (JavaScript) will be stored in a Docker container, as the Rankine API must be deployed is a Docker app.
When deployed separately, the UI could be installed as a Debian package and the Rankine API as a Docker app.

For both the frontend and the backend it is not clear, whether it would be desirable to create one app for multiple modules or (more or less) strictly separated modules (one or multiple `index.html` and one or multiple Docker apps).

## Decision Drivers

- Speed, ease and stability of updates.
- Allow updating frontend and backend separately.
- Allow code reuse between multiple modules in both the frontend and the backend.
- Allow developing frontend and backend separately.
- Ensure compatibility at runtime between frontend and backend, when updated separately.

## Considered Options

The following options are not mutually exclusive.
Instead, we are looking for a favorable combination.

- One "page" for *multiple* UI modules
- One "page" *per* UI module
- One REST API service for *multiple* UI modules
  - with the Python code for all routes *backed-in*
  - with the Python code for each route in *plugins*, installable as Debian packages (like in the `ucsschool-apis` app)
- One REST API service *per* UI module
- Deployment of UI as Debian package
- Deployment of UI in Docker container together with backend
- One REST API container for *multiple* REST API services
- One REST API container *per* REST API service
- If multiple Docker containers
  - all containers together in one app as Docker-Compose app
  - one app per container
- One git repository for/per UI module(s) and separate for/per backend module(s).
- Common git repository for/per UI module(s) with the respective backend module(s).

## Decision Outcome

Chosen options:

- One "page" *per* UI module, because
  changing one module, does not change another and less JS code is loaded per module.
- One REST API service *per* UI module, because
  we want to be able to update modules separately.
- One REST API container *per* REST API service, because
  they can be updated and scaled separately.
- One app per container, because
  that is easier to debug than Docker-Compose setups.
- Deployment of UI as Debian package, because
  it is easier and faster to update.
- Common git repository for UI modules with the respective backend modules, because
  related changes are easier to track.

### Positive Consequences

- One "page" *per* UI module:
  - Changes to one module do not change another modules, results in safer updates.
  - Only the JS code and its dependencies that is required is loaded (per module).
  - Versions of UI modules can differ.
- One REST API service *per* UI module:
  - Code for the backend can be stored together with the frontend code.
  - No delicate plugin setup at runtime.
  - Robust plugin setup at Docker build time.
  - Versions of backend services can differ.
- One REST API container *per* REST API service:
  - Stability: the crash of one backend (e.g. for "Manage users") does not affect other backend modules.
- One app per container:
  - Smaller apps can be released faster.
- Deployment of UI as Debian package:
  - Can be delivered as static content by the hosts Apache.
- Common git repository for UI modules with the respective backend modules:
  - Related changes are easy to track.
  - API client and server version changes happen in the same place.

### Negative Consequences

- One "page" *per* UI module:
  - Browsers that open multiple modules, load common code multiple times.
- One REST API service *per* UI module:
  - Higher memory usage, as more processes are running and duplicate code is in memory.
  - More processes and logfiles to supervise for the support.
- One REST API container *per* REST API service:
  - More places (logfiles, processes etc.) to look at, when debugging.
- One app per container:
  - More apps in the production Appcenter that have no value on their own.
- Deployment of UI as Debian package:
  - Incompatible versions of UI and its respective REST API service can be installed.
- Common git repository for UI modules with the respective backend modules:
  - Backend modules must be packaged as some kind of plugins.

## Notes

- Per-module and common frontend code must be developed as npm-installable projects, which will be assembled / compiled at Debian build time.
- Per-module and common backend code must be developed as pip-installable projects, which will be installed at Docker build time.
- The APIs of the REST API services must be versioned and the UI must show an appropriate error, when the required API version is not supported by the backend.

## More Information

Links to related decisions and resources:

- [ADR 0002 js-framework](0002-js-framework.md)
- [ADR 0003 rest-service-dedicated-to-ui](0003-rest-service-dedicated-to-ui.md)
