# Naming convention

---

- status: accepted
- date: 2022-09-27
- deciders: UCS@School
- consulted: Alexander Steffen, Nico Gulden, Sönke Schwardt-Krummrich,
  Daniel Tröder, Carlos García-Mauriño

---

## Context and Problem Statement

In te context of the RAM project, a lot of different terms are used to refer to
different entities, such as the Debian packages, the App Center Apps, ...

We want to settle on a convention to reduce confusion among developers and ease
the process of naming new components.

## Decision Drivers

- Currently the naming is not coherent.
- Renaming App Center apps is not easy.
- Renaming Debian packages could cause some issues.
- Renaming UCR variables can break scripts (Processional Services, third party,
  help articles, ...).

## Considered Options

- Leave it as it is and not settle on a naming convention.
- Settle on a convention and change all existing components.
- Settle on a convention and use it from now on.

## Decision Outcome

Chosen option: "Settle on a convention and use it from now on", because
changing all existing stuff would require a lot of effort and the pay off is
small. On the contrary just following the convention from now on takes no
effort (it even makes the naming process of new components easier).

### Positive Consequences

- Reduced confusion among developers and users.
- Easier naming of new modules.

### Negative Consequences

- Confusion when looking at old code and when searching for or browsing
  variables / packages / "names" in existing repositories.
- Inconsistency, when the naming convention from now on is different from past
  namings.

## Convention

- UCS@school should be written as `ucsschool` (no dash) wherever we can't put
  the `@`. This includes variable names, Debian packages, Git repositories...
- UCS@school UI modules:
  - Repository name: `ui-{modulename}`.
  - Front end directory in the repository: `frontend`.
  - Back end directory in the repository: `backend`.
  - Back end App Center App ID: `ucsschool-bff-{modulename}`.
  - Debian package for the frontend: `ucs-school-ui-{modulename}-frontend`.
  - Keycloak client ID used by all UCS@school UI modules in production:
    `ucsschool-ui`.
  - Keycloak client ID used by all UCS@school UI modules for development:
    `ucsschool-ui-dev`.
  - Path used for the web interface: `/univention/ui/ucsschool-{modulename}`.
  - Path for the back end configuration: `/etc/ucsschool/bff-users`.
  - `appcenter/settings` keys are not prefixed. They are local to the app and
    don't need a namespace (e.g. `kelvin_username`). This makes it easy for
    shared libraries to get the values of those settings on their own without
    relying on the main App.
  - UCR variables in Debian packages (front end) are prefixed with
    `ucsschool/{modulename}/` (e.g. `ucsschool/ui_users/backendURL`).

### UCS@school UI modules

Terms (old naming in ~~strikethrough~~, new naming in **bold**).

- `ui-users`: Name of the UI module for user management. Constituted by the
  front end and the back end. Same as the repository name.
- `frontend`: directory in the root of this repository to store the front end
  code.
- ~~rankine~~**backend**: directory in the root of this repository to store the
  back end code.
- `ucsschool-bff-users`: App Center app name for the back end.
- `ucs-school-ui-users-frontend`: Debian
  package name for the front end and CN used for the LDAP portal entry of the
  front end.
- ~~ucs-school-ui-users~~**ucsschool-ui**: Keycloak client ID used by
  `ui-users`.
- ~~school-ui-users-dev~~**ucsschool-ui-dev**: Keycloak client ID used by
  tests and for development.
- `ucsschool-users`: Path used for the web interface. The full path is
  `/univention/ui/ucsschool-users`/
- ~~bff-ui-users~~**bff-users**: Path for the back end configuration. Full
  path `/etc/ucsschool/`~~bff-ui-users~~**bff-users**.
