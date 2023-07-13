# Deployment of the Guardian components

---

- status: accepted
- date: 2023-07-17
- deciders: UCS@school RAM subteam
- consulted: PM
- informed: UCS@school team, PM

---

## Context and Problem Statement

The Guardian will be one of the central components of the role and rights management in UCS, and it will be deployed
in varied environments; from single server UCS domains to distributed kubernetes deployments with the SWP project.

Because of this, the composition of the components making up the Guardian should be chosen carefully.

The Guardian consists of the following components:

### Policy Repository

This component stores any information that is related to the management of the Guardian. This includes
roles, namespaces, conditions, mappings and custom policy code. Not included are the attributes of objects policies act
on (actors and targets).

### Management API

An API for manipulating the Policy Repository. With this component namespaces, conditions, mappings, etc. can be created
and modified.

### Policy Evaluation component

This component will be supplied with information from the Policy Repository and is capable of calculating the results
of policy requests.

### Authorization API

This component provides an API to interact with the Policy Evaluation component and constitutes the Policy Decision Point.

### Data layer

This component allows the authorization API to fetch actors and targets on the clients behalf to pass their attributes
on to the Policy Evaluation component.

---

The architecture of the Guardian should follow [ADR 0014](0014-component-deployments.md) and should ensure
maximum flexibility, scalability and separation of concerns.

## Decision Drivers

- ease of maintenance
- suitability for Kubernetes environments
- scalability
- compatibility with our UCS concepts
- Adhering to [ADR 0014](0014-component-deployments.md)

## Considered Options

This ADR documents the agreed upon decision, rather than comparing different solutions and weighing them
against each other.

## Decision Outcome

It was chosen to make each component of the guardian deployable on its own as a docker container,
independent of the others.

This allows for maximum flexibility in a kubernetes environment and maximises the separation of concerns.
It also decreases the coupling between each component and minimizes the risk on each component if another might
be breached.

This means the [Guardian project](https://git.knut.univention.de/univention/components/authorization-engine/)
will produce the following docker images:

- Guardian Management API
- Guardian Authorization API
- Guardian Policy Evaluation Component (OPA)
- Guardian Management UI

The images will have the following properties:

- Each image will provide one service only
- None of the images will expose HTTPS. It is expected to be handled by a proxy.
- All images will be [semantically versioned](https://semver.org/).
- All images will implement a [healthcheck](https://docs.docker.com/engine/reference/builder/#healthcheck)
- All images shall be fully configurable as to where to connect to for dependencies. This allows for injecting
external load balancing mechanisms as well as easy setups with one container for each service.
- All images will be based on a debian image with the s6 init system. This might change if the SWP team
  defines a standard process of creating images.

Notably absent are the **Policy Repository** and the **Data Layer**. The **Data Layer** is already implemented
in the UCS product as the UDM REST API and thus does not need to be created by the Guardian project.

The policy repository will most likely be some kind of relational database, which is implemented and published
as docker images already.

While Kubernetes will be able to utilize those images to set up a working environment, UCS is currently based on the
Appcenter, and thus we have to bundle the images as apps in a sensitive way. The following apps will be created
in the Appcenter:

### Guardian Authorization

A docker compose app that includes the Guardian Authorization API as well as the Guardian Policy Evaluation Component
in form of an OPA service.

### Guardian Management API

A docker compose app, which contains the management API as well as the policy repository.
The repository has to be synced within the UCS domain using the tools the chosen technology will offer.

### Guardian Management UI

A docker app, which contains the management UI. It will be served via HTTP on a specified port.

## Additional points

### Scaling/load balancing in the Appcenter

The apps itself will not be concerned about load balancing or scaling. Since the component is split into three
different apps (which should be configurable as to where they have to connect to find each other), scaling and load
balancing can be done on the operators discretion.

### UDM as Policy Repository

Using UDM as the policy repository for the management API is not yet excluded. If chosen the Guardian Management API App might
not have to be a docker compose app.

### Policy distribution

One component not mentioned here is the distribution of the data needed by the evaluation point from the policy repository.
There are multiple possible solutions from some static bundle repository to using UDM and pushing compiled data via listeners
to the OPA instances. The chosen option will influence the details of this decision, but not impact the central point
of one image per service. If a decision is made a new ADR in form of an addendum to this one shall be created.
