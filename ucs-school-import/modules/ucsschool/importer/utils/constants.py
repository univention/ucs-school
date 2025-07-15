MAX_LEGAL_GUARDIANS = 4
MAX_LEGAL_WARDS = 10


def get_default_prefixlen():
    # IP address prefix len concerning the netmask
    return 24


def get_sep_char():
    # separator char in infile (default: \t for Tabulator)
    return "\t"
