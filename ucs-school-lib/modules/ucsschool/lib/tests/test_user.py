from ucsschool.lib.models.user import ExamStudent, Staff, Student, Teacher, TeachersAndStaff, User


def test_read_user(new_user_via_ssh, lo_udm, remove_user_via_ssh):
	print("** new_user_via_ssh={!r}\n".format(new_user_via_ssh))
	dn, attr = new_user_via_ssh
	user_cls = attr.pop("user_cls")
	print(f"** user_cls={user_cls!r}")
	user = User.from_dn(dn, "DEMOSCHOOL", lo_udm)
	print("** type(user)=%r user.to_dict()={!r}".format(type(user), user.to_dict()))
	assert user.__class__.__name__ == user_cls
	try:
		for k, v in attr.items():
			val1 = v
			val2 = getattr(user, k)
			if isinstance(v, list):
				val1 = set(val1)
				val2 = set(val2)
			assert val1 == val2, "k={!r} v={!r} getattr(user, k)={!r}".format(k, v, getattr(user, k))
		print("** OK, deleting user...")
	finally:
		result, returncode = remove_user_via_ssh(dn)
		assert returncode == 0
	assert not User(**attr).exists(lo_udm)


def test_create_user(user_attrs, lo_udm, scp_code, get_user_via_ssh, remove_user_via_ssh):
	user_cls = user_attrs.pop("user_cls")
	print(f"** user_cls={user_cls!r}")
	cls = globals()[user_cls]
	print(f"** cls={cls!r}")
	user = cls(**user_attrs)
	print("** type(user)=%r user.to_dict()={!r}".format(type(user), user.to_dict()))
	user.create(lo_udm)
	result, returncode = get_user_via_ssh(user.dn)
	print("** result={!r} returncode={!r}".format(result, returncode))
	assert isinstance(result, dict)
	try:
		for k, value_here in user.to_dict().items():
			val_here = value_here
			val_ssh = result.get(k)
			if k == "disabled" and isinstance(val_ssh, str):
				val_ssh = bool(int(val_ssh))
			if isinstance(val_here, list):
				val_here = set(val_here)
				val_ssh = set(val_ssh)
			assert val_here == val_ssh, f"k={k!r} val_here={val_here!r} val_ssh={val_ssh!r}"
		print("** OK, deleting user...")
	finally:
		result, returncode = remove_user_via_ssh(user.dn)
		assert returncode == 0
	assert not User(**user_attrs).exists(lo_udm)


def test_remove_user(new_user_via_ssh, lo_udm, user_exists_via_ssh):
	print("** new_user_via_ssh={!r}\n".format(new_user_via_ssh))
	dn, attr = new_user_via_ssh
	user = User.from_dn(dn, "DEMOSCHOOL", lo_udm)
	dn = user.dn
	print("** user.dn={!r}".format(user.dn))
	user.remove(lo_udm)
	result, returncode = user_exists_via_ssh(dn)
	print("** result={!r} returncode={!r}".format(result, returncode))
	assert result is False
	assert not User(**attr).exists(lo_udm)
