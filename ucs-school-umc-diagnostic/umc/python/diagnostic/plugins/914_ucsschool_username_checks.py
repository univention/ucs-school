#!/usr/bin/python3
import os.path
import subprocess

from univention.lib.i18n import Translation
from univention.management.console.modules.diagnostic import Critical, Warning, main

_ = Translation("ucs-school-umc-diagnostic").translate

check_windows_compliance_tool_path = "/usr/share/ucs-school-lib/scripts/ucs-school-validate-usernames"

run_descr = ["This can be checked by running {}".format(check_windows_compliance_tool_path)]
title = _("Check if all present UCS@school usernames are supported.")
description = "\n".join(
    (
        _("This diagnostic check reviews all UCS@school usernames for compliance username rules."),
        _("A warning is issued if a username is no longer supported or deprecated."),
    ),
)


def run(_umc_instance):
    """Required: Main entry point for UMC diagnostics plugin."""
    if not os.path.exists(check_windows_compliance_tool_path):
        raise Warning(
            description="".join(
                (
                    _("The diagnostic tool is not available at the following path: "),
                    check_windows_compliance_tool_path,
                    _(" Please update your UCS@school installation."),
                )
            )
        )

    try:
        number_of_non_compliant_usernames = subprocess.check_output(  # nosec
            [check_windows_compliance_tool_path, "--silent"]
        )
    except subprocess.CalledProcessError:
        raise Critical(
            description=_("Diagnostic tool %s exited unexpectedly.") % check_windows_compliance_tool_path
        )

    try:
        number_of_non_compliant_usernames = int(number_of_non_compliant_usernames)
    except ValueError:
        raise Critical(description=_("Unexpected problem during output conversion."))

    if number_of_non_compliant_usernames > 0:
        raise Warning(
            description="{} {} {} {}\n{} {} {}".format(
                number_of_non_compliant_usernames,
                _("usernames have been detected which do not comply to Windows naming conventions."),
                _("Support for these names is deprecated, and will be removed with UCS 5.2."),
                _(
                    "To fix this, change the usernames to a supported form. "
                    "Refer to the administrators manual for rules regarding usernames."
                ),
                _("To retrieve a list of all offending usernames, use the tool"),
                check_windows_compliance_tool_path,
                _(" with the verbose mode option (-v)."),
            )
        )


if __name__ == "__main__":
    main()
