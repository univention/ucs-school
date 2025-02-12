#!/usr/bin/python3
import os.path
import subprocess
from html import escape

from univention.lib.i18n import Translation
from univention.management.console.modules.diagnostic import Critical, Warning, main

_ = Translation("ucs-school-umc-diagnostic").translate

check_windows_compliance_tool_path = "/usr/share/ucs-school-lib/scripts/ucs-school-validate-usernames"

run_descr = ["This can be checked by running {}".format(check_windows_compliance_tool_path)]
title = _("Check if all present UCS@school usernames are supported.")
description = "\n".join(
    (
        _("This diagnostic check reviews all UCS@school usernames for compliance to username rules."),
        _("A warning is issued if a username is no longer supported or deprecated."),
    ),
)


def run(_umc_instance):
    """Required: Main entry point for UMC diagnostics plugin."""
    if not os.path.exists(check_windows_compliance_tool_path):
        raise Critical(
            description="".join(
                (
                    _("The diagnostic tool is not available at the following path: "),
                    check_windows_compliance_tool_path,
                    _(" Please update your UCS@school installation."),
                )
            )
        )

    try:
        check_username_validity_output = subprocess.check_output(  # nosec
            [check_windows_compliance_tool_path]
        )
    except subprocess.CalledProcessError:
        raise Critical(
            description=_("Diagnostic tool %s exited unexpectedly.") % check_windows_compliance_tool_path
        )
    check_username_validity_output = check_username_validity_output.decode("utf-8")
    check_username_validity_output_escaped = escape(check_username_validity_output)

    if _("Total number of invalid usernames:") in check_username_validity_output_escaped:
        raise Warning(
            description="{} {} {}\n{} {}:\n\n<pre>{}</pre>".format(
                _("Usernames have been detected which do not comply to user naming rules."),
                _(
                    "To fix this, change the usernames to a supported form. "
                    'Refer to the <a href="http://docs.software-univention.de/ucsschool-manual/5.0/de/'
                    'management/users.html" target="_blank" rel="noopener noreferrer">'
                    "administrators manual</a> for rules regarding usernames."
                ),
                _(
                    "Important: Support for names which do not comply to Windows naming conventions"
                    " is deprecated, and will be removed with UCS 5.2."
                ),
                _("The following is a list of all offending usernames, as retrieved by the tool "),
                check_windows_compliance_tool_path,
                check_username_validity_output_escaped,
            )
        )


if __name__ == "__main__":
    main()
