package ucsschool.kelvin

demo_user := {
	"username": "demo_user",
	"kelvin_admin": false,
	"roles": [
		"teacher:school:demo1",
		"student:school:demo2",
		"school_admin:school:demo1",
	],
	"schools": ["demo1", "demo2"],
}

demo_teacher := {
	"username": "demo_teacher",
	"kelvin_admin": false,
	"roles": ["teacher:school:demo1"],
	"schools": ["demo1"],
}

test_has_role_in_school {
	has_role_in_school(demo_user, "teacher", "demo1")
	not has_role_in_school(demo_user, "student", "demo1")
}

test_has_capability_in_school {
	has_capability_in_school(demo_user, "list_student", "demo1")
	not has_capability_in_school(demo_user, "list_teacher", "demo2")
}

test_kelvin_admin_access {
	test_actor_admin := {"kelvin_admin": true}
	test_actor := {"kelvin_admin": false}
	users == true with actor as test_actor_admin
	schools == true with actor as test_actor_admin
	classes == true with actor as test_actor_admin
	roles == true with actor as test_actor_admin
	not users == true with actor as test_actor
	not schools == true with actor as test_actor
	not classes == true with actor as test_actor
	not roles == true with actor as test_actor
}

test_list_self {
	valid_request := {
		"method": "GET",
		"path": ["users", "demo_user"],
	}

	invalid_request := {
		"method": "GET",
		"path": ["users", "other_user"],
	}

	users with actor as demo_user with input.request as valid_request
	not users with actor as demo_user with input.request as invalid_request
}

test_pw_reset_self {
	valid_request := {
		"method": "PATCH",
		"data": {"password": "s3cRE1"},
	}

	invalid_request := {
		"method": "PATCH",
		"data": {"password": "s3cRE1", "other_field": "value"},
	}

	users with actor as demo_user with input.request as valid_request with input.target as demo_user
	not users with actor as demo_user with input.request as valid_request
		 with input.target as {"username": "other"}

	not users with actor as demo_user with input.request as invalid_request
		 with input.target as demo_user
}

test_list_filtering {
	request_teacher := {
		"method": "GET",
		"data": [
			{
				"username": "1",
				"schools": ["demo1"],
				"roles": ["student:school:demo1"],
			},
			{
				"username": "2",
				"schools": ["demo2"],
				"roles": ["student:school:demo2"],
			},
			{
				"username": "3",
				"schools": ["demo1"],
				"roles": ["teacher:school:demo1"],
			},
			demo_teacher,
		],
	}

	result := allowed_users_list with actor as demo_teacher with input.request as request_teacher
	result == {"1", "demo_teacher"}
}
