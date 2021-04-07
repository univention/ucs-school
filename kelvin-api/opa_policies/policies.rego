package ucsschool.kelvin

default users = false

default schools = false

default classes = false

default roles = false

# Allow kelvin_admin to do any operations
users {
	actor.kelvin_admin
}

schools {
	actor.kelvin_admin
}

classes {
	actor.kelvin_admin
}

roles {
	actor.kelvin_admin
}

allowed_users_list[user.username] {
	actor.kelvin_admin
	user := input.request.data[_]
}

## Allow any user to retrieve information about herself
#users {
#	input.request.method == "GET"
#	input.request.path[1] == actor.username
#}
#
## Allow any user to reset his or her own password
#users {
#	input.request.method == "PATCH"
#	input.request.data.password
#	count(input.request.data) == 1
#	input.target.username == actor.username
#}
#
## This rule allows the subject to reset the password of any user if they share at least one school
## and the subject has a role in that school that contains the capability password_reset_$ROLENAME
## where $ROLENAME is a role the listed user has in the shared school.
#users {
#	input.request.method == "PATCH"
#	input.request.data.password
#	count(input.request.data) == 1
#	target_school := input.target.schools[_]
#	actor_school := actor.schools[_]
#	role_capability_mapping[role_name]
#
#	target_school == actor_school
#	has_capability_in_school(actor, sprintf("password_reset_%v", [role_name]), actor_school)
#	has_role_in_school(input.target, role_name, target_school)
#}
#
## This rule returns the usernames of all users the subject shares at least one school with
## and the subject has a role in that school that contains the capability list_$ROLENAME
## where $ROLENAME is a role the listed user has in the shared school.
##
## This rule expects a list of objects to be supplied in the input.object
#allowed_users_list[user.username] {
#	# Vardefs
#	user := input.request.data[_]
#	user_school := user.schools[_]
#	actor_school := actor.schools[_]
#	role_capability_mapping[role_name]
#
#	# Constraints
#	user_school == actor_school
#	has_capability_in_school(actor, sprintf("list_%v", [role_name]), actor_school)
#	has_role_in_school(user, role_name, user_school)
#}
#
## This rule ensures that the actor itself is always part of the listing,
## if he is included in request.data
#allowed_users_list[user.username] {
#	user := input.request.data[_]
#	actor.username == user.username
#}

actor := token.payload.sub

# Helper to get the token payload.
token = {"payload": payload} {
	[header, payload, signature] := io.jwt.decode(input.token)
}

# Is True if the given user has any role in the given school that contains the specified capability
has_capability_in_school(user, capability, school) {
	role_parts := split(user.roles[_], ":")
	role_parts[1] == "school"
	role_parts[2] == school
	role_capability_mapping[role_parts[0]][_] == capability
}

# Is True if the given user has the given role in the specified school
has_role_in_school(user, role, school) {
	role_parts := split(user.roles[_], ":")
	role_parts[0] == role
	role_parts[1] == "school"
	role_parts[2] == school
}

# Until dynamic roles are a thing we need to save the capabilities of roles somewhere, to prevent
# hard coding permissions directly to our roles again. Mapping from ucsschool roles to capabilities
role_capability_mapping := {
	"school_admin": [
		"list_teacher", "list_staff", "list_student", "list_school_admin",
		"password_reset_teacher", "password_reset_student",
	],
	"staff": ["list_teacher", "list_student"],
	"teacher": ["list_student", "password_reset_student"],
	"student": [],
}
