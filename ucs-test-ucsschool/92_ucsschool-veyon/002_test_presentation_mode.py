#!/usr/share/ucs-test/runner /usr/bin/pytest-3 -l -v
## desc: test veyon presentation mode
## tags: [ucs_school_veyon]
## exposure: dangerous
## packages: [ucs-school-veyon-client]
## bugs: [53558]

import time


def test_normal_feature_change(
    windows_client, get_veyon_client, wait_for_demo_mode, set_demo_mode
):
    client = get_veyon_client(windows_client)
    print(client.get_user_info())
    wait_for_demo_mode(client, False)
    print("Check normal feature change")
    print("start demo")
    set_demo_mode(client, True)
    wait_for_demo_mode(client, True)
    print("stop demo")
    set_demo_mode(client, False)
    wait_for_demo_mode(client, False)
    print("normal feature change ok")


def test_reconnect_feature_change(
    windows_client, get_veyon_client, wait_for_demo_mode, set_demo_mode
):
    client = get_veyon_client(windows_client)
    print(client.get_user_info())
    wait_for_demo_mode(client, False)
    print("check feature change with api restart")
    print("start demo")
    set_demo_mode(client, True)
    wait_for_demo_mode(client, True)
    time.sleep(5)
    print("reconnect with other client")
    other_client = get_veyon_client(windows_client)
    wait_for_demo_mode(other_client, True)  # Need to wait until features are loaded?
    print("stop demo")
    set_demo_mode(other_client, False)
    wait_for_demo_mode(other_client, False)
    print("OK :-)")
