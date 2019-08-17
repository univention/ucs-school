from ucsschool.lib.models.group import SchoolClass


def test_read_school_class(new_school_class_via_ssh, lo_udm, remove_class_via_ssh):
	print("** new_school_class_via_ssh={!r}\n".format(new_school_class_via_ssh))
	dn, attr = new_school_class_via_ssh
	sc = SchoolClass.from_dn(dn, "DEMOSCHOOL", lo_udm)
	print("** sc.to_dict()={!r}".format(sc.to_dict()))
	try:
		for k, v in attr.items():
			val1 = v
			val2 = getattr(sc, k)
			if isinstance(v, list):
				val1 = set(val1)
				val2 = set(val2)
			assert val1 == val2, "k={!r} v={!r} getattr(sc, k)={!r}".format(k, v, getattr(sc, k))
		print("** OK, deleting class...")
	finally:
		result, returncode = remove_class_via_ssh(dn)
		assert returncode == 0
	assert not SchoolClass(**attr).exists(lo_udm)


def test_create_school_class(school_class_attrs, lo_udm, scp_code, get_school_class_via_ssh, remove_class_via_ssh):
	sc = SchoolClass(**school_class_attrs)
	print("** sc.to_dict()={!r}".format(sc.to_dict()))
	sc.create(lo_udm)
	result, returncode = get_school_class_via_ssh(sc.dn)
	print("** result={!r} returncode={!r}".format(result, returncode))
	assert isinstance(result, dict)
	try:
		for k, value_here in sc.to_dict().items():
			val_here = value_here
			val_ssh = result.get(k)
			if isinstance(val_here, list):
				val_here = set(val_here)
				val_ssh = set(val_ssh)
			assert val_here == val_ssh, f"k={k!r} val_here={val_here!r} val_ssh={val_ssh!r}"
		print("** OK, deleting class...")
	finally:
		result, returncode = remove_class_via_ssh(sc.dn)
		assert returncode == 0
	assert not SchoolClass(**school_class_attrs).exists(lo_udm)


def test_remove_school_class(new_school_class_via_ssh, lo_udm, school_class_exists_via_ssh):
	print("** new_school_class_via_ssh={!r}\n".format(new_school_class_via_ssh))
	dn, attr = new_school_class_via_ssh
	sc = SchoolClass.from_dn(dn, "DEMOSCHOOL", lo_udm)
	dn = sc.dn
	print("** sc.dn={!r}".format(sc.dn))
	sc.remove(lo_udm)
	result, returncode = school_class_exists_via_ssh(dn)
	print("** result={!r} returncode={!r}".format(result, returncode))
	assert result is False
	assert not SchoolClass(**attr).exists(lo_udm)
