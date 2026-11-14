"""A client asks a server, across a network, to add 10 to a balance of 100.

Five things can happen to one request: it is delivered and answered, the request is lost, the
server crashes before or after doing the work, or the reply is lost. The client waits for a
reply; when none comes before its timeout, it may retry once. The table shows what the client
saw and what the balance became, with and without that retry.
"""

FATES = ["delivered", "request lost", "crash before work", "crash after work", "reply lost"]


def send(fate: str, retry: bool) -> tuple[str, int]:
    balance = 100

    def attempt(fate: str) -> bool:  # True when a reply reaches the client
        nonlocal balance
        if fate in ("request lost", "crash before work"):
            return False
        balance += 10  # the server did the work
        return fate == "delivered"

    if attempt(fate):
        return "ok", balance
    if not retry:
        return "timeout", balance
    attempt("delivered")  # the retry gets through
    return "timeout, then ok", balance


print(f"{'what happened':<18} {'client saw':<17} {'no retry':>8} {'one retry':>9}")
for fate in FATES:
    seen, once = send(fate, retry=False)
    _, twice = send(fate, retry=True)
    print(f"{fate:<18} {seen:<17} {once:>8} {twice:>9}")
