
# Deployment of new UCS@school components

---

- status: accepted
- date: 2023-07-17
- deciders: UCS@school RAM subteam
- consulted: PM
- informed: UCS@school team, PM

---

## Context and Problem Statement

While the current UCS@school core product is based on a package based app in the UCS Appcenter, new components
and the future direction of Univention as a whole tend towards containerized services.

In addition, the path of deployment is also in flux. While most UCS@school components are still deployed
with the Univention Appcenter, we need to prepare for environments that deploy components developed by us
in Kubernetes.

The problem/question that is to be answered by this ADR is thus:

> How do the deployment artifacts look like, that we create in newly developed UCS@school components?

## Decision Drivers

- suitability for kubernetes
- BSI base security considerations
- compatibility with UCS concepts and paths of deployments (Appcenter)
- scalability
- ease of maintenance
- ease of testing
- ease of development

Some of those decision drivers have potential for conflict. Keeping to BSI base security requirements
might reduce the ease of maintenance or development. Thus, the drivers presented here are ordered roughly by
their importance.

## Considered Options

- multi service docker images
- mixed docker images and debian packages (currently used)
- single service docker images (currently used)

## Decision Outcome

Chosen option: "single service docker images"

It is the only option which really meets the criteria regarding kubernetes and BSI base security.
It also does not work against most of our other decision drivers as scaling, maintaining and testing
is less complex on smaller, simpler artifacts.

Deployment in the UCS Appcenter is also possible due to the support of docker compose apps.

The chosen option results in the following rules:

- New components are developed solely for deployment via docker images.
- Each docker image is allowed to contain only one service, which fulfills one purpose [^1].
- Each docker image needs to be fully configurable in a way that does not require the Appcenter [^2].
- Documentation on how the individual images interact with each other and how to set up
a working environment with docker compose has to exist.
- For release in the UCS Appcenter, one or multiple docker (compose) apps
have to be created.
- The images themselves are not concerned with scaling, load balancing, etc. This has to be handled
externally.

One consequence, which has to be kept in mind, is that proper versioning contracts have to be established to
enable easy use of the images. Proper versioning should be established to reduce hidden conflicts with updates.

### Positive Consequences

- Our docker images are simpler.
- We will not have to handle multiple services in one docker image.
- scalability of each individual part of a component, e.g. databases, caches, etc.
- Kubernetes' principles and best practices can be easily followed/adapted.
- Separation of concern can be enacted down to a very small level.

### Negative Consequences

- We will have to use the more complex docker compose apps in the Appcenter.
- We will be restricted to docker apps only.

## Additional information

This section is used to describe some common scenarios and how this ADR proposes to handle them.

### A component with a Web UI and Backend For Frontend (BFF)

One component could provide a user interface in form of a webpage. The component also implements
a network API the webpage is querying for data. The data is stored in some relational database.

This component should result in two docker images.

1) The image that exposes the webpage via HTTP
2) The image that exposes the network API for the webpage

The relational database is not a new docker image, but some already existing image for postgres, mariadb, etc.
This has to be provided in the deployment environment.

In Kubernetes those images are used directly.

In the UCS Appcenter we would either create one docker compose app that contains both images + relational database
or multiple Appcenter apps in case we want to allow for scaling of the webpage, network API and database individually.

### A component with a Web UI that utilizes existing UCS APIs

This component provides a user interface in form of a webpage. It requires access to existing UCS APIs, like the
UDM REST API or the Self Service APIs.

This component should result in one docker image.

1) The image that exposes the webpage via HTTP

In Kubernetes this image is used directly.

In the UCS Appcenter we would create a simple docker app with that image.

[^1]: The precise mechanism for service initiation within the docker container cannot be defined by this ADR.
It is up to the creator of the docker images to select their init system. They only have to ensure that a docker image
provides one service only. Future work of the SWP team might define the init system for all our containers.

[^2]: Appcenter settings are just written into the UCR derived `/etc/univention/base.conf` and thus not present
in a docker containers environment. That means that the images we create need to include some mechanism
to ingest Appcenter settings. In the Guardian for example this will be done with a composite adapter for the settings
which reads first from the environment and then from Appcenter settings.
