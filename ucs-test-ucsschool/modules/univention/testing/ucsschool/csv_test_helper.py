#!/usr/bin/python3
import codecs
import random
import string


def get_test_chars(encoding):
    if encoding in ["binary", "ascii"]:
        return string.ascii_letters
    elif encoding == "latin-1":
        return "".join([chr(i) for i in random.sample(range(128, 256), 20) if chr(i).isprintable()])
    else:
        # use some foreign letters
        return "ΆΕΔΦβθψϞϨϦϿϾ"


def write_formatted_csv(fn_csv, input_encoding, content):
    with open(fn_csv, "wb") as g:
        if input_encoding == "utf-8-sig":
            csv_content = bytes(content, encoding=input_encoding)
        elif input_encoding == "utf-16-be":
            csv_content = codecs.BOM_UTF16_BE + bytes(content, encoding=input_encoding)
        elif input_encoding == "utf-16-le":
            csv_content = codecs.BOM_UTF16_LE + bytes(content, encoding=input_encoding)
        elif input_encoding == "utf-16-no-bom":
            # simulating UTF-16 file without BOM
            csv_content = bytes(content, encoding="utf-16-be")
        else:
            csv_content = codecs.encode(content, encoding=input_encoding)

        g.write(csv_content)
