# Review: Flaky Test Suite: Rubric

## Finding the issues

- [ ] Flags `assert_not_called` without parentheses as an assertion that never runs.
- [ ] Flags the patch of `billing.email.send_receipt` as the wrong target, explaining `from ... import` binding.
- [ ] Flags suite-wide reruns as hiding flaky tests and real intermittent bugs.
- [ ] Flags the module-scoped fixture whose objects tests mutate.
- [ ] Flags state leaking through the process-wide store to other tests and modules.
- [ ] Flags the test that depends on another test having run first, and connects it to random order and xdist.
- [ ] Flags `datetime.now()` plus `time.sleep` as wall-clock dependence.
- [ ] Flags comparing a set's iteration order to a list.
- [ ] Flags bare `Mock()` chargers whose truthy results take the success path by accident.

## Prioritization

- [ ] Treats tests that cannot fail as blockers: they give false confidence on a billing path.
- [ ] Separates the correct production change from the problems in the tests.
- [ ] Flags the reruns policy as a team decision that does not belong in this PR.

## Actionable comments

- [ ] Shows the deterministic alternative: fixed datetimes passed as `now`, no sleeps.
- [ ] Proposes function-scoped fixtures with a fresh, injected store.
- [ ] Gives the correct patch target and a way to prove the patch works (assert it is called on the success path).
- [ ] Suggests `create_autospec` or a fake charger with explicit results.
- [ ] Explains how to reproduce the flakiness locally (seed, workers).

## Tone and collaboration

- [ ] Acknowledges that adding the first tests for `RenewalService` is valuable and the production fix is right.
- [ ] Explains each flaky mechanism as a scenario (which order or process makes it fail) rather than a rule.

## Asking about intent

- [ ] Asks whether paused subscriptions should be filtered in `due()` instead.
- [ ] Asks how the team wants to handle known flaky tests (quarantine with tickets) instead of global reruns.
