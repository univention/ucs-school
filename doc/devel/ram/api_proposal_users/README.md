# RAM users module BFF for the first release

## Keep

* Tightly coupled backend for the frontend. To simplify the frontend as much as
  possible.
* Page configuration endpoints for list view and add view. They contain all
  information for the frontend (layout, labels, input types...).
* Oauth flow:
  https://auth0.com/docs/get-started/authentication-and-authorization-flow/add-login-using-the-authorization-code-flow-with-pkce
* Users module is a tile in the portal that renders a website inside an iframe.
* User creation does not restrict fields: if a user does not have enough
  permissions, they will receive an error message after clicking save
  (e.g. if they try to create a user with a role that they are not allowed to).
* Version prefix for endpoints. I.e., `v1`.
* Action endpoints instead of using the generic PATCH endpoint.

## Change

* Multiple schools at a time.
* No support for non-standard ucsschool attributes. That implies changing the filters for the
  search endpoint and the response models. This will be added later on.
  * OPA: no extended attributes.
* No actions support apart from CRUD. Deactivate, export CSV... will be added later.
* Action endpoints (deactivate, toggle wifi...) should support a list of targets
  instead of just one. Whenever they are implemented.
* Role changes are allowed.
* No additional roles, other than default school roles (student, teacher,
  school_admin, staff). Users can have multiple roles.
* All authorization logic is moved to the Guardian. For BSB we implemented
  authorization logic in the
    [groups module](https://git.knut.univention.de/univention/ucsschool-components/ui-groups/-/blob/80f8e8cab6871f35c1fc14455d23dfe0ff7d50cf/rankine/rankine_groups/v1/groups.py#L612);
    going forward we want to remove this in both the groups and users modules.
* Direct usage of the UDM REST API is not required anymore (since reset-passwords endpoint won't be implemented yet). All operations will be done through the Kelvin REST API.
* No camel case renaming: the attributes keep the naming from Kelvin.
* Everything for the backend is in a single repository -- groups, users,
  common libs. Frontend is also in the repository, but may keep separate pages
  for deployment purposes. At least until the creation of another app requires sharing code.
  * The frontend and the backend always have the same version.
* Frontend is deployed as part of the Docker container. No Debian package.
  One app installs the whole functionality.
* No LDAP access. Everything should be done through Kelvin.
  **Performance will be poor** until Kelvin and UDM support pagination and
  sorting. Additionally, Kelvin might need to add support endpoints for
  retreieveing information about extended attributes.
* The Guardian instead of OPA.
