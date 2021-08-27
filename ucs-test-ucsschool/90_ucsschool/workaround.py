#!/usr/bin/python3

def filter_deprecated(stderr):
    errors = []
    for line in stderr.splitlines():
          if line.endswith('WARNING: The "blocking locks" option is deprecated'):
              continue
          else:
              errors.append(line)
    return '\n'.join(errors).strip()


