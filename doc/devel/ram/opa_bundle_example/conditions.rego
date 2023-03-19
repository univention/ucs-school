package univention.conditions

import future.keywords.if
import future.keywords.in

# This condition checks if the target has the same school as the actor.
# It also supports the case of object deletion (target_old is null) and
# object creation (target_new is null).
# But for modification it requires that the old and new target have the same
# school.
cap_condition("ucsschool_ucsschool_targetHasSameSchool", condition_data) if {
	condition_data.actor.school == condition_data.target_old.school
	condition_data.actor.school == condition_data.target_new.school
} else if {
	condition_data.target_old == null
	condition_data.actor.school == condition_data.target_new.school
} else if {
	condition_data.target_new == null
	condition_data.actor.school == condition_data.target_old.school
}

# This condition checks if the target has the given role
cap_condition("targetHasRole", condition_data) if {
	condition_data.parameters.role in {e.role |
		e := condition_data.target_old.roles[_]
	}
}
