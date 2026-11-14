"""How a record's TTL trades queries against stale answers.

A name's address changes at second 610. Clients ask a caching resolver for it every 30 seconds
for an hour. The resolver asks the authoritative server only when its cached copy has expired,
and a copy expires TTL seconds after it arrived. A long TTL saves queries; it also keeps the
old address in use for longer after the change.
"""

OLD, NEW = "192.0.2.10", "192.0.2.20"
CHANGE_AT, END, EVERY = 610, 3600, 30


def run(ttl: int) -> tuple[int, int | None]:
    cached: tuple[str, int] | None = None  # (address, time the copy expires)
    upstream, last_stale = 0, None
    for now in range(0, END, EVERY):
        current = OLD if now < CHANGE_AT else NEW
        if cached is None or now >= cached[1]:
            upstream += 1
            cached = (current, now + ttl)
        if cached[0] != current:
            last_stale = now
    return upstream, last_stale


print("TTL (s)  queries to the server  last old answer (s)")
for ttl in (60, 300, 3600):
    upstream, last_stale = run(ttl)
    stale = "none" if last_stale is None else str(last_stale)
    print(f"{ttl:>7}  {upstream:>21}  {stale:>19}")
