#!/usr/bin/python2.7
#
# UCS@school join hook
#
# Copyright 2018-2024 Univention GmbH
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

# As long as we support mixed environments with 4.4 we must provide this join hook as Python 2.7

import argparse
import json
import logging
import os
import subprocess
import sys
from collections import OrderedDict, namedtuple

try:
    from typing import Any, List, NamedTuple, Optional  # noqa: F401

    _HAS_TYPING = True
except ImportError:
    _HAS_TYPING = False

from distutils.version import LooseVersion

from ldap.filter import filter_format

import univention.admin
from univention.config_registry import ConfigRegistry, handler_set
from univention.lib.package_manager import PackageManager

log = None  # type: Optional[logging.Logger]
ucr = None  # type: Optional[ConfigRegistry]

if _HAS_TYPING:
    StdoutStderr = NamedTuple("StdoutStderr", [("stdout", str), ("stderr", str)])
    SchoolMembership = NamedTuple(
        "SchoolMembership", [("is_edu_school_member", bool), ("is_admin_school_member", bool)]
    )
else:
    StdoutStderr = namedtuple("StdoutStderr", ["stdout", "stderr"])
    SchoolMembership = namedtuple("SchoolMembership", ["is_edu_school_member", "is_admin_school_member"])

VEYON_APP_ID = "ucsschool-veyon-proxy"
MINIMUM_UCSSCHOOL_VERSION_FOR_VEYON = "4.4 v9"


class CallCommandError(Exception):
    pass


def get_lo(options):  # type: (Any) -> univention.admin.uldap.access
    log.info("Connecting to LDAP as %r ...", options.binddn)
    try:
        lo = univention.admin.uldap.access(
            host=options.master_fqdn,
            port=int(ucr.get("ldap/master/port", "7389")),
            base=ucr.get("ldap/base"),
            binddn=options.binddn,
            bindpw=options.bindpw,
        )
    except univention.admin.uexceptions.authFail:
        log.error("username or password is incorrect")
        sys.exit(5)
    return lo


def get_school_membership(options):  # type: (Any) -> SchoolMembership
    filter_s = filter_format(
        "(&(objectClass=univentionGroup)(uniqueMember=%s))", (ucr.get("ldap/hostdn"),)
    )
    grp_dn_list = options.lo.searchDn(filter=filter_s)
    log.info("Host is member of following groups: %r", grp_dn_list)
    is_edu_school_member = False
    is_admin_school_member = False
    for grp_dn in grp_dn_list:
        # is grp_dn in list of global school groups?
        if grp_dn in (
            "cn=DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
            "cn=Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
        ):
            log.debug("host is in group %s", grp_dn)
            is_edu_school_member = True
        if grp_dn in (
            "cn=DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
            "cn=Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
        ):
            log.debug("host is in group %s", grp_dn)
            is_admin_school_member = True
        # is dn in list of OU specific school groups?
        if not grp_dn.startswith("cn=OU"):
            continue
        for suffix in (
            "-DC-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
            "-Member-Edukativnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
        ):
            if grp_dn.endswith(suffix):
                log.debug("host is in group %s", grp_dn)
                is_edu_school_member = True
        for suffix in (
            "-DC-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
            "-Member-Verwaltungsnetz,cn=ucsschool,cn=groups,{}".format(ucr.get("ldap/base")),
        ):
            if grp_dn.endswith(suffix):
                log.debug("host is in group %s", grp_dn)
                is_admin_school_member = True
    return SchoolMembership(is_edu_school_member, is_admin_school_member)


def determine_role_packages(options, package_manager):  # type: (Any, PackageManager) -> List[str]
    IS_UCS4 = ucr["version/version"].startswith("4.")
    if options.server_role in ("domaincontroller_master",):
        return []

    elif options.server_role in ("domaincontroller_backup",):
        # if metapackage is already installed, then stick with it and don't change it
        for pkg_name in (
            "ucs-school-multiserver",
            "ucs-school-singleserver",
            "ucs-school-master",  # UCS@school 4.4
            "ucs-school-singleserver",  # UCS@school 4.4
        ):
            if package_manager.is_installed(pkg_name):
                log.info("Found installed metapackage %r. Reusing it.", pkg_name)
                return [pkg_name]
        # if no metapackage has been found, determine package type via Primary Node's UCR variable
        result = call_cmd_on_master(
            options.master_fqdn, "/usr/sbin/ucr", "get", "ucsschool/singlemaster"
        )
        if ucr.is_true(value=result.stdout.strip()):
            log.info("Primary Directory Node is a UCS@school single server system")
            return ["ucs-school-singleserver" if not IS_UCS4 else "ucs-school-singlemaster"]
        else:
            log.info("Primary Directory Node is part of a multi server environment")
            return ["ucs-school-multiserver" if not IS_UCS4 else "ucs-school-master"]

    elif options.server_role in ("domaincontroller_slave",):
        # if metapackage is already installed, then stick with it and don't change it
        for pkg_name in (
            "ucs-school-replica",
            "ucs-school-nonedu-replica",
            "ucs-school-central-replica",
            "ucs-school-slave",  # UCS@school 4.4
            "ucs-school-nonedu-slave",  # UCS@school 4.4
            "ucs-school-central-slave",  # UCS@school 4.4
        ):
            if package_manager.is_installed(pkg_name):
                log.info("Found installed metapackage %r. Reusing it.", pkg_name)
                return [pkg_name]

        # if no metapackage has been found, then determine Replica Node type via group memberships
        membership = get_school_membership(options)
        if membership.is_edu_school_member:
            return ["ucs-school-replica" if not IS_UCS4 else "ucs-school-slave"]
        elif membership.is_admin_school_member:
            return ["ucs-school-nonedu-replica" if not IS_UCS4 else "ucs-school-nonedu-slave"]
        else:
            return ["ucs-school-central-replica" if not IS_UCS4 else "ucs-school-central-slave"]

    elif options.server_role in ("memberserver",):
        return []

    log.warning("System role %r not found!", options.server_role)
    return []


def call_cmd_on_master(master_fqdn, *cmd):  # type: (str, *str) -> StdoutStderr
    local_cmd = [
        "univention-ssh",
        "/etc/machine.secret",
        "{}$@{}".format(ucr.get("hostname"), master_fqdn),
        " ".join(cmd),
    ]
    return call_cmd_locally(*local_cmd)


def call_cmd_locally(*cmd):  # type: (*str) -> StdoutStderr
    log.info("Calling %r ...", cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # nosec
    stdout, stderr = proc.communicate()
    stdout, stderr = stdout.decode("UTF-8", "replace"), stderr.decode("UTF-8", "replace")
    if proc.returncode:
        raise CallCommandError(
            "{!r} returned with exitcode {}:\n{}\n{}".format(cmd, proc.returncode, stderr, stdout)
        )
    return StdoutStderr(stdout, stderr)


def activate_repository():  # type: () -> None
    """
    Bug #49475: on UCS 4.4-0 DVDs the UCR variable repository/online is false and therefore
    an installation via univention-app will fail. This is a workaround until the installation
    media has been fixed/adapted.
    """
    log.info("repository/online: %r", ucr.get("repository/online"))
    if ucr.is_false("repository/online", False):
        log.warning("The online repository is deactivated. Reactivating it.")
        handler_set(["repository/online=true"])
        call_cmd_locally("/usr/bin/apt-get", "update")


def pre_joinscripts_hook(options):  # type: (Any) -> None
    # do not do anything, if we are running within a docker container
    if ucr.get("docker/container/uuid"):
        log.info("This is a docker container... stopping here")
        return

    package_manager = PackageManager(lock=False, always_noninteractive=True)

    pkg_list = determine_role_packages(options, package_manager)
    log.info("Determined role packages: %r", pkg_list)

    # check if UCS@school app is installed/configured/included,
    # if not, then install the same version used by domaincontroller_master
    result = call_cmd_locally("/usr/bin/univention-app", "info", "--as-json")
    local_status = json.loads(result.stdout)
    for app_entry in local_status.get("installed", []):
        app_name, app_version = app_entry.split("=", 1)
        if app_name == "ucsschool":
            ucsschool_installed = True
            break
    else:
        app_version = ""
        ucsschool_installed = False
    log.info("Installed apps: %r", local_status.get("installed"))
    log.info(
        "Is ucsschool already installed? %r%s",
        ucsschool_installed,
        " ({})".format(app_version) if app_version else "",
    )
    # only install UCS@school if at least one package has to be installed
    if not ucsschool_installed and pkg_list:
        result = call_cmd_on_master(options.master_fqdn, "/usr/sbin/ucr", "get", "version/version")
        master_version = result.stdout.strip()
        result = call_cmd_locally("ucr", "get", "version/version")
        local_version = result.stdout.strip()
        app_string = "ucsschool"
        log.info("Primary Directory Node version: %r", master_version)
        log.info("Local version: %r", local_version)
        if master_version == local_version:
            result = call_cmd_on_master(
                options.master_fqdn, "/usr/bin/univention-app", "info", "--as-json"
            )
            master_app_info = json.loads(result.stdout)
            # master_app_info:  {"compat": "4.3-1 errata0", "upgradable": [], "ucs": "4.3-1 errata0",
            # "installed": ["ucsschool=4.3 v5"]}

            for app_entry in master_app_info.get("installed", []):
                app_name, app_version = app_entry.split("=", 1)
                if app_name == "ucsschool":
                    log.info("Found UCS@school version %r on Primary Directory Node.", app_version)
                    break
            else:
                log.error(
                    "UCS@school does not seem to be installed on %s! Cannot get app version of "
                    "UCS@school on Primary Directory Node!",
                    options.master_fqdn,
                )
                sys.exit(1)

            app_version = determine_app_version(app_version, package_manager)
            app_string = "%s=%s" % (app_string, app_version)

        activate_repository()

        log.info("Updating app center information...")
        call_cmd_locally("/usr/bin/univention-app", "update")

        log.info("Installing %s ...", app_string)
        cmd = [
            "/usr/bin/univention-app",
            "install",
            app_string,
            "--skip-check",
            "must_have_valid_license",
            "--do-not-call-join-scripts",
            "--noninteractive",
            "--do-not-revert",
        ]
        if options.server_role not in ("domaincontroller_master", "domaincontroller_backup"):
            username = options.lo.getAttr(options.binddn, "uid")[0].decode("UTF-8")
            cmd.extend(["--username", username, "--pwdfile", options.bindpwdfile])
        call_cmd_locally(*cmd)

    # if not all packages are installed, then try to install them again
    if not all(package_manager.is_installed(pkg_name) for pkg_name in pkg_list):
        log.info("Not all required packages installed - calling univention-install...")
        call_cmd_locally("univention-install", "--force-yes", "--yes", *pkg_list)

    install_veyon_app(options, pkg_list)


def determine_app_version(primary_node_app_version, package_manager):
    # type: (str, PackageManager) -> str

    # When the pre-join hook is executed on a repliction node, it fetches the UCS@school version
    # installed on the primary node and trys to install the same one on the repliction node.
    # But the errata level of the UCS installation (already installed or currently installing from DVD)
    # may be below the one required by the UCS@school version. In such a case a lower app version
    # with lower requirements must be installed.

    # To add further checks, edit the "requirements" and "replacements" dictionaries. The order of the
    # "requirements" dict is the one in which the checks will be executed. Please leave a comment with
    # the reason for the errata requirement. The "replacements" dict holds the information which app
    # version should be installed in case a dependency is not met.

    log.info("Checking app version dependencies...")
    result_app_version = primary_node_app_version
    errata_package = package_manager.get_package("univention-errata-level")
    errata_loose_version = LooseVersion(errata_package.installed.version)
    primary_node_app_loose_version = LooseVersion(primary_node_app_version)
    # Order by which requirements will be checked:
    requirements = OrderedDict(
        (
            ("4.4 v7", "4.4.6-762"),  # Bug #52214 - univention-samba4 package for share permissions
            ("4.4 v9", "4.4.7-841"),  # Bug #52551 - univention-docker sec policy for Veyon proxy app
        )
    )
    replacements = {
        "4.4 v7": "4.4 v6",
        "4.4 v9": "4.4 v8",
    }
    for app_version, requirement in requirements.items():
        if primary_node_app_loose_version >= LooseVersion(
            app_version
        ) and errata_loose_version < LooseVersion(requirement):
            result_app_version = replacements[app_version]
            log.warning(
                "Current errata level (%r) to low for UCS@school version %r, installing %r instead.",
                errata_package.installed.version,
                app_version,
                result_app_version,
            )
            break
    else:
        log.info("UCS@school version %r can be installed.", primary_node_app_version)
    return result_app_version


def veyon_app_should_be_installed(options, roles_pkg_list):  # type: (Any, List[str]) -> bool
    """
    Check whether the Veyon Proxy App should be installed on this system.

    :return: True if this is a singleserver or an edu Replica Directory Node, else False
    """
    if options.server_role == "domaincontroller_master":
        return ucr.is_true("ucsschool/singlemaster")
    return "ucs-school-replica" in roles_pkg_list or "ucs-school-slave" in roles_pkg_list


def install_veyon_app(options, roles_pkg_list):  # type: (Any, List[str]) -> None
    """Install 'UCS@school Veyon Proxy' app on local system if it is an edu Replica Directory Node."""
    if not veyon_app_should_be_installed(options, roles_pkg_list):
        log.info("Not installing 'UCS@school Veyon Proxy' app on this system role.")
        return
    result = call_cmd_locally("/usr/bin/univention-app", "info", "--as-json")
    app_infos = json.loads(result.stdout)
    for app_entry in app_infos.get("installed", []):
        app_name, app_version = app_entry.split("=", 1)
        if app_name == "ucsschool" and LooseVersion(app_version) < LooseVersion(
            MINIMUM_UCSSCHOOL_VERSION_FOR_VEYON
        ):
            log.info(
                "Not installing 'UCS@school Veyon Proxy' app on local system with UCS@school version "
                "prior to %r.",
                MINIMUM_UCSSCHOOL_VERSION_FOR_VEYON,
            )
            return
        elif app_name == VEYON_APP_ID:
            log.info("Found 'UCS@school Veyon Proxy' app version %r on local system.", app_version)
            return
    log.info("Installing 'UCS@school Veyon Proxy' app on local system...")

    log.info("Updating app center information...")
    call_cmd_locally("/usr/bin/univention-app", "update")

    log.info("Installing 'UCS@school Veyon Proxy' app (%r)...", VEYON_APP_ID)
    log.info("Log output of the installation goes to 'appcenter.log'.")
    cmd = [
        "/usr/bin/univention-app",
        "install",
        VEYON_APP_ID,
        "--skip-check",
        "must_have_valid_license",
        "--do-not-call-join-scripts",
        "--noninteractive",
    ]
    if options.server_role not in ("domaincontroller_master", "domaincontroller_backup"):
        username = options.lo.getAttr(options.binddn, "uid")[0].decode("UTF-8")
        cmd.extend(["--username", username, "--pwdfile", options.bindpwdfile])
    try:
        call_cmd_locally(*cmd)
    except CallCommandError as exc:
        # don't exit program if veyon proxy app cannot be installed
        log.error("#" * 79)
        log.error("# Error installing the 'UCS@school Veyon Proxy' app.                          #")
        log.error("#" * 79)
        log.error(str(exc))
        log.error("#" * 79)
        log.error("# Please install the app manually by executing on the command line:           #")
        log.error("# univention-app install ucsschool-veyon-proxy                                #")
        log.error("#" * 79)


def main():  # type: () -> None
    global log, ucr

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server-role",
        help="server role of this system",
    )
    parser.add_argument(
        "--master",
        dest="master_fqdn",
        help="FQDN of the UCS Primary Directory Node",
    )
    parser.add_argument("--binddn", help="LDAP binddn")
    parser.add_argument("--bindpwdfile", help="path to password file")
    parser.add_argument(
        "--hooktype",
        dest="hook_type",
        help='join hook type (currently only "join/pre-joinscripts" supported)',
    )
    parser.add_argument("-v", "--verbose", action="count", default=3, help="Increase verbosity")
    options = parser.parse_args()

    if not options.server_role:
        parser.error("Please specify a server role")
    if not options.master_fqdn:
        parser.error("Please specify a FQDN for the Primary Directory Node")
    if not options.binddn:
        parser.error("Please specify a LDAP binddn")
    if not options.bindpwdfile:
        parser.error("Please specify a path to a file with a LDAP password")
    if not os.path.isfile(options.bindpwdfile):
        parser.error("The given path for --bindpwdfile is not valid")
    if not options.hook_type:
        parser.error("Please specify a hook type")
    if options.hook_type in ("join/post-joinscripts",):
        parser.error("The specified hook type is not supported by this script")

    options.bindpw = open(options.bindpwdfile).read().strip()

    LEVELS = [logging.FATAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    try:
        level = LEVELS[options.verbose]
    except IndexError:
        level = LEVELS[-1]
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format="%(asctime)s ucsschool-join-hook: [%(levelname)s] %(message)s",
    )

    log = logging.getLogger(__name__)
    log.info("ucsschool-join-hook.py has been started")
    ucr = ConfigRegistry()
    ucr.load()

    if ucr.is_false("ucsschool/join/hook/join/pre-joinscripts", False):
        log.warning(
            "UCS@school join hook has been disabled via UCR variable "
            "ucsschool/join/hook/join/pre-joinscripts."
        )
        sys.exit(0)

    options.lo = get_lo(options)

    try:
        pre_joinscripts_hook(options)
    except CallCommandError as exc:
        log.error(str(exc))
        sys.exit(1)

    log.info("ucsschool-join-hook.py is done")


if __name__ == "__main__":
    main()
