package univention.conditions

import future.keywords.if

# Test the targetHasSameSchool condition
test_target_has_same_school if {
	cap_condition(
		"ucsschool_ucsschool_targetHasSameSchool",
		{
			"actor": {
				"name": "teacher1",
				"school": "school1",
				"roles": [{"role": "ucsschool:ucsschool:teacher", "context": "school1"}],
			},
			"target_old": {
				"name": "student1",
				"school": "school1",
				"roles": [{"role": "ucsschool:ucsschool:student", "context": "school1"}],
			},
			"target_new": null,
			"additional_data": [],
		},
	)
	not cap_condition(
		"ucsschool_ucsschool_targetHasSameSchool",
		{
			"actor": {
				"name": "teacher1",
				"school": "school1",
				"roles": [{"role": "ucsschool:ucsschool:teacher", "context": "school1"}],
			},
			"target_old": {
				"name": "student1",
				"school": "school2",
				"roles": [{"role": "ucsschool:ucsschool:student", "context": "school2"}],
			},
			"target_new": null,
			"additional_data": null,
		},
	)
}

# Test the targetHasRole condition
test_target_has_role if {
	cap_condition(
		"targetHasRole",
		{
			"actor": {
				"name": "student1",
				"school": "school1",
				"roles": [{"role": "ucsschool:ucsschool:student", "context": "school1"}],
			},
			"target_old": {
				"name": "student1",
				"school": "school1",
				"roles": [{"role": "ucsschool:ucsschool:student", "context": "school1"}],
			},
			"target_new": null,
			"additional_data": null,
			"role": "ucsschool:ucsschool:student",
		},
	)
	not cap_condition(
		"targetHasRole",
		{
			"actor": {
				"name": "student1",
				"school": "school1",
				"roles": [{"role": "ucsschool:ucsschool:student", "context": "school1"}],
			},
			"target_old": null,
			"target_new": null,
			"additional_data": null,
			"role": "ucsschool:ucsschool:student",
		},
	)
}
