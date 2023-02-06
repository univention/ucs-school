from __future__ import print_function

from ipaddress import AddressValueError, IPv4Interface, NetmaskValueError
from typing import List  # noqa: F401

from ldap.filter import filter_format

from ucsschool.importer.exceptions import ComputerImportError
from ucsschool.importer.utils.constants import get_default_prefixlen
from ucsschool.importer.utils.import_pyhook import get_import_pyhooks
from ucsschool.lib.models.computer import SchoolComputer  # noqa: F401
from ucsschool.lib.models.utils import ucr
from univention.admin.uldap import access as LoType  # noqa: F401


def call_hook(lo, meth_name, obj, line):  # type: (LoType, str, SchoolComputer, List[str]) -> None
    hooks = get_import_pyhooks(
        "ucsschool.importer.utils.computer_pyhook.ComputerPyHook",
        None,
        lo=lo,
        dry_run=False,
    )  # result is cached on the lib side
    try:
        for func in hooks.get(meth_name, []):
            print(
                "Running {} hook {}.{} for {}.".format(
                    meth_name, func.__self__.__class__.__name__, func.__name__, obj
                )
            )
            func(obj, line)
    except Exception as exc:
        raise ComputerImportError("In hook stage %s: %s" % (meth_name, exc))


def get_ip_iface(ip_address):  # type: (str) -> IPv4Interface
    try:
        ip_iface = IPv4Interface("%s" % ip_address)
    except AddressValueError as exc:
        raise ComputerImportError("%s is not a valid ip address" % (exc,))
    except NetmaskValueError as exc:
        raise ComputerImportError("%s is not a valid netmask" % (exc,))

    if "/" not in ip_address:
        ip_iface = IPv4Interface("%s/%s" % (ip_address, get_default_prefixlen()))
        print(
            "WARNING: no netmask specified for ip address %s using %s"
            % (ip_iface.with_prefixlen, ip_iface.netmask)
        )
    return ip_iface


def mac_address_is_used(mac_address, lo):  # type: (str, LoType) -> bool
    return bool(
        lo.search(
            base=ucr["ldap/base"],
            scope="sub",
            filter=filter_format("(&(macAddress=%s)(objectClass=univentionHost))", [mac_address]),
            attr=["macAddress"],
        )
    )
