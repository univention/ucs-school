#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## -*- coding: utf-8 -*-
## desc: Integration tests running on the host (users and groups)
## tags: [ucsschool-bff-groups, ucsschool-bff-users]
## packages: [ucs-school-ui-groups-frontend, ucs-school-ui-users-frontend]
## exposure: dangerous

import time
from types import SimpleNamespace

import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from univention.config_registry import ConfigRegistry


@pytest.fixture()
def portal_config(ucr: ConfigRegistry) -> SimpleNamespace:
    config = {
        "url": f"https://{ucr['hostname']}.{ucr['domainname']}/univention/portal",
        "title": "Univention Portal",
        "sso_login_tile": "Login (Single sign-on)",
        "tile_name_class": "portal-tile__name",
        "category_title_class": "portal-category__title",
        "categories_id": "portalCategories",
        "tile_class": "portal-tile",
        "groups_tile": "School groups",
        "users_tile": "School users",
        "username": "admin",
        "password": "univention",
    }

    return SimpleNamespace(**config)


@pytest.fixture()
def keycloak_config(ucr: ConfigRegistry) -> SimpleNamespace:
    url = f"https://ucs-sso-ng.{ucr['domainname']}"
    config = {
        "url": url,
        "token_url": f"{url}/realms/master/protocol/openid-connect/token",
        "client_session_stats_url": f"{url}/admin/realms/ucs/client-session-stats",
        "logout_all_url": f"{url}/admin/realms/ucs/logout-all",
        "login_data": {
            "client_id": "admin-cli",
            "username": "Administrator",
            "password": "univention",
            "grant_type": "password",
        },
        "logout_all_data": {"realm": "ucs"},
        "clients": ["ucs-school-ui-users", "ucs-school-ui-groups"],
    }
    return SimpleNamespace(**config)


@pytest.fixture()
def selenium() -> webdriver.Chrome:
    """Browser based testing for using Selenium."""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")  # chrome complains about being executed as root
    chrome_options.add_argument("ignore-certificate-errors")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


@pytest.fixture()
def ucr() -> ConfigRegistry:
    ucr = ConfigRegistry()
    return ucr.load()


@pytest.fixture()
def portal(selenium: webdriver.Chrome, portal_config: SimpleNamespace) -> webdriver.Chrome:
    selenium.get(portal_config.url)
    wait_for_id(selenium, portal_config.categories_id)
    assert selenium.title == portal_config.title
    return selenium


def wait_for(driver: WebDriver, by: By, element: str, timeout: int = 60) -> None:
    element_present = EC.presence_of_element_located((by, element))
    WebDriverWait(driver, timeout).until(element_present)
    WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, element)))
    time.sleep(1)


def wait_for_id(driver: WebDriver, element_id: str, timeout: int = 60) -> WebElement:
    wait_for(driver, By.ID, element_id, timeout)
    return driver.find_element_by_id(element_id)


def wait_for_class(driver: WebDriver, element_class: str, timeout: int = 60) -> WebElement:
    wait_for(driver, By.CLASS_NAME, element_class, timeout)
    return driver.find_elements_by_class_name(element_class)


def get_portal_tile(driver: WebDriver, text: str) -> WebElement:
    for tile in driver.find_elements_by_class_name("portal-tile__name"):
        if tile.text == text:
            return tile


def keycloak_auth_header(config: SimpleNamespace) -> dict:
    response = requests.post(config.token_url, data=config.login_data)
    assert response.status_code == 204, response.text
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {response.json()['access_token']}",
    }


def keycloak_sessions(config: SimpleNamespace) -> dict:
    response = requests.get(config.client_session_stats_url, headers=keycloak_auth_header(config))
    assert response.status_code == 204, response.text
    return response.json()


def keycloak_logout_all(config: SimpleNamespace) -> None:
    response = requests.post(
        config.logout_all_url,
        headers=keycloak_auth_header(config),
        data=config.logout_all_data,
    )
    assert response.status_code == 204, response.text


def test_portal_sso_slo_keycloak_sessions(portal, portal_config, keycloak_config):
    # check no active session in keycloak
    keycloak_logout_all(keycloak_config)
    for session in keycloak_sessions(keycloak_config):
        if session["clientId"] in keycloak_config.clients:
            assert int(session.get("active", 0)) == 0

    # login
    get_portal_tile(portal, portal_config.sso_login_tile).click()
    wait_for_id(portal, "umcLoginUsername")
    portal.find_element_by_id("umcLoginUsername").send_keys(portal_config.username)
    portal.find_element_by_id("umcLoginPassword").send_keys(portal_config.password)
    portal.find_element_by_class_name("umcLoginFormButton").click()

    # open apps
    wait_for_id(portal, portal_config.categories_id)
    groups = get_portal_tile(portal, portal_config.groups_tile)
    users = get_portal_tile(portal, portal_config.users_tile)

    # groups app
    groups.click()
    wait_for_id(portal, "iframe-1")
    portal.switch_to.frame("iframe-1")
    wait_for_id(portal, "app")
    heading = wait_for_class(portal, "listView__heading")
    assert "Gruppen" in heading[0].text
    portal.switch_to.default_content()
    wait_for_id(portal, "portalTitle").click()

    # users app
    users.click()
    wait_for_id(portal, "iframe-2")
    portal.switch_to.frame("iframe-2")
    wait_for_id(portal, "app")
    heading = wait_for_class(portal, "listView")
    assert "Benutzer" in heading[0].text.split("\n")
    portal.switch_to.default_content()
    wait_for_id(portal, "portalTitle").click()

    # check active sessions in keycloak
    for session in keycloak_sessions(keycloak_config):
        if session["clientId"] in keycloak_config.clients:
            assert int(session.get("active", 0)) > 0

    # logout
    wait_for_id(portal, "header-button-menu").click()
    wait_for_class(portal, "portal-sidenavigation__logout-link")[0].click()
    get_portal_tile(portal, portal_config.sso_login_tile)

    # check logout, no more active sessions in keycloak
    for session in keycloak_sessions(keycloak_config):
        if session["clientId"] in keycloak_config.clients:
            assert int(session.get("active", 0)) == 0
