from __future__ import print_function

import tempfile

from univention.testing.ucsschool.computerroom import run_commands


def write_peap_config_file(conf_file, username, password):
    content = """network={
    key_mgmt=WPA-EAP
    eap=PEAP
    identity="%s"
    anonymous_identity="anonymous"
    password="%s"
    phase2="autheap=MSCHAPV2"\n}""" % (
        username,
        password,
    )
    conf_file.write(content)


def peap_auth(username, password, radius_secret):
    peap_conf_file = tempfile.NamedTemporaryFile("w+", suffix=".conf", dir="/tmp")
    print(" ** Creating temp config file %s" % peap_conf_file.name)
    write_peap_config_file(peap_conf_file, username, password)
    peap_conf_file.flush()
    peap_auth_cmd = ["eapol_test", "-c", "%(peap_conf_file)s", "-s", "%(radius_secret)s"]
    result = run_commands(
        [peap_auth_cmd], {"peap_conf_file": peap_conf_file.name, "radius_secret": radius_secret}
    )
    return result[0] == 0


def test_peap_auth(username, password, radius_secret, should_succeed=True):
    print(
        "*** PEAP AUTH: user: %s, password: %s, should_succeed: %r"
        % (
            username,
            password,
            should_succeed,
        ),
        "-" * 40,
    )
    auth_result = peap_auth(username, password, radius_secret)
    assert (
        auth_result == should_succeed
    ), "PEAP authentication unexpected result (%r), while the expected is (%r)\nUser=%s" % (
        auth_result,
        should_succeed,
        username,
    )
