#
# Univention UCS@school
#  listener module
#
# SPDX-FileCopyrightText: 2007-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import absolute_import

import os
import shlex
import shutil
import time

try:
    from subprocess import getstatusoutput
except ImportError:
    from commands import getstatusoutput

from listener import configRegistry, setuid, unsetuid

import univention.debug as ud

hostname = configRegistry["hostname"]
domainname = configRegistry["domainname"]
ip = configRegistry["interfaces/eth0/address"]  # FIXME: ...
name = "remove-old-sharedirs"
description = "moves directories of removed group shares to backup folder"
filter = "(&(objectClass=univentionShare)(|(univentionShareHost=%s.%s)(univentionShareHost=%s)))" % (
    hostname,
    domainname,
    ip,
)
attributes = []
modrdn = "1"

DEFAUL_FS = "ext2/ext3:ext2:ext3:ext4:xfs:btrfs"
TARGET_BLACKLIST = "/:/boot:/sys:/proc:/etc:/dev"

target_dir = configRegistry.get("ucsschool/listener/oldsharedir/targetdir")
prefixlist = configRegistry.get("ucsschool/listener/oldsharedir/prefixes", "").split(":")
fs_types = configRegistry.get("ucsschool/listener/oldsharedir/fs_types", DEFAUL_FS).split(":")

# either returns "" if everything is ok, or returns an error message


def check_target_dir(directory):
    if not directory:
        return "targetdir is not set"

    # check target blacklist
    tmp = directory.rstrip("/")
    for i in TARGET_BLACKLIST.split(":"):
        if not tmp or tmp == i:
            return "%s as target directory is invalid" % directory

    if os.path.exists(directory) and not os.path.isdir(directory):
        return "%s is not a directory" % directory

    # create directory
    if not os.path.isdir(directory):
        setuid(0)
        try:
            os.makedirs(directory)
        except EnvironmentError:
            return "failed to create target directory %s" % directory
        finally:
            unsetuid()

    # check fs
    ret = check_filesystem(directory)
    if ret:
        return ret

    return ""


def check_source_dir(prefixlist, directory):
    """either returns "" if everything is ok, or returns an error message"""
    # check directory
    if not os.path.isdir(directory):
        return "%s is not a directory" % directory

    # check fs
    ret = check_filesystem(directory)
    if ret:
        return ret

    # check allowed prefix
    for prefix in prefixlist:
        if directory.startswith(prefix):
            return ""

    return "%s does not match any value in ucsschool/listener/oldsharedir/prefixes" % directory


def check_filesystem(directory):
    """make sure that we are dealing with a known filesystem"""
    ret, out = getstatusoutput("LC_ALL=C stat -f %s" % shlex.quote(directory))  # nosec  # noqa: S605
    myFs = ""
    for line in out.splitlines():
        tmp = line.split("Type: ", 1)
        if len(tmp) == 2:
            myFs = tmp[1].strip()
            for fs in fs_types:
                if fs.lower() == myFs.lower():
                    # ok,
                    return ""
            break
    return "%s for %s is not on a known filesystem" % (myFs, directory)


def move_dir(src, dst):
    """move directory"""
    newName = os.path.basename(src) + ".%s" % int(time.time())
    dst = os.path.join(dst, newName)
    ret = ""

    setuid(0)
    try:
        shutil.move(src, dst)
    except Exception as exc:
        ret = str(exc)
    finally:
        unsetuid()

    return ret


def handler(dn, new, old, command):
    """
    remove empty share directories
    if object is really removed (not renamed)
    """
    if old and not new and not command == "r":
        name = old["cn"][0].decode("UTF-8")

        # check object
        if not old.get("univentionShareHost") or not old.get("univentionSharePath"):
            ud.debug(
                ud.LISTENER,
                ud.WARN,
                "not removing directory of share %s: univentionShareHost(Path) ist not set" % name,
            )
            return

        share_dir = old["univentionSharePath"][0].decode("UTF-8")

        # check if target directory is okay
        ret = check_target_dir(target_dir)
        if ret:
            ud.debug(ud.LISTENER, ud.WARN, "not removing directory of share %s: %s" % (name, ret))
            return

        # check source (share) directory
        ret = check_source_dir(prefixlist, share_dir)
        if ret:
            ud.debug(ud.LISTENER, ud.WARN, "not removing share directory of share %s: %s" % (name, ret))
            return

        # move it
        ret = move_dir(share_dir, target_dir)
        if ret:
            ud.debug(
                ud.LISTENER,
                ud.ERROR,
                "failed to move directory of share %s from %s to %s: %s"
                % (name, share_dir, target_dir, ret),
            )
