"""Handing data to a page's script as JSON in a data block, with <, > and & escaped."""

import json

profile = {"name": "Zoë</script><script>steal()</script>", "team": "R&D"}

plain = json.dumps(profile)
print("json.dumps:      ", plain)
print("closes the block:", "</script" in plain.lower())

escaped = plain.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
print("escaped:         ", escaped)
print("closes the block:", "</script" in escaped.lower())
print("same data back:  ", json.loads(escaped) == profile)

page = f'<script type="application/json" id="profile">{escaped}</script>'
print(page)
