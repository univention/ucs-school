#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

import importlib
import logging
import sys
from operator import attrgetter

import click
from ldap.filter import escape_filter_chars
from six import iteritems, itervalues

import univention.admin.modules as udm_modules
from ucsschool.lib.models.base import (
    MultipleObjectsError,
    NoObject,
    UnknownModel,
    WrongModel,
    WrongObjectType,
)
from ucsschool.lib.models.school import School
from ucsschool.lib.models.utils import get_stream_handler, ucr
from univention.admin.filter import conjunction, expression, parse, walk
from univention.admin.uexceptions import ldapError, noObject
from univention.admin.uldap import access as LoType, getAdminConnection, position as PoType

try:
    from typing import TYPE_CHECKING, Dict, Iterable, List, NamedTuple, Optional, Set, Tuple, Type

    if TYPE_CHECKING:
        import univention.admin.handlers.simpleLdap
        from ucsschool.lib.models.base import UCSSchoolModel
except ImportError:
    pass


ModuleAndClass = NamedTuple("ModuleAndClass", [("module_name", str), ("class_name", str)])

no_display_attrs = ("$dn$", "objectType", "type", "type_name")
logger = logging.getLogger("ucsschool")
model_classes = {
    "anycomputer": ModuleAndClass("ucsschool.lib.models.computer", "AnyComputer"),
    "anydhcpservice": ModuleAndClass("ucsschool.lib.models.dhcp", "AnyDHCPService"),
    "basicgroup": ModuleAndClass("ucsschool.lib.models.group", "BasicGroup"),
    "basicschoolgroup": ModuleAndClass("ucsschool.lib.models.group", "BasicSchoolGroup"),
    "classshare": ModuleAndClass("ucsschool.lib.models.share", "ClassShare"),
    "computerroom": ModuleAndClass("ucsschool.lib.models.group", "ComputerRoom"),
    "container": ModuleAndClass("ucsschool.lib.models.misc", "Container"),
    "dhcpdnspolicy": ModuleAndClass("ucsschool.lib.models.policy", "DHCPDNSPolicy"),
    "dhcpserver": ModuleAndClass("ucsschool.lib.models.dhcp", "DHCPServer"),
    "dhcpservice": ModuleAndClass("ucsschool.lib.models.dhcp", "DHCPService"),
    "dhcpsubnet": ModuleAndClass("ucsschool.lib.models.dhcp", "DHCPSubnet"),
    "dnsreversezone": ModuleAndClass("ucsschool.lib.models.network", "DNSReverseZone"),
    "examstudent": ModuleAndClass("ucsschool.lib.models.user", "ExamStudent"),
    "group": ModuleAndClass("ucsschool.lib.models.group", "Group"),
    "groupshare": ModuleAndClass("ucsschool.lib.models.share", "GroupShare"),
    "ipcomputer": ModuleAndClass("ucsschool.lib.models.computer", "IPComputer"),
    "maccomputer": ModuleAndClass("ucsschool.lib.models.computer", "MacComputer"),
    "maildomain": ModuleAndClass("ucsschool.lib.models.misc", "MailDomain"),
    "marketplaceshare": ModuleAndClass("ucsschool.lib.models.share", "MarketplaceShare"),
    "network": ModuleAndClass("ucsschool.lib.models.network", "Network"),
    "policy": ModuleAndClass("ucsschool.lib.models.policy", "Policy"),
    "school": ModuleAndClass("ucsschool.lib.models.school", "School"),
    "schooladmin": ModuleAndClass("ucsschool.lib.models.user", "SchoolAdmin"),
    "schoolclass": ModuleAndClass("ucsschool.lib.models.group", "SchoolClass"),
    "schoolcomputer": ModuleAndClass("ucsschool.lib.models.computer", "SchoolComputer"),
    "schooldc": ModuleAndClass("ucsschool.lib.models.computer", "SchoolDC"),
    "schooldcslave": ModuleAndClass("ucsschool.lib.models.computer", "SchoolDCSlave"),
    "schoolgroup": ModuleAndClass("ucsschool.lib.models.group", "SchoolGroup"),
    "staff": ModuleAndClass("ucsschool.lib.models.user", "Staff"),
    "student": ModuleAndClass("ucsschool.lib.models.user", "Student"),
    "teacher": ModuleAndClass("ucsschool.lib.models.user", "Teacher"),
    "teachersandstaff": ModuleAndClass("ucsschool.lib.models.user", "TeachersAndStaff"),
    "ucccomputer": ModuleAndClass("ucsschool.lib.models.computer", "UCCComputer"),
    "umcpolicy": ModuleAndClass("ucsschool.lib.models.policy", "UMCPolicy"),
    "windowscomputer": ModuleAndClass("ucsschool.lib.models.computer", "WindowsComputer"),
    "workgroup": ModuleAndClass("ucsschool.lib.models.group", "WorkGroup"),
    "workgroupshare": ModuleAndClass("ucsschool.lib.models.share", "WorkGroupShare"),
}
if ucr.get("server/role") in ("domaincontroller_master", "domaincontroller_backup"):
    model_classes.update(
        {
            "importstaff": ModuleAndClass("ucsschool.importer.models.import_user", "ImportStaff"),
            "importstudent": ModuleAndClass("ucsschool.importer.models.import_user", "ImportStudent"),
            "importteacher": ModuleAndClass("ucsschool.importer.models.import_user", "ImportTeacher"),
            "importteachersandstaff": ModuleAndClass(
                "ucsschool.importer.models.import_user", "ImportTeachersAndStaff"
            ),
        }
    )


def escape_filter_c(filter_s: str) -> str:
    filter_s = escape_filter_chars(filter_s)
    return filter_s.replace(r"\2a", "*")


def get_ldap_access() -> Tuple[LoType, PoType]:
    return getAdminConnection()


def load_model(model_name: str) -> Type[UCSSchoolModel]:
    try:
        m_c = model_classes[model_name.lower()]
    except KeyError:
        logger.critical("Unkown model %r.", model_name)
        sys.exit(1)
    try:
        mod = importlib.import_module(m_c.module_name)
        return getattr(mod, m_c.class_name)
    except (AttributeError, ImportError, TypeError) as exc:
        logger.critical(
            "Error loading class %r from module %r: %s", m_c.class_name, m_c.module_name, exc
        )
        sys.exit(1)


def get_obj(
    lo: LoType, model_cls: Type[UCSSchoolModel], dn: str, name: str, school: str
) -> UCSSchoolModel:
    try:
        if dn:
            return model_cls.from_dn(dn, None, lo)
        elif name and school:
            name_udm_prop = model_cls._attributes["name"].udm_name
            objs = model_cls.get_all(
                lo, school=school, filter_str=escape_filter_c("{}={}".format(name_udm_prop, name))
            )
            if len(objs) == 1:
                return objs[0]
            elif len(objs) > 1:
                raise MultipleObjectsError(
                    "Found more than one {!r} object with school={!r} and name={!r}.".format(
                        model_cls.__name__, school, name
                    )
                )
            else:
                raise NoObject(
                    "No {!r} object with school={!r} and name={!r} found.".format(
                        model_cls.__name__, school, name
                    )
                )
        else:
            logger.critical("Either '--dn' or '--name' AND '--school' is required.")
            sys.exit(1)
    except (
        ldapError,
        MultipleObjectsError,
        NoObject,
        noObject,
        UnknownModel,
        WrongModel,
        WrongObjectType,
    ) as exc:
        if dn:
            args_str = "DN {!r}".format(dn)
        else:
            args_str = "name {!r} and school {!r}".format(name, school)
        logger.critical("Error loading object of type %r with %s: %s", model_cls.__name__, args_str, exc)
        sys.exit(1)


def print_object(obj: UCSSchoolModel, print_attrs: str = None) -> None:
    attrs = sorted(set(obj.to_dict().keys()) - set(no_display_attrs))
    if print_attrs:
        p_a = print_attrs.split(",")
        attrs = [a for a in attrs if a in p_a]
    obj_repr = obj.to_dict()
    msg = "{}{}{}".format(
        obj,
        "\n  dn: {!r}".format(obj.dn) if not attrs or "dn" in attrs else "",
        "\n  {}".format("\n  ".join("{}: {!r}".format(k, obj_repr[k]) for k in attrs)),
    )
    logger.info(msg)


@click.group(help="Experimental and unsupported tool for UCS@school object manipulation.")
@click.option("--debug/--no-debug", help="Enable DEBUG level output from ucsschool.lib.", default=False)
@click.pass_context
def cli(ctx: click.core.Context, debug: bool) -> None:
    ctx.obj["DEBUG"] = debug
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    logger.addHandler(get_stream_handler(level=level, stream=sys.stdout))
    if not debug:
        # to much noise in school lib at INFO level
        logging.getLogger("ucsschool.lib.models").setLevel(logging.WARNING)


@cli.command(help="Create a new object.")
@click.argument("model")
# Name and school should actually be 'click.argument' as they are required,
# but modify and delete have them as options, so the interface will be more
# homogeneous with them being options here as well.
@click.option("--name", help="Name of object to modify.", required=True)
@click.option("--school", help="School (OU) of object to modify.", required=True)
@click.option(
    "--append",
    "multi_value",
    help="Set a multi-value attribute to a value: '--append <attr> <value>' (can be used multiple"
    " times).",
    type=(str, str),
    multiple=True,
)
@click.option(
    "--set",
    "single_value",
    help="Set a single-value attribute to a value: '--set <attr> <value>' (can be used multiple times).",
    type=(str, str),
    multiple=True,
)
def create(
    model: str,
    name: str,
    school: str,
    multi_value: Iterable[Tuple[str, str]],
    single_value: Iterable[Tuple[str, str]],
) -> None:
    logger.debug(
        "create: model=%r name=%r school=%r multi_value=%r single_value=%r",
        model,
        name,
        school,
        multi_value,
        single_value,
    )
    model_cls = load_model(model)
    obj = model_cls(name=name, school=school)
    for k, v in single_value:
        if k not in model_cls._attributes:
            logger.critical("Unknown attribute %r for model %r.", k, model_cls.__name__)
            sys.exit(1)
        setattr(obj, k, v)
    to_append: Dict[str, Set[str]] = {}
    for k, v in multi_value:
        if k not in model_cls._attributes:
            logger.critical("Unknown attribute %r for model %r.", k, model_cls.__name__)
            sys.exit(1)
        if k == "ucsschool_roles":
            logger.warning("Setting 'ucsschool_roles' manually is not recommended.")
        to_append.setdefault(k, set()).add(v)
    for k, v in iteritems(to_append):
        setattr(obj, k, list(v))
    lo, _ = get_ldap_access()
    if obj.exists(lo):
        logger.critical(
            "Object of type %r with school=%r and name=%r exists.", model_cls.__name__, school, name
        )
        sys.exit(1)
    success = obj.create(lo)
    sys.exit(0 if success else 1)


@cli.command(help="Modify an existing object. Either '--dn' or '--name' AND '--school' is required.")
@click.argument("model")
@click.option("--dn", help="DN of object to modify.")
@click.option("--name", help="Name of object to modify.")
@click.option("--school", help="School (OU) of object to modify.")
@click.option(
    "--append",
    "multi_value",
    help="Set a multi-value attribute to a value: '--append <attr> <value>' (can be used multiple"
    " times).",
    type=(str, str),
    multiple=True,
)
@click.option(
    "--set",
    "single_value",
    help="Set a single-value attribute to a value: '--set <attr> <value>' (can be used multiple times).",
    type=(str, str),
    multiple=True,
)
@click.option(
    "--remove",
    "rm_value",
    help="Remove a value from a multi-value attribute: '--remove <attr> <value>' (can be used multiple"
    " times).",
    type=(str, str),
    multiple=True,
)
def modify(
    model: str,
    dn: str,
    name: str,
    school: str,
    multi_value: Iterable[Tuple[str, str]],
    single_value: Iterable[Tuple[str, str]],
    rm_value: Iterable[Tuple[str, str]],
) -> None:
    # noqa: E501
    logger.debug(
        "modify: model=%r dn=%r name=%r school=%r multi_value=%r single_value=%r rm_value=%r",
        model,
        dn,
        name,
        school,
        multi_value,
        single_value,
        rm_value,
    )
    model_cls = load_model(model)
    lo, _ = get_ldap_access()
    obj = get_obj(lo, model_cls, dn, name, school)
    for k, v in single_value:
        if k not in model_cls._attributes:
            logger.critical("Unknown attribute %r for model %r.", k, model_cls.__name__)
            sys.exit(1)
        setattr(obj, k, v)
    to_append: Dict[str, Set[str]] = {}
    for k, v in multi_value:
        if k not in model_cls._attributes:
            logger.critical("Unknown attribute %r for model %r.", k, model_cls.__name__)
            sys.exit(1)
        if k == "ucsschool_roles":
            logger.warning("Changing 'ucsschool_roles' manually is not recommended.")
        to_append.setdefault(k, set()).add(v)
    for k, v in iteritems(to_append):
        attr = getattr(obj, k)
        attr.extend(v)  # no problem if the value already exists, UDM handles it
    to_remove: Dict[str, Set[str]] = {}
    for k, v in rm_value:
        if k not in model_cls._attributes:
            logger.critical("Unknown attribute %r for model %r.", k, model_cls.__name__)
            sys.exit(1)
        if k == "ucsschool_roles":
            logger.warning("Changing 'ucsschool_roles' manually is not recommended.")
        to_remove.setdefault(k, set()).add(v)
    for k, v in iteritems(to_remove):
        attr = getattr(obj, k)
        for val in v:
            try:
                attr.remove(val)
            except ValueError:
                logger.warning(
                    "Value %r doesn't exist in objects attribute %r and was thus not removed.", val, k
                )
    success = obj.modify(lo)
    sys.exit(0 if success else 1)


@cli.command(help="Delete an existing object. Either '--dn' or '--name' AND '--school' is required.")
@click.argument("model")
@click.option("--dn", help="DN of object to delete.")
@click.option("--name", help="Name of object to delete.")
@click.option("--school", help="School (OU) of object to delete.")
def delete(model: str, dn: str, name: str, school: str) -> None:
    logger.debug("delete: model=%r dn=%r name=%r school=%r", model, dn, name, school)
    model_cls = load_model(model)
    lo, _ = get_ldap_access()
    obj = get_obj(lo, model_cls, dn, name, school)
    obj.remove(lo)


@cli.command(
    "list", help="List/show existing object(s). Use '*' in attribute values like in LDAP filters."
)
@click.argument("model")
@click.option("--dn", help="DN of object to show. Cannot be used together with other options.")
@click.option("--name", help="Name of object(s) to list.")
@click.option("--school", help="School (OU) of object(s) to list.")
@click.option(
    "--attr",
    "attr_filters",
    help="Search for object(s) with the attribute set to the value: '--attr <attr> <value>' (can be used"
    " multiple times).",
    type=(str, str),
    multiple=True,
)
@click.option(
    "--filter",
    "filter_str",
    help="LDAP/UDM filter to use for searching. Can be used together with '--school' as a search "
    "base, but no other options are allowed.",
)
@click.option(
    "--print-attrs",
    help="Print only the listed attributes (comma separated): '--print-attrs' 'dn,name,firstname'",
)
@click.pass_context
def list_objs(
    ctx: click.core.Context,
    model: str,
    dn: str,
    name: str,
    school: str,
    attr_filters: Iterable[Tuple[str, str]],
    filter_str: str,
    print_attrs: str,
) -> None:
    logger.debug(
        "list: model=%r dn=%r name=%r school=%r attr_filter=%r filter_str=%r print_attrs=%r",
        model,
        dn,
        name,
        school,
        attr_filters,
        filter_str,
        print_attrs,
    )

    def check_school(lo: LoType, school: str) -> str:
        if not School(name=school).exists(lo):
            logger.critical("Unknown school %r.", school)
            sys.exit(1)
        ou_obj = lo.get("ou={},{}".format(school, ucr["ldap/base"]))
        return ou_obj["ou"][0]

    def udm_filter_from_school_filter(filter_str: str) -> str:
        def replace_school_attr_with_udm_prop(expr: expression, arg: Dict[str, str]) -> None:
            try:
                udm_prop_name = model_cls._attributes[expr.variable].udm_name
            except KeyError:
                return
            old_expr_str = str(expr)
            new_expr_str = str(expression(udm_prop_name, expr.value))
            filter_s = arg.pop("filter_str")  # just replacing the old value didn't work
            arg["filter_str"] = filter_s.replace(old_expr_str, new_expr_str)

        if not filter_str:
            return filter_str

        # Using UDM for LDAP searches, we have to replace school attribute
        # names with UDM property names.
        tree = parse(filter_str)
        # walk() has no return value, so we pass a mutable object
        arg = {"filter_str": filter_str}
        walk(tree, expression_walk_function=replace_school_attr_with_udm_prop, arg=arg)
        return arg["filter_str"]

    def get_and_print_with_school(
        lo: LoType, model_cls: Type[UCSSchoolModel], school: str, filter_str: str
    ) -> None:
        filter_str = udm_filter_from_school_filter(filter_str)
        objs = model_cls.get_all(lo, school=school, filter_str=filter_str)
        if not objs:
            logger.warning("No objects found.")
        else:
            for obj in objs:
                print_object(obj, print_attrs)

    def get_and_print_without_school(
        lo: LoType, model_cls: Type[UCSSchoolModel], base: str = "", filter_str: str = ""
    ) -> None:

        filter_str = udm_filter_from_school_filter(filter_str)
        model_cls.init_udm_module(lo)
        try:
            udm_objs: List[univention.admin.handlers.simpleLdap] = udm_modules.lookup(
                module_name=model_cls._meta.udm_module,
                co=None,
                lo=lo,
                base=base,
                filter=filter_str,
                scope="sub",
            )
        except noObject:
            logger.warning("No objects found.")
            sys.exit(0)
        udm_objs.sort(key=attrgetter("dn"))
        if not ctx.obj["DEBUG"]:
            # result may include lots of non-school objects -> suppress log message at WARNING level:
            # "does not correspond to a Python class in the UCS school lib."
            logging.getLogger("ucsschool.lib.models").setLevel(logging.ERROR)
        for udm_obj in udm_objs:
            school = model_cls.get_school_from_dn(udm_obj.dn)
            try:
                obj = model_cls.from_udm_obj(udm_obj, school, lo)
            except (UnknownModel, WrongModel):
                continue
            print_object(obj, print_attrs)

    def get_and_print(
        lo: LoType,
        model_cls: Type[UCSSchoolModel],
        school: str = "",
        base: str = "",
        filter_str: str = "",
    ) -> None:
        if school:
            school = check_school(lo, school)
            get_and_print_with_school(lo, model_cls, school, filter_str)
        else:
            if getattr(model_cls, "type_filter", None):
                filter_str = str(conjunction("&", [parse(model_cls.type_filter), parse(filter_str)]))
            get_and_print_without_school(lo, model_cls, base=base, filter_str=filter_str)

    model_cls = load_model(model)
    lo, _ = get_ldap_access()
    if dn:
        if name or school or attr_filters or filter_str:
            logger.critical("Option '--dn' must not be used together with other options.")
            sys.exit(1)
        obj = get_obj(lo, model_cls, dn, name, school)
        print_object(obj, print_attrs)
    elif filter_str:
        if dn or name or attr_filters:
            logger.critical(
                "Option '--filter' must not be used together with other options except '--school'."
            )
            sys.exit(1)
        get_and_print(lo, model_cls, school=school, base="", filter_str=filter_str)
    else:
        # Use name, school, attr_filters to find objects.
        complete_filter = model_cls._meta.udm_filter
        if complete_filter and not complete_filter.startswith("("):
            complete_filter = "({})".format(complete_filter)
        if name:
            # 'name' will be translated to UDM property in udm_filter_from_school_filter()
            # called by get_and_print_with*_school() called by get_and_print()
            name_filter = "(name={})".format(escape_filter_c(name))
            if complete_filter:
                complete_filter = conjunction("&", [parse(complete_filter), parse(name_filter)])
            else:
                complete_filter = name_filter
        for k, v in attr_filters:
            # k will be translated to UDM property in udm_filter_from_school_filter() ...
            filter_s = "({}={})".format(k, escape_filter_c(v))
            if complete_filter:
                complete_filter = conjunction("&", [parse(complete_filter), parse(filter_s)])
            else:
                complete_filter = filter_s
        complete_filter = str(complete_filter)
        get_and_print(lo, model_cls, school=school, base="", filter_str=complete_filter)
    sys.exit(0)


@cli.command("list-models", help="List known models.")
@click.option("--attributes", "-a", help="List attributes for each model.", is_flag=True)
def list_models(attributes: bool) -> None:
    # logger.info("\n".join(sorted(m_c.class_name for m_c in itervalues(model_classes))))
    for class_name in sorted(m_c.class_name for m_c in itervalues(model_classes)):
        model_cls = load_model(class_name)
        logger.info(class_name)
        if attributes:
            for attr_name in sorted(model_cls._attributes.keys()):
                logger.info(
                    "    %s%s",
                    attr_name,
                    " [required]" if model_cls._attributes[attr_name].required else "",
                )


if __name__ == "__main__":
    cli(obj={})
