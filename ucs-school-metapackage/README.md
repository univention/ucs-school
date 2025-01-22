# ucs-school-metapackages

## Pre-join hook "ucsschool-join-hook.py"

In UCS, it is possible to execute hooks before the join process resp. before or after executing the join scripts. These hook scripts are registered in the LDAP directory and downloaded from the LDAP directory with the credentials transferred during the join process and executed on the joining system.

UCS@school uses a hook before the join scripts are executed. This hook checks on all systems during the join process or during a univention-run-join-script whether the necessary UCS@school meta package is installed for the respective system.

UCS@school delivers a meta package for each directory node system role, which makes specific settings for the system. It also distinguishes between normal replica directory nodes and those that are to function as school servers. The meta package installs the complete UCS@school on school servers, for example. This means that since the introduction of the join hook, manual installation of UCS@school is only necessary on the primary directory node.

The background to this is that some Samba4 settings must be made before the join scripts are executed for the first time, which cannot be easily corrected later. As a rule, a new installation is then necessary.

To reduce the number of incorrect installations, the join hook mechanism and the corresponding pre-join script hook were introduced for UCS@school.
