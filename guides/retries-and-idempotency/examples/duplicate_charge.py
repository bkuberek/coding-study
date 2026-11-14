"""Why a retry can charge a card twice, and how an idempotency key prevents it.

The server does the work and answers, and the network loses the answer. The client sees only a
timeout: it cannot tell a request that never arrived from an answer that never came back, so it
retries. Without a key the server charges again. With a key it finds the answer it gave the
first time and sends that again, without charging.
"""


class PaymentServer:
    def __init__(self) -> None:
        self.charges: list[int] = []
        self.answers: dict[str, str] = {}  # idempotency key -> the answer first given

    def charge(self, cents: int, key: str | None) -> str:
        if key is not None and key in self.answers:
            return self.answers[key]
        self.charges.append(cents)
        answer = f"charge #{len(self.charges)} of {cents} cents ok"
        if key is not None:
            self.answers[key] = answer
        return answer


def call_with_retries(server: PaymentServer, cents: int, key: str | None, lost: set[int]) -> None:
    for attempt in range(1, 4):
        answer = server.charge(cents, key)
        if attempt in lost:
            print(f"  attempt {attempt}: no answer before the timeout")
            continue
        print(f"  attempt {attempt}: {answer}")
        return


for key in (None, "order-41-payment"):
    server = PaymentServer()
    print(f"key {key}:")
    call_with_retries(server, 2500, key, lost={1})
    print(f"  the card was charged {len(server.charges)} time(s): {server.charges}")

server = PaymentServer()
server.charge(2500, "order-41-payment")
print("same key, different amount:", server.charge(9900, "order-41-payment"))
