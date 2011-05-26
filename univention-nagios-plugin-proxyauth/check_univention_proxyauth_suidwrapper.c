#include <signal.h>
#include <sys/param.h>
#include <pwd.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>

#define COMMAND "/usr/lib/nagios/plugins/check_univention_proxyauth"


main( int argc, char ** argv, char ** envp )
{
    int status = 0;
	uid_t uid = getuid();
    if( setgid(getegid()) ) perror( "setgid" );
    if( setuid(geteuid()) ) perror( "setuid" );
	execle(COMMAND, COMMAND, (char *)0, (char *)0);
	setuid(uid);
	exit(1);
}
