#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: Print UCS@school installation information
## tags: [apptest, ucsschool]
## exposure: safe

import logging
import os
import sys

from apt.cache import Cache as AptCache

import univention.testing.ucr

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()
ucr = univention.testing.ucr.UCSTestConfigRegistry()
ucr.load()
apt_cache = AptCache()
pck_s = [
    "{:<40} {}".format(
        pck, apt_cache[pck].installed.version if apt_cache[pck].is_installed else "Not installed"
    )
    for pck in sorted([pck for pck in apt_cache.keys() if "school" in pck])
]
logger.info("Installed package versions:\n%s", "\n".join(pck_s))

logger.info("=" * 79)

for filename in os.listdir("/etc/apt/sources.list.d/"):
    path = os.path.join("/etc/apt/sources.list.d", filename)
    logger.info("Content of %r:\n%s", path, open(path, "rb").read())

logger.info("=" * 79)

logger.info("UCR:\n%s", "\n".join("{!r}: {!r}".format(k, ucr[k]) for k in sorted(ucr.keys())))

sys.exit(0)
