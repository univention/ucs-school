import copy
import importlib
import os
import tempfile
from typing import Any, Dict, Tuple

import pytest
from faker import Faker
from ldap.dn import explode_dn

from ucsschool.lib.models.base import PYHOOKS_PATH, _pyhook_loader
from ucsschool.lib.models.dhcp import DHCPService
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.share import MarketplaceShare
from udm_rest_client import UDM

HOOK_TEXT = """
# -*- coding: utf-8 -*-
from ucsschool.lib.models.hook import Hook
IMPORT_VAR  # noqa: F821

print("*********** HOOK **********")
print(f"*** __file__={__file__!r}")
print("*** IMPORT_VAr=IMPORT_VAR")
print("*** TARGET_FILE_VAr=TARGET_FILE_VAR")
print("*** MODEL_CLASS_VAr=MODEL_CLASS_VAR")
print("*** HOOK_METHOd=HOOK_METHOD")
print("***************************")

class TestHook(Hook):
    model = MODEL_CLASS_VAR  # noqa: F821
    priority = {"HOOK_METHOD": 1}

    async def HOOK_METHOD(self, obj):
        print(f"*********** HOOK_METHOD() self.model={self.model!r} obj={obj!r}")
        msg = f"HOOK_METHOD {obj.__class__.__name__} {obj.name} {obj.school}"
        self.logger.debug("Writing %r to %r...", msg, "TARGET_FILE_VAR")
        with open("TARGET_FILE_VAR", "a") as fp:
            fp.write(f"{msg}\\n")
"""

CLASSES_MODULES = {
    "AnyDHCPService": "ucsschool.lib.models.dhcp",
    "BasicGroup": "ucsschool.lib.models.group",
    "ClassShare": "ucsschool.lib.models.share",
    "ComputerRoom": "ucsschool.lib.models.group",
    "Container": "ucsschool.lib.models.misc",
    "DHCPDNSPolicy": "ucsschool.lib.models.policy",
    "DHCPServer": "ucsschool.lib.models.dhcp",
    "DHCPService": "ucsschool.lib.models.dhcp",
    # "DHCPSubnet": "ucsschool.lib.models.dhcp",  # Bug in UDM REST API or Client?: (*1)
    # "DNSReverseZone": "ucsschool.lib.models.network",  # Bug in UDM REST API: (*2)
    "ExamStudent": "ucsschool.lib.models.user",
    "Group": "ucsschool.lib.models.group",
    "GroupShare": "ucsschool.lib.models.share",
    # "IPComputer": "ucsschool.lib.models.computer",  # Bug in UDM REST API: (*2)
    # "MacComputer": "ucsschool.lib.models.computer",  # Bug in UDM REST API: (*2)
    "MailDomain": "ucsschool.lib.models.misc",
    "MarketplaceShare": "ucsschool.lib.models.share",
    # "Network": "ucsschool.lib.models.network",  # Bug in UDM REST API:
    "OU": "ucsschool.lib.models.misc",
    "School": "ucsschool.lib.models.school",
    "SchoolAdmin": "ucsschool.lib.models.user",
    "SchoolClass": "ucsschool.lib.models.group",
    "SchoolDCSlave": "ucsschool.lib.models.computer",
    "SchoolGroup": "ucsschool.lib.models.group",
    "Staff": "ucsschool.lib.models.user",
    "Student": "ucsschool.lib.models.user",
    "Teacher": "ucsschool.lib.models.user",
    "TeachersAndStaff": "ucsschool.lib.models.user",
    "UMCPolicy": "ucsschool.lib.models.policy",
    # "WindowsComputer": "ucsschool.lib.models.computer",  # Bug in UDM REST API: (*2)
    "WorkGroup": "ucsschool.lib.models.group",
    "WorkGroupShare": "ucsschool.lib.models.share",
}
#
# (*1) Uncaught exception PUT /udm/dhcp/subnet/cn=april86d,cn=dhcp,ou=... -> why PUT, should be POST?
# (*2) IndexError in GET /udm/dns/reverse_zone/add
#
CLASSES_WITH_SCHOOL_NONE = ("AnyDHCPService", "BasicGroup", "MailDomain", "DNSReverseZone", "School")

MODIFY_MODULES = copy.deepcopy(CLASSES_MODULES)
del MODIFY_MODULES["Container"]  # (*1)
del MODIFY_MODULES["OU"]  # (*1)
del MODIFY_MODULES["DHCPDNSPolicy"]  # (*2)
del MODIFY_MODULES["School"]  # (*1)
del MODIFY_MODULES["SchoolClass"]  # (*3)
del MODIFY_MODULES["WorkGroup"]  # (*3)
#
# (*1) model does not support modify operation
# (*2) possibly a bug in the UDM REST API OpenAPI schema properties->emptyAttributes->nullable=true? -> udm_rest_client.exceptions.ModifyError: Unprocessable Entity: {'emptyAttributes': 'The property emptyAttributes has an invalid value: Invalid syntax. The property Empty attribute must be a list'}
# (*3) possibly a bug in the UDM REST API: PATCH /udm/groups/group/cn=DEMOSCHOOL-dvargas,cn=klassen,cn=schueler,cn=groups,ou=... -> udm_rest_client.exceptions.APICommunicationError: [HTTP 401] Credentials invalid or no permissions for operation 'update' on 'groups/group' with arguments {'groups_group': {'options': {'ucsschoolAdministratorGroup': False, 'samba': True, 'posix': True, 'ucsschoolImportGroup': False}, 'position': 'cn=klassen,cn=schueler,cn=groups,ou=...', 'properties': {'description': 'jeremydawson'}}, 'dn': 'cn=DEMOSCHOOL-dvargas,cn=klassen,cn=schueler,cn=groups,ou=...'}.
#

MOVE_MODULES = copy.deepcopy(CLASSES_MODULES)
del MOVE_MODULES["OU"]  # (*1)
del MOVE_MODULES["School"]  # (*1)
del MOVE_MODULES["ExamStudent"]  # (*2)
del MOVE_MODULES["SchoolAdmin"]  # (*3)
del MOVE_MODULES["Staff"]  # (*3)
del MOVE_MODULES["Student"]  # (*3)
del MOVE_MODULES["Teacher"]  # (*3)
del MOVE_MODULES["TeachersAndStaff"]  # (*3)
#
# (*1) model does not support move operation
# (*2) Bug in UDM REST API: Uncaught exception PUT /udm/users/user/uid=geraldbenitez,cn=examusers,ou=...; UDM_Error: This operation is not allowed on this object. Destination object can't have sub objects.
# (*3) Bug in ucsschool.lib!! TB starts at "await obj.change_school(ou2, udm)" -> udm_rest_client.exceptions.MoveError: Error moving UdmObject('users/user', 'uid=smithkyle,cn=admins,cn=users,ou=testou2176,...') to 'cn=admins,cn=users,ou=testou1991,...': [401] Unauthorized
#

REMOVE_MODULES = copy.deepcopy(CLASSES_MODULES)
del REMOVE_MODULES["Container"]  # (*1)
del REMOVE_MODULES["OU"]  # (*1)
del REMOVE_MODULES["School"]  # (*1)
#
# (*1) model does not support remove operation
#


def _inside_docker():
    try:
        import ucsschool.kelvin.constants
    except ImportError:
        return False
    return ucsschool.kelvin.constants.CN_ADMIN_PASSWORD_FILE.exists()


pytestmark = pytest.mark.skipif(
    not _inside_docker(),
    reason="Must run inside Docker container started by appcenter.",
)

fake = Faker()


@pytest.fixture
def create_hook_file():
    files_to_remove = []

    def _func(model: str, method: str) -> Tuple[str, str]:
        target_file = tempfile.NamedTemporaryFile(prefix=f"hook_result_{model}_{method}_", delete=False)
        target_file.close()
        files_to_remove.append(target_file.name)
        hook_file = tempfile.NamedTemporaryFile(
            dir=PYHOOKS_PATH, prefix=f"hook_{model}_{method}_", suffix=".py", delete=False
        )
        files_to_remove.append(hook_file.name)
        hook_text = HOOK_TEXT.replace("IMPORT_VAR", f"from {CLASSES_MODULES[model]} import {model}")
        hook_text = hook_text.replace("TARGET_FILE_VAR", target_file.name)
        hook_text = hook_text.replace("MODEL_CLASS_VAR", model)
        hook_text = hook_text.replace("HOOK_METHOD", method)
        hook_file.write(hook_text.encode())
        hook_file.close()
        files_to_remove.append(hook_file.name)
        _pyhook_loader.drop_cache()
        return hook_file.name, target_file.name

    yield _func

    while files_to_remove:
        path = files_to_remove.pop()
        try:
            os.unlink(path)
            print(f"Deleted {path!r}.")
        except FileNotFoundError:
            pass


@pytest.fixture
def creation_kwargs(
    random_first_name, random_last_name, random_user_name, schedule_delete_udm_obj, udm_kwargs
):
    async def _create_dhcp_service(ou: str, name: str) -> DHCPService:
        print("Creating DHCPService...")
        dhcp_service = DHCPService(school=ou, name=name)
        async with UDM(**udm_kwargs) as udm:
            if not await dhcp_service.create(udm):
                raise RuntimeError("Failed creating DHCPService.")
        print(f"Created {dhcp_service!r}.")
        schedule_delete_udm_obj(dhcp_service.dn, "dhcp/service")
        return dhcp_service

    async def _func(ou: str, model: str) -> Dict[str, Any]:
        result = {
            "school": ou,
            "name": random_user_name(),
        }
        if model in ("ExamStudent", "SchoolAdmin", "Staff", "Student", "Teacher", "TeachersAndStaff"):
            result.update(
                {
                    "firstname": random_first_name(),
                    "lastname": random_last_name(),
                }
            )
        elif model in ("ComputerRoom", "SchoolGroup", "SchoolClass", "WorkGroup"):
            result.update({"name": f"{ou}-{random_user_name()}", "users": [], "allowedEmailGroups": []})
        elif model in ("Share", "ClassShare", "GroupShare", "WorkGroupShare"):
            school_group = SchoolClass(school=ou, name=f"{ou}-{random_user_name()}", users=[])
            async with UDM(**udm_kwargs) as udm:
                if not await school_group.create(udm):
                    raise RuntimeError(f"Failed to create school group required for {model} object.")
            schedule_delete_udm_obj(school_group.dn, "groups/group")
            share = school_group.ShareClass.from_school_group(school_group)
            schedule_delete_udm_obj(share.dn, "shares/share")
            # use different name for ClassShare, as school_group will
            # have automatically created a ClassShare with its own name
            result.update({"name": random_user_name(), "school_group": school_group})
        elif model == "DHCPServer":
            result["dhcp_service"] = await _create_dhcp_service(ou, f"{result['name']}d")
        elif model == "DHCPSubnet":
            dhcp_service = await _create_dhcp_service(ou, f"{result['name']}d")
            result.update(
                {
                    "name": "11.40.231.0",
                    "dhcp_service": dhcp_service,
                    "subnet_mask": "255.255.248.0",  # /21
                }
            )
        elif model == "DNSReverseZone":
            result["name"] = fake.ipv4_private().rsplit(".", 1)[0]
        elif model in ("IPComputer", "MacComputer", "WindowsComputer"):
            result.update({"ip_address": [fake.ipv4_private()], "mac_address": [fake.mac_address()]})
        elif model == "MarketplaceShare":
            # there can be only one MarketplaceShare, and the test OU already has one
            async with UDM(**udm_kwargs) as udm:
                await MarketplaceShare(school=ou).remove(udm)
            del result["name"]
        elif model == "Network":
            result.update(
                {
                    "name": "12.40.232.0",
                    "netmask": "255.255.248.0",
                    "network": "12.40.232.0",
                }
            )
        elif model in ("School", "OU"):
            del result["school"]
        return result

    return _func


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ("Student",))
@pytest.mark.parametrize("method", ("pre_create",))
async def test_hooks_must_be_async(
    create_hook_file, creation_kwargs, create_ou_using_python, model, method, udm_kwargs
):
    ou = await create_ou_using_python()
    hook_file, target_file = create_hook_file(model, method)
    with open(hook_file, "r") as fp:
        hook_text = fp.read()
    hook_text = hook_text.replace(f"async def {method}", f"def {method}")
    with open(hook_file, "w") as fp:
        fp.write(hook_text)
    module = importlib.import_module(CLASSES_MODULES[model])
    cls = getattr(module, model)
    kwargs = await creation_kwargs(ou, model)
    obj = cls(**kwargs)
    async with UDM(**udm_kwargs) as udm:
        with pytest.raises(TypeError, match=f"Hook method TestHook.{method} must be an async function."):
            await obj.create(udm)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", CLASSES_MODULES.keys())
@pytest.mark.parametrize("method", ("pre_create", "post_create"))
async def test_create_hooks(
    create_hook_file, creation_kwargs, create_ou_using_python, model, method, udm_kwargs
):
    ou = await create_ou_using_python()
    hook_file, target_file = create_hook_file(model, method)
    module = importlib.import_module(CLASSES_MODULES[model])
    cls = getattr(module, model)
    kwargs = await creation_kwargs(ou, model)
    obj = cls(**kwargs)
    async with UDM(**udm_kwargs) as udm:
        await obj.create(udm)
    with open(target_file, "r") as fp:
        result = fp.read()
    print(f"target_file content: {result}")
    if model in ("Container", "OU"):
        assert not result
    else:
        assert f"{method} {model} {obj.name} {obj.school}" in result


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MODIFY_MODULES.keys())
@pytest.mark.parametrize("method", ("pre_modify", "post_modify"))
async def test_modify_hooks(
    create_hook_file,
    creation_kwargs,
    create_ou_using_python,
    model,
    method,
    random_first_name,
    random_user_name,
    udm_kwargs,
):
    ou = await create_ou_using_python()
    hook_file, target_file = create_hook_file(model, method)
    module = importlib.import_module(CLASSES_MODULES[model])
    cls = getattr(module, model)
    kwargs = await creation_kwargs(ou, model)
    obj = cls(**kwargs)
    async with UDM(**udm_kwargs) as udm:
        await obj.create(udm)

    # try to change an attribute, not that it'd be necessary, but it can't hurt either
    if hasattr(obj, "display_name"):
        obj.display_name = random_user_name()
    elif hasattr(obj, "description"):
        obj.description = random_user_name()
    elif hasattr(obj, "inventory_number"):
        obj.inventory_number = random_user_name()
    elif hasattr(obj, "firstname"):
        obj.firstname = random_first_name()
    elif obj.__class__.__name__ == "DHCPServer":
        dhcp_service_dn = ",".join(explode_dn(obj.dn, False)[1:])
        obj.name = "{}b".format(obj.name)  # change something
        # not loaded automatically, but required:
        async with UDM(**udm_kwargs) as udm:
            obj.dhcp_service = await DHCPService.from_dn(dhcp_service_dn, ou, udm)
    elif obj.__class__.__name__ == "Network":
        obj.netmask = "21"  # prevent UDM valueMayNotChange exception (value is 255.255.248.0)
        obj.broadcast = "12.40.232.255"  # change something (was None)

    # required for group objects:
    for attr in ("hosts", "users"):
        if hasattr(obj, attr) and getattr(obj, attr) is None:
            setattr(obj, attr, [])

    async with UDM(**udm_kwargs) as udm:
        await obj.modify(udm)

    with open(target_file, "r") as fp:
        result = fp.read()
    print(f"target_file content: {result}")
    if model in CLASSES_WITH_SCHOOL_NONE:
        assert obj.school is None
    else:
        assert obj.school == ou
    assert f"{method} {model} {obj.name} {obj.school}" in result


@pytest.mark.asyncio
@pytest.mark.parametrize("model", MOVE_MODULES.keys())
@pytest.mark.parametrize("method", ("pre_move", "post_move"))
async def test_move_hooks(
    create_hook_file,
    creation_kwargs,
    create_multiple_ous,
    ldap_base,
    model,
    method,
    random_first_name,
    random_user_name,
    udm_kwargs,
):
    ou1, ou2 = await create_multiple_ous(2)
    print(f"** ou1={ou1!r} ou2={ou2!r}")
    hook_file, target_file = create_hook_file(model, method)
    module = importlib.import_module(CLASSES_MODULES[model])
    cls = getattr(module, model)
    kwargs = await creation_kwargs(ou1, model)
    obj = cls(**kwargs)
    async with UDM(**udm_kwargs) as udm:
        await obj.create(udm)

    async with UDM(**udm_kwargs) as udm:
        obj = await cls.from_dn(obj.dn, ou1, udm)

    if model == "SchoolAdmin":
        async with UDM(**udm_kwargs) as udm:
            # check that target container exists
            target_cn = await udm.get("container/cn").get(f"cn=admins,cn=users,ou={ou2},{ldap_base}")
            print(f"Trying to move to existing {target_cn!r}.")

    if hasattr(obj, "schools"):
        async with UDM(**udm_kwargs) as udm:
            await obj.change_school(ou2, udm)
        move_success = True
    else:
        # the move will fail - that's expected!
        obj.school = ou2
        async with UDM(**udm_kwargs) as udm:
            move_success = await obj.move(udm)
        assert not move_success, f"=====> Move of model {model!r} succeeded unexpectedly."
        # obj.school = ou1

    with open(target_file, "r") as fp:
        result = fp.read()
    print(f"target_file content: {result}")

    if model == "Group":
        # see Group.get_class_for_udm_obj()
        model = "SchoolGroup"

    if method == "pre_move" or method == "post_move" and move_success:
        assert f"{method} {model} {obj.name} {obj.school}" in result
    else:
        # most models don't support move(), so post_move() isn't executed
        assert not result


@pytest.mark.asyncio
@pytest.mark.parametrize("model", REMOVE_MODULES.keys())
@pytest.mark.parametrize("method", ("pre_remove", "post_remove"))
async def test_remove_hooks(
    create_hook_file,
    creation_kwargs,
    create_ou_using_python,
    model,
    method,
    random_first_name,
    random_user_name,
    udm_kwargs,
):
    ou = await create_ou_using_python()
    hook_file, target_file = create_hook_file(model, method)
    module = importlib.import_module(CLASSES_MODULES[model])
    cls = getattr(module, model)
    kwargs = await creation_kwargs(ou, model)
    obj = cls(**kwargs)
    async with UDM(**udm_kwargs) as udm:
        await obj.create(udm)

    async with UDM(**udm_kwargs) as udm:
        obj = await cls.from_dn(obj.dn, ou, udm)
        await obj.remove(udm)

    with open(target_file, "r") as fp:
        result = fp.read()
    print(f"target_file content: {result}")

    if model == "Group":
        # see Group.get_class_for_udm_obj()
        model = "SchoolGroup"

    assert f"{method} {model} {obj.name} {obj.school}" in result
