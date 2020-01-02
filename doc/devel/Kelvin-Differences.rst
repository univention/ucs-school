.. to compile run:
..     $ rst2html5 kelvin-api.rst kelvin-api.html

Differences in UCS@school lib Kelvin vs Stock
=============================================
base.py

- The lo object is now of type UDM
- Most functions are now asynchronous due to the UDM REST Client
- Hooks are not supported yet
- init_udm_module  does not exist anymore
- _attrs_for_easy_filter is not implemented anymore (missing low level UDM access)
- _build_hook_line was removed

computer.py

- build_hook_line was removed

group.py

- build_hook_line was removed

school.py

- build_hook_line was removed
- _filter_local_schools is not used in get_all anymore (which means all schools are returned)

share.py

- function get_server_udm_object was added

user.py

- build_hook_line was removed

utils.py

- added function env_or_ucr
- added function mkdir_p
- class ModuleHandler was removed
- added class UCSTTYColoredFormatter