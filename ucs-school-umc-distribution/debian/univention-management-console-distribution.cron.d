SHELL=/bin/sh
PATH=/sbin:/bin:/usr/sbin:/usr/bin

20 3 * * * root find /tmp/webui/ -mtime +2 -name univention-management-console.*uploadFile.tmp | xargs -n20 -r rm -f >> /dev/null
