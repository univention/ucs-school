#!/usr/share/ucs-test/runner python
## bugs: [40470]
## desc: Check that school-servers (except master and backup) have their DNS related ucr variables set to the right values.
## exposure: safe
## roles:
##  - domaincontroller_slave
## tags: [apptest, ucsschool]

from univention.testing.ucr import UCSTestConfigRegistry


def main():
	with UCSTestConfigRegistry() as ucr:
		ucrv_forward = ucr.get('dns/nameserver/registration/forward_zone')
		assert ucr.is_false(value=ucrv_forward), "The ucr variable 'dns/nameserver/registration/forward_zone' is set to '%s', but must be set to 'no'." % (ucrv_forward,)
		ucrv_reverse = ucr.get('dns/nameserver/registration/reverse_zone')
		assert ucr.is_false(value=ucrv_reverse), "The ucr variable 'dns/nameserver/registration/reverse_zone' is set to '%s', but must be set to 'no'." % (ucrv_reverse,)


if __name__ == '__main__':
	main()
