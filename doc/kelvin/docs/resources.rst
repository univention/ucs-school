Resources
=========

Resources may support a varying range of operations: retrieve, search, create, modify, move and delete.

Pagination has not yet been implemented.
When it is, there will be ``<Link>`` entries in the response headers.
The format of the JSON response in the body will not change.

Requests to resource endpoints must carry a valid token.
Section :ref:`Installation and configuration` describes how to obtain one.
Sending no or an invalid token leads to the server responding with HTTP status ``401``.

The token must be in the ``Authorization`` header with a value ``Bearer <token>``. E.g.::

    "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...."


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   resource-roles
   resource-schools
   resource-users
