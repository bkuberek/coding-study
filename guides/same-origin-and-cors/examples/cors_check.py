"""The browser's side of CORS, run against four ways a server might answer.

The check follows the Fetch standard's CORS check: the browser shares a response with the page
only when Access-Control-Allow-Origin allows the page's origin, and, for a request that carried
cookies, only when the response also says Access-Control-Allow-Credentials: true.
"""


def browser_shares(page_origin: str, with_cookies: bool, headers: dict) -> bool:
    allowed = headers.get("Access-Control-Allow-Origin")
    if allowed is None:
        return False
    if not with_cookies and allowed == "*":
        return True
    if allowed != page_origin:
        return False
    if not with_cookies:
        return True
    return headers.get("Access-Control-Allow-Credentials") == "true"


def wildcard(origin: str) -> dict:
    return {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true"}


def echo_any(origin: str) -> dict:
    return {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"}


def ends_with(origin: str) -> dict:
    return echo_any(origin) if origin.endswith("bank.example") else {}


def exact_set(origin: str) -> dict:
    return echo_any(origin) if origin in {"https://app.bank.example"} else {}


pages = {
    "own": "https://app.bank.example",
    "evil": "https://evil.example",
    "look-alike": "https://notbank.example",
    "opaque": "null",
}
for label, origin in pages.items():
    print(f"{label:10} = {origin}")
print()
print("server     cookies  " + "".join(f"{label:12}" for label in pages).rstrip())
for server in (wildcard, echo_any, ends_with, exact_set):
    for with_cookies in (False, True):
        row = f"{server.__name__:10} {'yes' if with_cookies else 'no':8} "
        for origin in pages.values():
            row += f"{'reads' if browser_shares(origin, with_cookies, server(origin)) else '-':12}"
        print(row.rstrip())
