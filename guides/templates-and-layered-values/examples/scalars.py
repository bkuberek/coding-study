"""What a value pasted unquoted into YAML becomes, under the 1.2 core schema and the 1.1 booleans.

A plain (unquoted) scalar is resolved by matching it against regular expressions; the first match
picks its type, and no match leaves it a string. The patterns below are copied from the YAML
1.2.2 core schema (section 10.3.2), except the infinity and not-a-number rows, and from the YAML
1.1 boolean type. Quoting the value as a JSON string keeps it a string, since a JSON string is
also a YAML 1.2 string.
"""

import json
import re

CORE_1_2 = [
    ("null", r"null|Null|NULL|~|"),
    ("bool", r"true|True|TRUE|false|False|FALSE"),
    ("int", r"[-+]?[0-9]+"),
    ("int (octal)", r"0o[0-7]+"),
    ("int (hex)", r"0x[0-9a-fA-F]+"),
    ("float", r"[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?"),
]
BOOL_1_1 = r"y|Y|yes|Yes|YES|n|N|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF"


def resolve_1_2(text: str) -> str:
    return next((tag for tag, pattern in CORE_1_2 if re.fullmatch(pattern, text)), "str")


for value in ["no", "on", "1.10", "007", "0x1A", "12e3", "true", "web-1"]:
    as_1_1 = "bool" if re.fullmatch(BOOL_1_1, value) else "-"
    print(f"{value:6} 1.2 core: {resolve_1_2(value):12} 1.1 bool: {as_1_1:5}"
          f" quoted: {json.dumps(value)}")
