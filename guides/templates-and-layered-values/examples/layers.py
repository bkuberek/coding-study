"""Layers of values looked up in order, the nested value a shallow lookup loses, a missing value.

ChainMap searches its mappings from the first to the last and returns the first value it finds,
so the most specific layer goes first. It never looks inside a nested dictionary: a nested value
in an upper layer hides the whole nested value below it.
"""

from collections import ChainMap
from string import Template

defaults = {"replicas": 1, "port": 8080, "image": {"repo": "shop/web", "tag": "1.4"}}
production = {"replicas": 3, "image": {"tag": "1.5"}}
values = ChainMap(production, defaults)

print("replicas:", values["replicas"], "| port:", values["port"])
print("image:", values["image"], "<- the repo from defaults is gone")

template = Template("image: $repo:$tag\nreplicas: $replicas")
flat = {"replicas": values["replicas"], **values["image"]}
try:
    print(template.substitute(flat))
except KeyError as missing:
    print("substitute refuses, missing", missing)
print(template.safe_substitute(flat).replace("\n", " | "), "<- safe_substitute ships it")
