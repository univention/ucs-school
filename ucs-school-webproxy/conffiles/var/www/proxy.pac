function FindProxyForURL(url, host) {
@!@
import json

def print_parent_proxy_or_direct(var):
	if configRegistry.is_true(var, False):
		print '            return %s;' % (json.dumps("PROXY %s:%s" % (configRegistry.get('squid/parent/host'), configRegistry.get('squid/parent/port'))),)
	else:
		print '            return "DIRECT";'

if configRegistry.is_true('proxy/pac/exclude/localhost', False):
	print '        // If the requested host is the local machine, send "DIRECT" (no proxy is used):'
	print '        if (isInNet(host, "127.0.0.0", "255.0.0.0") || dnsDomainIs(host, "localhost"))'
	print '            return "DIRECT";'
	print

if configRegistry.is_true('proxy/pac/exclude/networks/enabled', False):
	print '        // If the requested host is in the given network, send "DIRECT" (no proxy is used) or use parent proxy:'
	for network in configRegistry.get('proxy/pac/exclude/networks/networklist', '').split(" "):
		items = network.split('/')
		if not items:
			continue
		if len(items) == 1:
			items.append('255.255.255.0')
		print '        if (isInNet(host, %s, %s))' % (json.dumps(items[0]), json.dumps(items[1]))
		print_parent_proxy_or_direct('proxy/pac/exclude/networks/parentproxy/enabled')
	print

if configRegistry.is_true('proxy/pac/exclude/domains/enabled', False):
	print '        // If the requested dns domain name matches, send "DIRECT" (no proxy is used) or use parent proxy:'
	for dnsdomain in configRegistry.get('proxy/pac/exclude/domains/domainnames', '').split(" "):
		print '        if (dnsDomainIs(host, %s))' % (json.dumps(dnsdomain), )
		print_parent_proxy_or_direct('proxy/pac/exclude/domains/parentproxy/enabled')
	print

if configRegistry.is_true('proxy/pac/exclude/expressions/enabled', False):
	print '        // If the requested shell expression matches, send "DIRECT" (no proxy is used) or use parent proxy:'
	for shExp in configRegistry.get('proxy/pac/exclude/expressions/expressionlist', '').split(" "):
		print '        if (shExpMatch(url, %s))' % (json.dumps(shExp), )
		print_parent_proxy_or_direct('proxy/pac/exclude/expressions/parentproxy/enabled')
	print

print '        // DEFAULT RULE : All other traffic will use these settings (default proxy):'
print '        return %s;' % (json.dumps("PROXY %s.%s:%s" % (configRegistry.get('hostname'), configRegistry.get('domainname'), configRegistry.get('squid/httpport', '3128'))),)
@!@
}
