import sys

import pytest

sys.path.insert(1, "modules")
from ucsschool.lib.roles import (  # noqa: E402
    UnknownRole,
    all_context_types,
    all_roles,
    create_ucsschool_role_string,
)


class TestCreateUcsschoolRoleString:
    """Tests for roles.create_ucsschool_role_string"""

    @pytest.mark.parametrize("role", all_roles)
    def test_default_values(self, role):
        context = "some-context"
        expected = ":".join([role, "school", context])
        assert expected == create_ucsschool_role_string(role, context)

    @pytest.mark.parametrize("role", all_roles)
    def test_default_values_uses_school_instead_of_context(self, role):
        context = "some-context"
        school = "Some School"
        expected = ":".join([role, "school", school])
        assert expected == create_ucsschool_role_string(
            role,
            context,
            school=school,
        )

    def test_default_values_unknown_role_raises_error(self):
        role = "foobar"
        context = "some-context"
        try:
            create_ucsschool_role_string(role, context)
            assert False, "No error raised for invalid role"
        except UnknownRole:
            pass

    def test_default_context_unknown_role_with_school_raises_error(self):
        role = "foobar"
        context = "some-context"
        school = "Some School"
        try:
            create_ucsschool_role_string(
                role,
                context,
                school=school,
            )
            assert False, "No error raised for invalid role, when school present"
        except UnknownRole:
            pass

    @pytest.mark.parametrize("context_type", all_context_types)
    @pytest.mark.parametrize("role", all_roles)
    def test_context_type_supplied(self, role, context_type):
        context = "some-context"
        expected = ":".join([role, context_type, context])
        assert expected == create_ucsschool_role_string(
            role,
            context,
            context_type=context_type,
        )

    @pytest.mark.parametrize("context_type", all_context_types)
    @pytest.mark.parametrize("role", all_roles)
    def test_context_type_supplied_uses_school_instead_of_context(self, role, context_type):
        context = "some-context"
        school = "Some School"
        expected = ":".join([role, context_type, school])
        assert expected == create_ucsschool_role_string(
            role,
            context,
            context_type=context_type,
            school=school,
        )

    @pytest.mark.parametrize("context_type", all_context_types)
    def test_context_type_supplied_raises_error_for_unknown_role(self, context_type):
        role = "foobar"
        context = "some-context"
        try:
            create_ucsschool_role_string(
                role,
                context,
                context_type=context_type,
            )
            assert False, "No error raised for invalid role when context_type provided"
        except UnknownRole:
            pass

    @pytest.mark.parametrize("context_type", all_context_types)
    def test_context_type_supplied_raises_error_for_unknown_role_and_school(self, context_type):
        role = "foobar"
        context = "some-context"
        school = "Some School"
        try:
            create_ucsschool_role_string(
                role,
                context,
                context_type=context_type,
                school=school,
            )
        except UnknownRole:
            pass

    def test_unknown_context_type_doesnt_check_role(self):
        role = "foobar"
        context = "some-context"
        context_type = "foobar"
        expected = ":".join([role, context_type, context])
        assert expected == create_ucsschool_role_string(
            role,
            context,
            context_type=context_type,
        )

    @pytest.mark.parametrize("role", all_roles)
    def test_unknown_context_type_doesnt_use_school(self, role):
        context = "some-context"
        school = "Some School"
        context_type = "foobar"
        expected = ":".join([role, context_type, context])
        assert expected == create_ucsschool_role_string(
            role,
            context,
            context_type=context_type,
            school=school,
        )

    @pytest.mark.parametrize("role", all_roles)
    def test_context_with_colons_is_replaced_by_ampersands(self, role):
        context = "foo:bar:baz:buz"
        expected = ":".join([role, "school", "foo&&&bar&&&baz&&&buz"])
        assert expected == create_ucsschool_role_string(role, context)

    @pytest.mark.parametrize("role", all_roles)
    def test_school_context_with_colons_is_replaced_by_ampersands(self, role):
        context = "foobar"
        school = "foo:bar:baz:buz"
        expected = ":".join([role, "school", "foo&&&bar&&&baz&&&buz"])
        assert expected == create_ucsschool_role_string(
            role,
            context,
            school=school,
        )
