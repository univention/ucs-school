@startuml
actor User
participant "ucs-school-user-import"
participant ConfigPyHook
participant PreReadPyHook
participant PostReadPyHook
participant FormatPyHook
participant UserPyHook
participant ResultPyHook

User -> "ucs-school-user-import": Start import

"ucs-school-user-import" -> ConfigPyHook
note over ConfigPyHook: post_config_files_read():\nCalled after reading the configuration files and command line arguments,\nbut before making the configuration object read-only.\n(config, lo, logger available)
ConfigPyHook -> "ucs-school-user-import"

"ucs-school-user-import" -> PreReadPyHook
note over PreReadPyHook: pre_read():\nCalled before reading the CSV file\n(config, lo, logger available)
PreReadPyHook -> "ucs-school-user-import"

note over "ucs-school-user-import": Load CSV file
note over "ucs-school-user-import": Trim leading/trailing whitespace

"ucs-school-user-import" -> PostReadPyHook
note over PostReadPyHook: entry_read():\nAdjust or skip data record directly after reading it. Executed after each entry.\n(lo+logger available)
PostReadPyHook -> "ucs-school-user-import"

"ucs-school-user-import" -> PostReadPyHook
note over PostReadPyHook: all_entries_read():\nCalled after all data records have been read\n(lo+logger available)
PostReadPyHook -> "ucs-school-user-import"

"ucs-school-user-import" -> FormatPyHook
note over FormatPyHook: patch_fields_$ROLE():\nAdjust fields TEMPORARILY for evaluating\ncorresponding scheme
FormatPyHook -> "ucs-school-user-import"

note over "ucs-school-user-import": Evaluate field schemata by using data\nfrom FormatPyHooks (e.g. make_username)

alt "user is about to be created"

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: pre_create(user):\nAdjust fields and UDM properties in <user> as desired\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

    note over "ucs-school-user-import": Create new user

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: post_create(user):\nPerform required manual actions in LDAP or somewhere else\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

else "user is about to be modified"

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: pre_modify(user):\nAdjust fields and UDM properties in <user> as desired\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

    note over "ucs-school-user-import": Modify existing user

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: post_modify(user):\nPerform required manual actions in LDAP or somewhere else\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

else "user is about to be deactivated and marked for purging"

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: pre_modify(user):\nAdjust fields and UDM properties in <user> as desired.\nThis special case can be detected by checking\nuser.udm_properties[\"ucsschoolPurgeTimestamp\"]\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

    note over "ucs-school-user-import": Modify existing user and mark user\nfor deletion at specified date.

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: post_modify(user):\nPerform required manual actions in LDAP or somewhere else\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

else "user is about to be moved/renamed in LDAP"

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: pre_move(user):\nAdjust fields and UDM properties in <user> as desired\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

    note over "ucs-school-user-import": Move existing user in LDAP

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: post_move(user):\nPerform required manual actions in LDAP or somewhere else\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

else "user is immediately removed from LDAP !OR! automatically removed via cron job after reaching the purgeTimestamp"

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: pre_remove(user):\nAdjust fields and UDM properties in <user> as desired\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

    note over "ucs-school-user-import": Remove existing user from LDAP

    "ucs-school-user-import" -> UserPyHook
    note over UserPyHook: post_remove(user):\nPerform required manual actions in LDAP or somewhere else\n(lo+logger available)
    UserPyHook -> "ucs-school-user-import"

end

"ucs-school-user-import" -> User: Show results

"ucs-school-user-import" -> ResultPyHook
note over ResultPyHook: user_result(user_import):\nHook has access to import results and\ncan e.g. send mails in case of import errors.
ResultPyHook -> "ucs-school-user-import"

@enduml
