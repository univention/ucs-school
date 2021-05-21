#!/usr/share/ucs-test/runner /usr/bin/pytest -l -v
## -*- coding: utf-8 -*-
## desc: test settings in kelvin app ini file
## roles: [domaincontroller_master]
## tags: [apptest,ucsschool,ucsschool_import1]
## exposure: safe

import itertools
import re

try:
    from typing import Iterable
except ImportError:
    pass
try:
    import ConfigParser
except ImportError:
    from configparser import ConfigParser  # py3
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin  # Python 3

import tempfile

import pytest
import requests

APPCENTER_SERVERS = ("appcenter.software-univention.de", "appcenter-test.software-univention.de")
INI_PARENT_PATH = "/meta-inf/4.4/ucsschool-kelvin-rest-api"
BASE_URLS = ("https://{}/{}/".format(server, INI_PARENT_PATH) for server in APPCENTER_SERVERS)
URL_PATTERN = re.compile(r".*>(?P<component>ucsschool-kelvin-rest-api_.+\.ini?)<.*")
VERSION_PATTERN = re.compile(r".*/ucsschool-kelvin-rest-api_(?P<date>.+).ini$")


def get_ini_urls(base_url):  # type: (str) -> Iterable[str]
    result = set()
    r = requests.get(base_url)
    assert r.status_code == 200
    for line in r.content.split("\n"):
        m = URL_PATTERN.match(line)
        if m:
            result.add(urljoin(base_url, m.groupdict()["component"]))
    return result


INI_URLS = sorted(itertools.chain(*(get_ini_urls(base_url) for base_url in BASE_URLS)))


def get_config(ini_url):  # type: (str) -> ConfigParser.ConfigParser
    r = requests.get(ini_url)
    assert r.status_code == 200
    with tempfile.NamedTemporaryFile() as fd:
        fd.write(r.content)
        fd.flush()
        fd.seek(0)
        config = ConfigParser.ConfigParser()
        config.readfp(fd)
    return config


def shorten_url(url):  # type: (str) -> str
    url_split = url.split("/")
    return "{}...{}".format(url_split[2].split(".", 1)[0], url_split[-1])


@pytest.mark.parametrize("ini_url", INI_URLS, ids=shorten_url)
def test_ini_settings(ini_url):
    version = int(VERSION_PATTERN.match(ini_url).groupdict()["date"])
    config = get_config(ini_url)

    assert config.get("Application", "ID") == "ucsschool-kelvin-rest-api"
    exp = {
        "/var/log/univention/ucsschool-kelvin-rest-api:/var/log/univention/ucsschool-kelvin-rest-api",
        "/var/lib/ucs-school-import/configs:/var/lib/ucs-school-import/configs",
        "/var/lib/ucs-school-import/kelvin-hooks:/var/lib/ucs-school-import/kelvin-hooks",
    }
    if version >= 20210518142444:
        exp.add("/var/lib/ucs-school-lib/kelvin-hooks:/var/lib/ucs-school-lib/kelvin-hooks")
    assert {v.strip() for v in config.get("Application", "DockerVolumes").split(",")} == exp
    if version <= 20200804122304:
        assert config.get("Application", "RequiredApps") == "ucsschool"
    else:
        assert config.get("Application", "RequiredApps") == ""
    assert config.get("Application", "WebInterfacePortHttp") == "8911"
    assert config.get("Application", "WebInterfaceProxyScheme") == "http"
    assert config.get("Application", "DockerImage").startswith(
        "docker.software-univention.de/ucsschool-kelvin-rest-api:"
    )
    if int(version) >= 20200827122150:
        exp = {"domaincontroller_master"}
    else:
        exp = {"domaincontroller_master", "domaincontroller_backup"}
    assert {r.strip() for r in config.get("Application", "ServerRole").split(",")} == exp
    assert config.get("Application", "WebInterfacePortHttps") == "8911"
    assert config.get("Application", "DockerShellCommand") == "/bin/ash"
    assert config.get("Application", "WebInterface") == "/ucsschool/kelvin"
    assert config.get("Application", "DockerScriptConfigure") == "/tmp/ucsschool-kelvin-configure"
    if version == 20210223082023:
        exp = {"groups/group", "users/user"}
    else:
        exp = {
            "settings/extended_attribute",
            "settings/extended_options",
            "settings/udm_module",
            "settings/udm_syntax",
        }
    assert {m.strip() for m in config.get("Application", "ListenerUdmModules").split(",")} == exp
