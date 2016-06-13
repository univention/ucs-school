Global configuration file reference
===================================

The configuration files are in JSON format. All options can be set from the
command line using "--set <option> ...". Multiple options can be listed
space-separated. Nested options are set using colon (':') as seperator, e.g.:
--set verbose=True input:type=csv 'scheme:username:student=<firstname>.<lastname>'

Configuration files are read in a predefined order. Settings in later read
configuration files overwrite settings from prior ones. The order is:
1. /usr/share/ucs-school-import/configs/global_defaults.json (do not edit)
2. /var/lib/ucs-school-import/configs/global.json (edit this)
3. Module specific configuration from /usr/share/ucs-school-import/configs/ (do not edit)
4. Module specific configuration from /var/lib/ucs-school-import/configs/ (edit this)
5. Configuration file set on the command line.
6. Options set on the command line by --set and its aliases.


"dry_run": bool: set to False if changes should be committed to LDAP
"logfile": str: path to additional logfile
"verbose": bool: if enabled, log output of level DEBUG will be send to the command line (stdout)
