"""A consumer's contract, checked against its own fake and against each version of the provider.

The billing code reads accounts from another team's service. Its unit tests use a fake of that
service, which is fast and never fails for network reasons, but can drift from the real thing.
The contract lists only what billing relies on, and the same check runs against the fake and
the real provider, so a drift shows up as a failing contract, not as a bill gone wrong.
"""

CONTRACT = {  # field -> type, for what billing reads from an account
    "id": str,
    "plan": str,
    "seats": int,
}


def fake_account(account_id: str) -> dict:
    """The fake billing's unit tests use."""
    return {"id": account_id, "plan": "team", "seats": 5}


def provider_v1(account_id: str) -> dict:
    return {"id": account_id, "email": "ops@example.org", "plan": "team", "seats": 5,
            "created": "2026-03-01"}


def provider_v2(account_id: str) -> dict:  # drops a field billing never reads
    return {"id": account_id, "plan": "team", "seats": 5, "created": "2026-03-01"}


def provider_v3(account_id: str) -> dict:  # renames plan to tier, sends seats as text
    return {"id": account_id, "tier": "team", "seats": "5", "created": "2026-03-01"}


def check_contract(get_account) -> list[str]:
    account = get_account("acct-7")
    problems = []
    for field, kind in CONTRACT.items():
        if field not in account:
            problems.append(f"missing {field}")
        elif not isinstance(account[field], kind):
            problems.append(f"{field} is {type(account[field]).__name__}, not {kind.__name__}")
    return problems


for source in (fake_account, provider_v1, provider_v2, provider_v3):
    problems = check_contract(source)
    print(f"{source.__name__:<13} {'ok' if not problems else 'broken: ' + '; '.join(problems)}")
