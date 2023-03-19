package univention.utils

import future.keywords.every
import future.keywords.in

import data.univention.mapping.role_capability_mapping

###############
# merge_dicts #
###############

test_merge_dicts {
	merge_dicts({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
	merge_dicts({"a": 1}, null) == {"a": 1}
	merge_dicts(null, {"a": 1}) == {"a": 1}
	merge_dicts({"a": 1}, {}) == {"a": 1}
	merge_dicts({"a": [1, 2]}, {}) == {"a": [1, 2]}
	merge_dicts({"a": {"a": 1, "b": 2}}, {}) == {"a": {"a": 1, "b": 2}}
}

#######################
# evaluate_conditions #
#######################

test_evaluate_conditions {
	evaluate_conditions("OR", [], {})
	evaluate_conditions("AND", [], {})
	not evaluate_conditions("AND", ["notExists"], {})
	not evaluate_conditions("OR", ["notExists"], {})
}

#########################
# get_role_capabilities #
#########################

test_get_role_capabilies {
	get_role_capabilities(
		"ucsschool:ucsschool:teacher",
		"ucsschool",
		"ucsschool",
	) == {
		{"permissions": ["read:firstName", "read:lastName"], "conditions": [], "relation": "AND"},
		{"permissions": ["read:firstName", "write:password", "export"], "conditions": [{"data": {}, "name": "ucsschool_ucsschool_targetHasSameSchool"}, {"data": {"role": "ucsschool:ucsschool:student"}, "name": "targetHasRole"}], "relation": "AND"},
	}
	get_role_capabilities(
		"ucsschool:ucsschool:teacher",
		"OX",
		"mail",
	) == {{"permissions": ["editSpamFilter", "export"], "conditions": [], "relation": "AND"}}
}

###################
# get_permissions #
###################

test_get_permissions {
	get_permissions(
		{
			"roles": [{"role": "ucsschool:ucsschool:teacher", "context": "school1"}],
			"name": "teacher1",
			"school": "school1",
		},
		{
			"roles": [{"role": "ucsschool:ucsschool:teacher", "context": "school1"}],
			"name": "teacher1",
			"school": "school1",
		},
		"ucsschool",
		"ucsschool",
		{},
	) == {"read:firstName", "read:lastName"}

	get_permissions(
		{
			"roles": [{"role": "ucsschool:ucsschool:teacher", "context": "school1"}],
			"name": "teacher1",
			"school": "school1",
		},
		{
			"roles": [{"role": "ucsschool:ucsschool:student", "context": "school1"}],
			"name": "student1",
			"school": "school1",
		},
		"ucsschool",
		"ucsschool",
		{},
	) == {"export", "read:firstName", "read:lastName", "write:password"}

	get_permissions(
		{
			"roles": [{"role": "ucsschool:ucsschool:teacher", "context": "school1"}],
			"name": "teacher1",
			"school": "school1",
		},
		{
			"roles": [{"role": "ucsschool:ucsschool:student", "context": "school1"}],
			"name": "student1",
			"school": "school1",
		},
		"OX",
		"mail",
		{},
	) == {"editSpamFilter", "export"}
}
