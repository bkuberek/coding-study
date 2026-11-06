# Authorization Policy Engine

## Statement

Every request in a document platform asks one question before it does anything: may this principal perform this action on this resource? The answer comes from rules that administrators write as data, so the code has to give the same answer no matter what order they wrote them in, and it has to fail closed when no rule speaks.

Implement `PolicyEngine`:

- `inherit(role, parentRole)`: `role` gets every rule of `parentRole`, directly or through further parents. `parentRole` gets nothing from `role`.
- `assignRole(principal, role)`: `principal` holds `role`. A principal may hold several roles.
- `addRule(role, effect, action, resource)`: adds a rule to `role`. `effect` is `allow` or `deny`.
- `check(principal, action, resource)`: decides, as below, and returns `"allow"`, `"deny"` or `"default-deny"`.

A rule **applies** to a check when all three of these hold:

1. **Role.** The principal holds the rule's role, or holds a role that reaches it through `inherit` in any number of steps.
2. **Action.** The rule's action equals the requested action, or is `*`, which stands for every action.
3. **Resource.** The rule's resource equals the requested resource, or is one of its ancestors, or is `*`, which stands for every resource. Resources are paths of segments separated by `/`, and each ancestor drops whole segments from the end: `docs/alpha` is an ancestor of `docs/alpha/q3`, but not of `docs/alphabet`.

The decision then has three steps:

1. If any applicable rule is a `deny`, the result is `"deny"`. How specific the rule is, which role it came from and when it was added make no difference. A deny on `docs` beats an allow on `docs/alpha/q3`.
2. Otherwise, if any applicable rule is an `allow`, the result is `"allow"`.
3. Otherwise the result is `"default-deny"`. A caller refuses this as it refuses `"deny"`. The two are kept apart so an audit log can show whether a rule refused the request or no rule spoke.

**Cycles are allowed.** The rules come from people, and `inherit` does not refuse a cycle: `inherit("a", "b")` followed by `inherit("b", "a")` is legal, and it means that `a` and `b` have the same rules. `check` must finish and answer correctly when the roles contain one.

Every call takes effect at once: `check` always answers from everything added so far.

## Input

- `role`, `parentRole`, `principal`: names. A name needs no declaring: a role with no rules, or a principal with no roles, simply has nothing that applies.
- `effect`: `allow` or `deny`.
- `action`: an action name, or `*` in a rule.
- `resource`: a path of segments separated by `/`, or `*` in a rule.

Names are compared exactly, including case. Each test is a sequence of calls: the constructor first, then the other calls in order.

## Output

One result per call: `null` for every call but `check`, which returns `"allow"`, `"deny"` or `"default-deny"`.

## Examples

### Example 1

<!-- case: ex1 -->

`editor` inherits `viewer`, so `dana` may `read` anything under `docs`, and `write` anything under `docs/alpha`. `write` on `docs/beta` has no rule, which is a `"default-deny"`. `viewer` does not inherit from `editor`, so `viewer` holders do not get `write`.

### Example 2

<!-- case: ex2 -->

The allow on `docs/alpha/q3` is more specific than the deny on `docs/alpha`, and it was added later. Neither matters: a deny that applies wins. The deny says nothing about `docs/beta`, so the allow on `docs` still decides there.

### Example 3

<!-- case: ex3 -->

`auditor` and `reviewer` inherit each other, so a principal who holds either one has the rules of both.

## Constraints

- At most `10^4` calls, and at most 1000 distinct roles.
- Names and action names are 1 to 40 characters long, with no `/`. A requested action is never `*`, and a rule's action or resource uses `*` only as its whole value.
- A resource has 1 to 20 segments. Segments are not empty and are never `.` or `..`.

## Follow-ups

- Resources arrive here already normalized. Where should `docs/alpha/../beta` be normalized, and what goes wrong if the policy check sees it first?
- Return which rule decided, for the audit log.
- Add a wildcard for one segment (`docs/*/q3`). What happens to the ancestor lookup?
- Many checks and few changes: precompute each role's effective rules. What must be invalidated when `inherit` adds an edge, and how do cycles change the computation?

## Hints

### Hint 1

Separate three questions: which roles does the principal really hold, which resources count as covering this one, and which rules match both.

### Hint 2

One visited set, for the whole walk over the roles. That single set handles a cycle, and it also handles many paths that lead to the same role.

### Hint 3

Do not stop at the first applicable rule unless it is a deny.
