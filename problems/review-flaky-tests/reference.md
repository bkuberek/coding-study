# Review: Flaky Test Suite: Reference

Verdict: request changes. The production change (two lines in `renew_due`) is right. The tests do not protect it: the test for the new behavior asserts nothing, another test cannot fail, and the rest depend on the wall clock, on test order and on which xdist worker runs them. The suite-wide reruns would then hide all of that, and every future real intermittent failure in billing code. A strong review explains for each test how it can pass when the code is wrong or fail when it is right, and shows the deterministic version: fixed times passed as `now`, fresh data per test, mocks patched where they are looked up.

The shape to suggest:

```python
NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)

@pytest.fixture
def subscriptions():
    repo = InMemoryStore()          # a fresh store per test, injected into RenewalService
    ...
    return repo

def test_renews_due_subscriptions(subscriptions):
    charger = mock.create_autospec(Charger, instance=True)
    charger.charge.return_value = ChargeResult(ok=True, charge_id="ch_1")
    renewed = RenewalService(charger, subscriptions).renew_due(now=NOW)
    assert renewed == {"sub-1", "sub-2"}
```

To reproduce the flakiness locally: run the module several times with `-p randomly` and `-n 4`, or with a fixed `--randomly-seed` from a failing CI run.

## Blocker

- `test_renewals.py:61`: `charger.charge.assert_not_called` without parentheses only looks the method up; it asserts nothing. The one test of this PR's behavior passes even if paused subscriptions are charged (revert the `continue` and it still passes). Call it. In an isolated test it then checks the right thing; with the current shared fixture it would also start failing whenever an earlier test left `sub-1` due, which is the next issue.
- `test_renewals.py:41`: `mock.patch("billing.email.send_receipt")` patches the name in `billing.email`, but `renewals.py` did `from billing.email import send_receipt`, so `billing.renewals.send_receipt` still refers to the real function. The mock is never called whatever the code does, so `send_receipt.assert_not_called()` cannot fail. Patch where the name is looked up: `mock.patch("billing.renewals.send_receipt")`, and prove the patch works by asserting it is called in the success test.
- `pyproject.toml` `addopts = "-n auto --reruns 3"`: reruns for the whole suite turn every flaky test, and every intermittent real bug in billing code (races, ordering bugs), into a green build. A test that fails one run in four passes CI. Real failures also take four times as long. This is a team-wide policy change hidden in a feature PR: remove it here; if the team wants a stopgap, mark specific known-flaky tests with `@pytest.mark.flaky` and a ticket, and track flaky tests explicitly.

## Major

- `test_renewals.py:12-22` shared mutable fixture: `scope="module"` hands the same `Subscription` objects to every test, and tests mutate them (`test_failed_charge...` marks `sub-1` past due and moves its date; `test_paused...` moves `sub-3`; renewals move dates forward). Each test's outcome depends on which tests ran before it on the same worker. `store.add` also writes into the process-wide store and nothing removes the rows, so other test modules that call `store.due()` see them. Use a function-scoped fixture that builds fresh objects in a fresh store per test (inject the store, which `RenewalService` already supports), or reset the store in a `yield` fixture.
- `test_renewals.py:35-38` order dependence: `test_renewal_moves_the_next_renewal_date` reads `sub-1` from the global store and expects test 1 to have renewed it. Under pytest-randomly it fails whenever it runs first; under xdist it fails whenever it lands on another worker; run alone (`pytest -k next_renewal`) it fails because `sub-1` does not exist. Each test arranges its own data; fold this assertion into the renewal test, asserting that `renews_at` moved by exactly `RENEWAL_PERIOD` from its fixed starting value.
- `test_renewals.py:14` and `:27` wall-clock dependence: renewal dates come from `datetime.now()` when the module fixture first runs, then `time.sleep(1)` hopes they become due, then `renew_due()` reads the clock again. Whether a subscription is due depends on scheduling, machine load and wall-clock adjustments, and the module fixture's time depends on when the first test of the module happened to run. `renew_due` already takes `now`: pass fixed datetimes, delete the sleep, and test the boundary (`renews_at == now`) on purpose.
- `test_renewals.py:31`: `renew_due` returns a set, and the iteration order of a set of strings changes from process to process (hash randomization), so `list(renewed) == ["sub-1", "sub-2"]` fails in about half of the runs. Compare sets: `assert renewed == {"sub-1", "sub-2"}`.

## Minor

- `test_renewals.py:26`, `:43`, `:55`: bare `mock.Mock()` chargers accept any call, and `charge(...).ok` is a truthy `Mock`, so the first test takes the success path by accident, and the tests keep passing if `Charger.charge`'s signature changes. Use `mock.create_autospec(Charger, instance=True)` with an explicit `ChargeResult` return value, or a small fake charger that records calls.
- `test_renewals.py:27`: `time.sleep(1)` slows every run; fixed times remove it.
- Missing cases: a successful renewal sends a receipt with the charge id; a failed charge does not move `renews_at`; a paused subscription is neither charged, renewed nor marked past due; the `renews_at == now` boundary; renewed subscriptions are saved through the store.
- `renewals.py:16` (pre-existing): `now or datetime.now()` uses naive local time. Ask how `renews_at` is stored; if it is UTC, use aware UTC datetimes in the code and the tests, as a follow-up.

## Nit

- `renewals.py:19-20`: consider filtering paused subscriptions in `due()` (the query) so they are never loaded; ask whether other callers of `due()` should see them.
- `test_renewals.py:41-42`: with `mock.patch` as a decorator, the mock argument comes before fixtures; the context-manager form (or pytest-mock's `mocker`) reads more clearly next to fixtures.
- Test data: `price_cents=999` repeated; a small factory (`make_subscription(id, status="active", renews_at=NOW)`) keeps each test focused on what differs.
