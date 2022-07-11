#!/usr/bin/python3


def filter_deprecated(stderr):
    errors = []
    for line in stderr.splitlines():
        if line.endswith('WARNING: The "blocking locks" option is deprecated'):
            continue
        if line.endswith('WARNING: Using password on command line is insecure. Please install the setproctitle python module.'):
            continue
        else:
            errors.append(line)
    return "\n".join(errors).strip()
