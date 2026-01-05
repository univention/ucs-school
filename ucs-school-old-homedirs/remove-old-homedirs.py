#
# Univention UCS@school
#  listener module
#
# SPDX-FileCopyrightText: 2007-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import absolute_import

import os
import shutil
import time

from listener import configRegistry, setuid, unsetuid
from psutil import disk_partitions

import univention.debug as ud

name = "remove-old-homedirs"
description = "moves directories of removed users away from home"
filter = "(objectClass=ucsschoolType)"
attributes = ["posixAccount"]
modrdn = "1"

DEFAUL_FS = "ext2/ext3:ext2:ext3:ext4:xfs:btrfs"
TARGET_BLACKLIST = ["/", "/boot", "/sys", "/proc", "/etc", "/dev"]

target_dir = configRegistry.get("ucsschool/listener/oldhomedir/targetdir")
fs_types = configRegistry.get("ucsschool/listener/oldhomedir/fs_types", DEFAUL_FS).split(":")
exam_remove = configRegistry.is_true("ucsschool/exam/user/homedir/autoremove", False)


def check_target_dir(directory):
    """either returns "" if everything is ok, or returns an error message"""
    if not directory:
        return "targetdir is not set"

    # check target blacklist
    directory = directory.rstrip("/")
    if not directory or directory in TARGET_BLACKLIST:
        return "%s as target directory is invalid" % directory

    if os.path.exists(directory) and not os.path.isdir(directory):
        return "%s is not a directory" % directory

    # create directory
    if not os.path.isdir(directory):
        setuid(0)
        try:
            os.makedirs(directory)
        except EnvironmentError as exc:
            return "failed to create target directory %s: %s" % (directory, exc)
        finally:
            unsetuid()

    # check fs
    ret = check_filesystem(directory)
    if ret:
        return ret

    return ""


def check_source_dir(directory):
    """either returns "" if everything is ok, or returns an error message"""
    if not os.path.exists(directory):
        return "%s does not exist" % directory
    if not os.path.isdir(directory):
        return "%s is not a directory" % directory

    # check fs
    ret = check_filesystem(directory)
    if ret:
        return ret

    return ""


def check_filesystem(directory):
    """either returns "" if everything is ok, or returns an error message"""
    partitions = [(p[1], p[2]) for p in disk_partitions(True)]
    partitions.sort(key=lambda x: len(x[0]), reverse=True)
    path = os.path.realpath(os.path.abspath(directory))
    for k, v in partitions:
        if path.startswith(k):
            if v in fs_types:
                return ""
            else:
                break
    return "%s is not on a known filesystem" % directory


# move directory
def move_dir(src, dst):
    """either returns "" if everything is ok, or returns an error message"""
    newName = os.path.basename(src) + ".%s" % int(time.time())
    dst = os.path.join(dst, newName)
    ret = ""

    setuid(0)
    try:
        shutil.move(src, dst)
    except EnvironmentError as exc:
        ret = str(exc)
    finally:
        unsetuid()
    warn("moved %s to %s." % (src, dst))

    return ret


def warn(msg):
    ud.debug(ud.LISTENER, ud.WARN, "remove-old-homedirs: {}".format(msg))


def handler(dn, new, old, command):
    if old and not new and command != "r":  # user was deleted or moved to another OU
        uid = old["uid"][0].decode("UTF-8")
        if not exam_remove and b"ucsschoolExam" in old["objectClass"]:
            warn(
                "ignoring exam user {!r}, as ucsschool/exam/user/homedir/autoremove is set to "
                "False.".format(uid)
            )
            return

        home_dir = old.get("homeDirectory", [b""])[0].decode("UTF-8")
        if not home_dir:
            warn("not removing home of user %s: homeDirectory not set" % uid)
            return

        # check if target directory is okay
        ret = check_target_dir(target_dir)
        if ret:
            warn("not removing home of user %s: %s" % (uid, ret))
            return

        # check source (home) directory
        ret = check_source_dir(home_dir)
        if ret:
            warn("not removing home of user %s: %s" % (uid, ret))
            return

        # move it
        ret = move_dir(home_dir, target_dir)
        if ret:
            warn("failed to move home of user %s from %s to %s: %s" % (uid, home_dir, target_dir, ret))
        return
