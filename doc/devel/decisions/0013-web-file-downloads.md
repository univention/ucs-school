# File downloads in stateless back ends

---

- status: accepted
- date: 2023-03-23
- deciders: UCS@school team
- consulted: J Leadbetter, Sönke Schwardt-Krummrich, Carlos García-Mauriño

---

## Context and Problem Statement

When downloading a file from a back end, front end modules sometimes need to
additionally retrieve metadata.

Our first approach was to create an endpoint that returned JSON with
the metadata and the file as a base64 encoded string. Then the front end
would create a blob with the file contents and then proceed to download it.

The problem with the previous approach is that the default Content Security
Policy (CSP) of some browsers, for example Mozilla Firefox, don't allow blob downloads from
`iframe`s.

To solve this, we stored the file in a temporary directory and added an
endpoint for the direct download, which is allowed by Firefox's default CSP.

But, if there are multiple workers behind a load balancer, the request that
generates the file and the request to download it, might run in different
instances.

We need a way of providing metadata and a direct download endpoint keeping the
back end stateless.

## Decision Drivers

- Simplicity of the solution.
- Performance.
- Security.

## Considered Options

- Change the Portal CSP header to allow blob downloads from `iframe`s.
- Have a shared directory between the back end instances. Samba, NFS, Syncthing,
  Nextcloud, ...
  - Store the file in the DCD or Redis.
- Separate the endpoints for the metadata and the file generation + download.

The first option (change the Portal CSP header) is not possible since Bitflip
does not want to change it for security concerns. The second option (shared
directory between the back end instances) is possible but complex, the
deployment and maintenance of such an infrastructure would be costly. The third
option (separate the endpoints for the metadata and the file generation +
download) is possible and requires a small effort to be implemented.

## Decision Outcome

Chosen option: "Separate the endpoints for the metadata and the file
generation + download", because it's easy to implement with no negative impact
on performance or security.

## Negative consequences

- The back end will have to authorize the request 2 times and maybe even
  calculate the complete response two times if parts of it are contained in the
  metadata.
- Although the front end should send both requests in quick succession or even
  simultaneously, there could be a difference in the responses, as data may be
  changed by a parallel process.
