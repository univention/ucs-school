import importlib
import os
import tempfile
from typing import Any, Dict, Tuple

import pytest

from ucsschool.lib.models.base import PYHOOKS_PATH, _pyhook_loader
from udm_rest_client import UDM

HOOK_TEXT = """
# -*- coding: utf-8 -*-
from ucsschool.lib.models.hook import Hook
IMPORT_VAR  # noqa: F821

print("*********** HOOK **********")
print("*** __file__={__file__!r}")
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
    "SchoolClass": "ucsschool.lib.models.group",
    "Student": "ucsschool.lib.models.user",
}


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
def creation_kwargs(random_first_name, random_last_name, random_user_name):
    def _func(ou: str, model: str) -> Dict[str, Any]:
        if model == "Student":
            return {
                "school": ou,
                "name": random_user_name(),
                "firstname": random_first_name(),
                "lastname": random_last_name(),
            }
        elif model == "SchoolClass":
            return {
                "school": ou,
                "name": f"{ou}-{random_user_name()}",
            }
        raise ValueError(f"Unknown model {model!r}.")

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
    kwargs = creation_kwargs(ou, model)
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
    kwargs = creation_kwargs(ou, model)
    obj = cls(**kwargs)
    async with UDM(**udm_kwargs) as udm:
        await obj.create(udm)
    with open(target_file, "r") as fp:
        result = fp.read()
    print(f"target_file content: {result}")
    assert f"{method} {model} {obj.name} {obj.school}" in result
