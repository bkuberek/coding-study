# Loop Controller: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| state-machine | optimal | O(L) for L the total length of the steps' texts | O(n) for n steps | default answer; one pass over the steps with a handful of counters and two ordered lists of checks |

Here `L` is the total length of the texts in the steps that are executed (the arguments and the results are read once each), and `n` is the number of steps, since the trace keeps one row for each.

## How the design grows level by level

| Level | Change | What the pass adds |
|-------|--------|--------------------|
| 1 | Stop at `final`, at the cap, or when the steps end | The loop itself, an iteration counter, and the first of the two ordered lists of checks |
| 2 | Stop on repeated identical failures | A canonical form of a failure, the previous failure and a streak counter |
| 3 | Token and time budgets | Two running totals, a `>=` test before a step and a `>` test after it, and the rows of `tripped` |
| 4 | A claim of done must pass a check | A function from a step to an outcome and feedback, a rejected claim treated as a failure, and a trace built as the loop goes |

The design choice that carries the whole problem is to see the loop as **two ordered lists of questions**: the ones asked before an iteration (cap, budgets, steps left) and the ones asked after a step (final, budgets, no progress). Every level adds a question to one of the lists, and the order of the lists is the answer to "what if two are true at once". A first version that scatters the stops through the loop with `if ... break` works until the order matters, and then nobody can say which stop wins.

## Approach: state-machine (One pass with a streak counter and ordered checks)

### Intuition

A harness loop is a small state machine: its state is a handful of numbers (iterations, tokens, milliseconds, the last failure and how many times in a row it happened), and each step moves it forward. The brakes are predicates on that state. Because the steps are given as data, the machine is deterministic, and the interesting design is not the loop but the **definitions**: what makes two failures "the same", when a budget counts as "used up", and which stop is reported when several are true.

### Algorithm

1. At the start of `run`, create a fresh record with the counters at zero, the reason empty and empty reports. Keep configuration (the no-progress limit, the budgets, the check) on the controller, and the record of the last run next to it.
2. Loop. Before a step, ask in order: have `maxIterations` iterations run (`max_iterations`)? Is the token total at or above its limit (`token_budget`)? Is the time total at or above its limit (`time_budget`)? Is no step left (`out_of_steps`)? The first yes ends the run, and `tripped` keeps the budget rows of that check.
3. Take the next step and add its tokens and milliseconds to the totals.
4. Judge the step. A tool step has the outcome of its status. A `final` step with no check is `accepted`. With a check, the verdict `pass` makes it `accepted` and anything else `rejected`, with the verdict as feedback (`no verdict` when no claim names the answer). Push the `step` row, and the `feedback` row when there is feedback.
5. If the outcome is `accepted`, the run ends with `final`.
6. Compute the **signature** of a failure (an `error` step or a `rejected` claim): the action, the arguments written back as JSON with sorted keys and no white space, and the message with white space collapsed and digits replaced by `#`. If the step is not a failure the streak is 0; if the signature equals the previous one the streak grows by 1; otherwise it is 1. Remember the signature.
7. After the step, ask in order: is a token total above its limit, then a time total above its limit (`>` this time), then is the streak at the limit, which is above 0 (`no_progress`)? The first yes ends the run.
8. When the loop ends, push the `stop` row and return the reason.

### Correctness

The loop terminates because every iteration consumes one step of a finite list. The reason it returns is the first true question of the list that was being asked when it stopped, which is the definition in the statement. The two lists are asked at different moments (before an iteration, after a step) and never mix, so no pair of questions has an ambiguous order: within a moment the order is the table, and between moments the one that comes first in time wins, which is why the cap, asked before the next iteration, loses to `no_progress`, asked right after a step. A streak counts consecutive equal signatures: it is reset by any step that has no signature and restarted at 1 by a different one, so its value after a step is exactly the length of the run of equal failures that ends at that step. Canonical forms make the comparison faithful: parsing and writing the arguments back with sorted keys maps two JSON texts to the same text exactly when they are the same JSON value (arrays keep their order, `true`, `1` and `"1"` stay different), and the message form is a function of the message, so equal messages map to equal forms. Treating a rejected claim as a failure with the feedback as its message makes the stuck-claim case reuse the same counter with no new rule.

### Complexity

- Time: O(L) for L the total length of the steps' texts — each executed step is judged once, its arguments are parsed and written once and its message is scanned once; every check is O(1).
- Space: O(n) for n steps — the trace holds one row for each executed step (and one for each rejected claim), and the signatures kept are those of one step.

### Trade-offs

- A **consecutive** streak is simple, cheap and explainable, and it is blind to a loop that alternates between two calls. Keeping the last `k` signatures and stopping when one repeats `limit` times in the window catches those loops too, at the price of stopping a model that really does need to retry a flaky call between other work. The statement fixes the simple rule and leaves the window to the follow-ups.
- Masking digits merges failures that differ only in a number. That is what a harness wants for line numbers and timings, and wrong for `exit code 1` against `exit code 2`. A production harness would let each tool say which part of its message is the signature.
- Checking budgets only between steps is the simplest design, and it lets one long step overshoot. The alternative is a deadline passed to the step itself (a timeout on the tool call, a cap on the output length), which the data-only model of this problem cannot show.
- The check being given as data keeps the problem deterministic. A real check is code that runs, can be slow or flaky, and its cost belongs in the budgets.
- A loop that never stops is the same resource-exhaustion risk that OWASP lists as LLM06:2026 Unbounded Consumption (2025: LLM10), which is framed around abuse of an application but recommends agentic circuit breakers among its mitigations: step limits, time limits and per-run cost ceilings on every agent execution. A step cap, a token budget and a time budget are those kinds of limits applied to an agent.

### Pitfalls and edge cases

- Level 1: ask the cap before looking for a step, or a run that ends exactly at the cap reports `out_of_steps`, and a cap of 0 with no steps reports the wrong reason. A `final` step on the last allowed iteration must still count. `iterations()` before any run is 0, and each run starts from zero.
- Level 2: compare the arguments as JSON values, not as text: key order and white space must not matter, and `true` must stay different from `1`. Collapse white space before masking digits, and trim first. A success, a `final` step or any different failure ends the streak; forgetting to reset it on a success makes `A ok A` look like two in a row. With a limit of 1 the first failure stops the run; with 0 the check is off. `no_progress` is reported before the next cap check, so a streak that reaches the limit on the last allowed iteration reports `no_progress`.
- Level 3: use `>=` before a step and `>` after it. A run that uses exactly its budget does not overshoot, and it still stops at the next check. A limit of 0 is not "no limit": it is spent before the first step, and `-1` is the no-limit value. A `final` step that went over budget is still `final`. Both budgets can trip together, and the rows come tokens first. When the steps end exactly as a budget is spent, the budget check comes before `out_of_steps`.
- Level 4: an unknown claim is matched as written, so a trailing space or a different case gets `no verdict`; only the exact text `pass` accepts. A rejected claim must go through the same budget and streak checks as any step. A trace for a run of zero iterations has only the `stop` row, and `summary()` describes the last run only.

### Language notes

- Python: `json.dumps(json.loads(args), sort_keys=True, separators=(",", ":"))` is the canonical form of the arguments, and `" ".join(text.split())` trims and collapses white space in one call. A frozen tuple of three strings compares directly. A `dataclass(slots=True)` keeps the record of one run in one place.
- TypeScript: there is no built-in canonical JSON, so a short recursive function sorts the keys of each object and writes arrays in order; `JSON.stringify` of a tuple of three strings makes a signature that compares with `===`. Splitting on `/\s+/` and dropping empty words does the trimming and collapsing.

## Further reading

- S. Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", ICLR 2023, arXiv:2210.03629: the cycle of model reasoning, tool use and observation that agent loops follow.
- [OWASP Top 10 for LLM Applications 2026, LLM06:2026 Unbounded Consumption (2025: LLM10)](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/): why an application should bound the inferences it runs, with rate limits, hard spending caps and agentic circuit breakers (step, recursion-depth and time limits) among the mitigations.
- [RFC 8259, The JSON Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259): an object is an unordered collection of name/value pairs (the reason key order is ignored here), the advice that names be unique, and the range of integers that is safe across implementations (section 6).
