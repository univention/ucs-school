@!@
func_template = '''
function FindProxyForURL(url, host) {
        return "PROXY %(host)s:%(port)s";
}
'''

print func_template % {
	'host' : "%s.%s" % ( configRegistry.get( 'hostnanme' ), configRegistry.get( 'domainname' ) ),
	'port' : configRegistry.get( 'squid/httpport', '3128' )
	}
@!@
