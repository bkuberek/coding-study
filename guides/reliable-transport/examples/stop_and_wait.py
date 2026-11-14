"""A stop-and-wait sender and its receiver, over a network simulated in memory.

The sender numbers every byte, sends one segment, and waits for the acknowledgement. If none
comes back before its timer expires, it sends the same segment again. The receiver acknowledges
cumulatively: its ACK carries the number of the next byte it expects. The network is a list of
fates, one per packet in either direction, so every run is the same.
"""

ONE_WAY_MS = 50  # time for a packet to cross the network
TIMEOUT_MS = 300  # fixed here; the guide's next example computes it from measurements


class Network:
    def __init__(self, fates: list[str]) -> None:
        self.fates = fates

    def carries(self) -> bool:
        return self.fates.pop(0) == "ok"


class Receiver:
    def __init__(self) -> None:
        self.next_seq = 0
        self.delivered = b""

    def on_segment(self, seq: int, data: bytes) -> tuple[int, str]:
        if seq == self.next_seq:
            self.delivered += data
            self.next_seq += len(data)
            return self.next_seq, "delivers it"
        # with one segment in flight nothing arrives early: this is a copy of an old one
        return self.next_seq, "drops a duplicate"


def send(message: bytes, size: int, network: Network) -> tuple[bytes, int]:
    receiver, now, seq = Receiver(), 0, 0
    while seq < len(message):
        data = message[seq : seq + size]
        line = f"{now:>5} ms  send seq {seq:>2} {data!r:<9} -> "
        if not network.carries():
            print(line + f"lost; timer expires at {now + TIMEOUT_MS} ms")
            now += TIMEOUT_MS
            continue
        ack, action = receiver.on_segment(seq, data)
        if not network.carries():
            print(
                line + f"receiver {action}, ACK {ack} lost; timer expires at {now + TIMEOUT_MS} ms"
            )
            now += TIMEOUT_MS
            continue
        now += 2 * ONE_WAY_MS
        print(line + f"receiver {action}, ACK {ack} back at {now} ms")
        seq = ack
    return receiver.delivered, now


fates = ["ok", "ok", "lost", "ok", "lost", "ok", "ok", "ok", "ok"]
delivered, finished = send(b"Hello, network!", 5, Network(fates))
print(f"delivered {delivered!r} by {finished} ms; without losses it takes {3 * 2 * ONE_WAY_MS} ms")
