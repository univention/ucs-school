# LUSD import

The LUSD import debian package provides a reader class (`LUSDReader`),
and a configuration which can be used to import a JSON dump. At the time
of writing, the input format expects a format like in the
`example_data/teachers.json` or `example_data/students.json`.
This format is equivalent to the value `personal` or `lernende` attribute
in the specification.

A user import with the `LUSDReader` class and configuration can be run manually like this, provided `school1` exists:

```bash
/usr/share/ucs-school-import/scripts/ucs-school-user-import -v -u student \
-c /usr/share/ucs-school-import-lusd/configs/user_import_lusd_student.json \
-i /usr/share/ucs-school-import-lusd/example_data/students.json --set school=school1
```

```bash
/usr/share/ucs-school-import/scripts/ucs-school-user-import -v -u teacher \
-c /usr/share/ucs-school-import-lusd/configs/user_import_lusd_teacher.json \
-i /usr/share/ucs-school-import-lusd/example_data/teachers.json --set school=school1
```

## LUSD JSON API clarifications

*How do we identify the role of a `teacher`, `staff` or `teacher_and_staff`?*

It is suggested that we can discern teachers from staff users by the existence of classes.
We assume for development until further clarification that the LUSD API only returns `teacher`s.
We might need to add some data filtering into the CLI tool which calls the `ucs-school-user-import`.
