# Review: Flaky Test Suite

## Context

The billing service (Python 3.12) runs a nightly job that renews subscriptions through `RenewalService.renew_due`. This pull request makes renewals skip paused subscriptions and adds the first tests for `RenewalService`. CI has been failing intermittently in other billing tests for weeks.

Facts about the codebase that are not visible in the diff:

- CI runs `pytest` with pytest-randomly (random test order, new seed each run) and pytest-xdist (`-n auto`: tests are spread over several worker processes).
- In tests, `billing.store` is an in-memory repository module shared by every test in the same process: `add`, `get`, `save`, and `due(now)`, which returns subscriptions with `renews_at <= now` in insertion order. Nothing resets it between tests.
- `Charger.charge(customer_id, amount_cents)` in `billing/charging.py` returns `ChargeResult(ok: bool, charge_id: str | None)`.
- `billing.email.send_receipt` calls the email provider; the test settings route it to the console.

## Pull request

**Skip paused subscriptions when renewing**

> Paused subscriptions were being charged. `renew_due` now skips them. Added tests for `RenewalService` (renewal, next date, failed charge, paused). CI has been flaky, so I enabled pytest-rerunfailures with 3 reruns for the whole suite to stabilize it.

## Task

Review the change as you would a teammate's pull request, in about 30 minutes. For each issue, give its location, its severity (blocker, major, minor or nit), why the test can pass when the code is wrong (or fail when it is right), and the change you would ask for. End with your overall verdict.
