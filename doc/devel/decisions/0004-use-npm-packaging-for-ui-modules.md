
# Use npm packaging for JavaScript modules

---

- status: accepted
- deciders: Johannes
- consulted: Daniel

---

## Context and Problem Statement

We want a (self developed) UI library that can be used by multiple projects.
The library should contain the basic building blocks and styles to develop our different frontends in the same look
and behaviour.

The main question is how the library will be installed/used.

## Decision Drivers

For the new Univention Portal there were generic components created, that would be used in other projects, but they
are in the same repository (and tangled withing the other Portal code) as the Portal.

For the RAM project we now want to use those components and therefore create a component library repository.

## Considered Options

- Gitlab npm registry: The library is build and pushed to an internal [Gitlab npm registry](https://docs.gitlab.com/ee/user/packages/npm_registry/).
  The library can then be installed via npm like any other npm dependency.
- CDN: The library is provided via a CDN and downloaded via `<script>` tag.
- File on Host: The library is installed/put on the host and downloaded via `<script>` tag.

## Decision Outcome

Chosen option: "Gitlab npm registry", because
the Pros of the Gitlab npm registry out-ways the Cons of its option and also the Pros of the others (see below)}.

### Gitlab npm registry

- Good, because it integrates easily in the development process (also enables optimizations in bundling like tree-shaking etc.).
- Good, because the using project has more certainty about the stable-ness of its releases since the library version is a hard dependency.
- Bad, because if a new version of the library is released, all using projects have to release a new version with the
  library version updated.

### CDN

- Good, because releasing a new library version is easy.
- Neutral, because without versioning using frontend could break when new version is released.
- Bad, because a running network connection and reachable CDN is required.

### File on host

- Good, because only the library has to be updated and all frontends that use it have the new version.
- Bad, because the library could be updated independently of the using frontend (and vive versa) and break things.

## More Information

- [Issue "Create Gitlab pipeline to validate and push UI components into Gitlabs npm registry"](https://git.knut.univention.de/univention/internal/research-library/-/issues/6)
