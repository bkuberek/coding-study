"""Two replicas, A and B, of one register; a client writes at A, then another reads at B.

A copies every write to B soon after, but this read comes before the copy arrives. A replica
that answers on its own replies in 1 ms; asking the other replica costs a round trip of 80 ms,
and fails when the link between them is cut. A "consistent" B asks A before it answers a read;
an "available" B answers from its own copy.
"""

LOCAL_MS, ROUND_TRIP_MS = 1, 80


def read_at_b(mode: str, link_up: bool) -> str:
    a, b = "v2", "v1"  # the write has landed at A; B still holds the old value
    if mode == "available":
        return f"{b} after {LOCAL_MS} ms (stale)"
    if not link_up:
        return "no answer: A cannot be reached"
    return f"{a} after {LOCAL_MS + ROUND_TRIP_MS} ms"


for link_up in (True, False):
    for mode in ("consistent", "available"):
        link = "link up " if link_up else "link cut"
        print(f"{link}, {mode:<10} B: {read_at_b(mode, link_up)}")
