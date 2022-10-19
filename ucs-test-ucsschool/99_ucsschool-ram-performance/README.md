# Performance tests for RAM

## Structure

Performance test files with specifications are placed, as in every other section,
at the top level and have a number prefix. The test runs `locust` via a virtual environment
on one of the locust files in the directory `locustfiles`, which are prefixed with ``locust_``.
Utilities used by the locust files are located in `utils.py` and abstract base classes in `locustclasses.py`.

Adjust locust configuration for a specific test in the top level performance test file
via the global variable `LOCUST_ENV_VARIABLES`.

## Paths and enviroment variables

The path below which application relevant data and the python virtual environment
is stored is `/var/lib/ram-performance-tests/`. As the installation depends on this path,
it is not changeable via an environment variable.

- `UCS_ENV_KEYCLOAK_BASE_URL` Default: `ucs-sso-ng.ram.local`
  - Fully qualified domain name for Keycloak
- `UCS_ENV_BFF_TEST_DATA_PATH` Default: `/var/lib/test-data`
  - Path for the `diskcache` database with the test data
- `UCS_ENV_BFF_USERS_HOST` Default: `rankine.ram.local`
  - Fully qualified domain name for the users bff
- `UCS_ENV_BFF_GROUPS_HOST` Default: `rankine.ram.local`
  - Fully qualified domain name for the groups bff
- `UCS_ENV_BFF_TEST_ADMIN_PASSWORD` Default: `univention`
- `UCS_ENV_BFF_TEST_ADMIN_USERNAME` Default: `Administrator`

## Installation and usage

During development, build and install the package locally. Otherwise, install it as any other package with:

```shell
univention-install ucs-test-ucsschool-ram-performance
```

As any other section, all test can be run via:

```shell
ucs-test -E dangerous -s ucsschool-ram-performance
```

To run the `locustfiles` manually, run:

```shell
/var/lib/ram-performance-tests/venv/bin/locust -t <runtime> -f <locustfile> --headless --host <hostfqdn>
```

For example:

```shell
/var/lib/ram-performance-tests/venv/bin/locust -t 1m -f /usr/share/ucs-test/99_ucsschool-ram-performance/locustfiles/locust_users_post.py --headless --host backup1.ucs.local
```

To run the complete test including the stats checks:

```shell
pytest-3 /usr/share/ucs-test/99_ucsschool-ram-performance/01_users_post.py
```
