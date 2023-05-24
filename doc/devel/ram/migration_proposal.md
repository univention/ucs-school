# Migration of UCS@school to Roles and Access Model (RAM)

## Introduction

Currently, UCS@school implements authorization together with the functionality.
There are a set of predefined user roles that are checked in the code.

RAM is a new authorization framework that we want to use. It allows for custom
roles, delegates the authorization logic to the Guardian and the role
management and storage to UDM.

This document describes the migration of UCS@school to Roles and Access Model
(RAM), which is an attribute based authorization system that allows for
custom roles with fine tuned permissions.

### Versions

Currently UCS is in version 5.0. It will be updated to 5.1 as an intermediate
release and then to 5.2. No system should stay in 5.1, it's just a step in the
update required since two major Debian release upgrades will take place.

## Requirements

* Domains with nodes from different 5.x versions should be supported. There
  might be a timespan where the primary is already in 5.2 but some nodes are
  still in 5.0. During that time roles should be maintained in the old way
  alongside the new way. It's OK to limit the creation of custom roles or
  changes to the existing ones from the Guardian until all nodes are in 5.2.
* There should be an option to rollback the changes to the objects.

## Migration

## Code changes

Before the migration, the UCS@school code should switch to using ports an
adapters for getting the roles of an object (user or group). Initially, the
role would be retrieved from the LDAP attribute ucsschool_roles but would
allow for switching the backend to UDM when needed.

Supported version combinations within a domain:

* 5.0 supports 4.4 v9 (last 4.4 release, uses `ucsschool_roles` attribute)
  objects and vice-versa.
* 5.0 supports read-only of 5.2 roles.
* 5.2 supports read and write of 5.0 roles.

### Components that need to change

* UCS@school lib
* Kelvin

This changes can be added as an errata release to 5.0.

### Checklist

* Register the UCS@school app in the Guardian.
* Register the required contexts in the Guardian.
  We will use the following contexts:

  * `school-{school_name}`: should be created during the migration.
  * `exam-{exam_name}`: should be created on demand, when an exam is created
    and removed afterwards. The capabilities of this context should be
    created on the fly as well.
* Create the default UCS@school roles in the Guardian.
* Set the roles for all existing UCS@school objects with UDM.
* After all nodes are in 5.2, remove the old roles from the objects.
