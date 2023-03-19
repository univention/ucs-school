package univention.utils

import future.keywords.every
import future.keywords.if
import future.keywords.in

import data.mapping.roleCapabilityMapping
import data.univention.conditions.cap_condition

# Merge two dictionaries.
#
# Parameters:
#   a: The first dictionary.
#   b: The second dictionary.
# Returns (dict): The merged dictionary.
merge_dicts(a, b) := {key: value |
	some d in {a, b}
	value := d[key]
}

evaluate_conditions("AND", conditions, condition_data) if {
	every condition in conditions {
		cap_condition(condition.name, merge_dicts(condition_data, condition.data))
	}
}

evaluate_conditions("OR", conditions, condition_data) if {
	some condition in conditions
	cap_condition(condition.name, merge_dicts(condition_data, condition.data))
}

evaluate_conditions("OR", conditions, condition_data) if {
	conditions == []
}

# This function returns a list of capabilities of a role for an app and
# namespace.
#
# Parameters:
#   role: The role to get the capabilities for.
#   app_id: The app to get the capabilities for.
#   namespace: The namespace to get the capabilities for.
# Returns (list): A list of capabilities.
get_role_capabilities(role, appId, namespace) := capabilities if {
	capabilities := {capability |
		element := data.mapping.roleCapabilityMapping[role][_]
		element.appId == appId
		element.namespace == namespace
		capability := element.capabilities[_]
	}
}

# Return the permissions that an actor can perform on a target.
#
# Parameters:
#   actor: The actor to get the capabilities for.
#   target: The target.
#   appId: The app that requests the information.
#   namespace: The namespace of the app.
#   additional_data: Additional data for the conditions.
# Returns (set): A set of permissions.
get_permissions(actor, target, appId, namespace, additional_data) := permissions if {
	permissions := {action |
		role := actor.roles[_]
		capability := get_role_capabilities(role.role, appId, namespace)[_]
		evaluate_conditions(capability.relation, capability.conditions, {"actor": actor, "target_old": target, "target_new": target, "additional_data": additional_data})
		action := capability.permissions[_]
	}
}
