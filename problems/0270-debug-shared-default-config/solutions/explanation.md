# Debug: Shared Default Config: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| deep-copy-per-tenant | optimal | O(1) per call, with a settings object of fixed size | O(t) | default answer: every tenant gets a deep copy of the defaults |

Here `t` is the number of tenants with settings.

## Approach: deep-copy-per-tenant (A deep copy of the defaults per tenant)

### Intuition

`{ ...DEFAULT_SETTINGS }` looks like a copy, and it is one level of a copy. A spread copies each property's value, and the value of an object property is a reference. So `retries`, a number, is a real copy, while `limits` and `notifyChannels` are the same objects as in the defaults. Writing `settings.limits.requestsPerMinute = 500` writes into the one `limits` object that every tenant and the defaults all share.

The defaults live in a module-level constant, so the damage outlives the request. `const` doesn't help: it fixes the variable, not what the variable points at. This is why a restart "fixes" it, and why tests pass or fail by their order: an earlier test has changed the defaults for all later ones in the same process.

### Say it out loud

"Spread is a shallow copy. Nested objects and arrays are shared by reference, so a write through one tenant's settings mutates the module-level default for everyone, for the life of the process. I'd use `structuredClone` here, or better, a function that builds new defaults on each call, so there's no shared object to corrupt. And `const` doesn't make an object immutable, it only stops the variable being reassigned."

### Debugging approach

1. **Reproduce in one test.** Change `blue`, then read `green`.
2. **Test identity.** `settings.limits === DEFAULT_SETTINGS.limits` is `true`. That is the bug, in one line.
3. **Explain what doesn't leak.** `retries` is fine because it's a number directly on the copied object. A symptom that affects some fields and not others points at how deep the copy goes.
4. **Check every level.** Copying `limits` alone leaves `notifyChannels` (`h2`). Spreading `limits` leaves `perRoute`, one level down (`h3`). A deep copy on every call loses the earlier changes (`h6`).

### Algorithm

1. When a tenant is first used, give it `structuredClone(DEFAULT_SETTINGS)`, and store that.
2. Every later call uses the tenant's own copy.
3. `reset` deletes the tenant's entry, so its next use starts from the defaults, which nothing has changed.

### Correctness

`structuredClone` copies every nested object and array, so no tenant's settings share a mutable object with another tenant or with the defaults. Every setter writes only through `#settingsOf(tenant)`, so it reaches only that tenant's copy, and `DEFAULT_SETTINGS` is only ever read, so it keeps its values for the life of the process. `channels` returns a copy too, so a caller can't reach into the settings through its result.

### Complexity

- Time: O(1) per call, with a settings object of fixed size — copying the defaults takes a fixed number of steps, and Map operations are O(1) on average.
- Space: O(t) — one settings object per tenant with settings. Route limits add to it as they are set.

### Trade-offs

A factory, `function defaultSettings(): Settings { return { retries: 3, ... }; }`, can't be corrupted at all, because there's no shared object, and it's the cleanest option when the defaults are written in code. `structuredClone` is the smallest change, and it works when defaults come from a file. It throws on functions, and it drops class prototypes. `JSON.parse(JSON.stringify(...))` also deep-copies plain data, and it loses `undefined`, `Date`s and `Map`s.

Layering instead of copying (store only each tenant's changes, and read through to the defaults) uses less memory with many tenants, and it means a change to the defaults reaches every tenant that hasn't overridden it. That is either what you want or the next incident, so it deserves a decision.

### Pitfalls and edge cases

- The general trap: spread, `Object.assign`, `slice` and `concat` are all shallow.
- `const` isn't immutability. `Object.freeze` isn't deep, either: freezing `DEFAULT_SETTINGS` still lets `limits` change, and a write to a frozen object fails silently in sloppy mode and throws in strict mode, which ES modules always are.
- A getter that returns an internal array hands the caller a way in. `channels` returns a copy here, and a caller of the shipped version could `push` to the tenant's list.
- State at module level lives as long as the process, across every request. In a server that is a long time, and in a test run it is every test in the file.
- A test passing alone and failing in a suite usually means shared state. Run the file in another order to confirm it.

### Prevention

- Build defaults in a function rather than sharing an object.
- Type them `Readonly<...>` all the way down, and the compiler rejects writes through them: a `DeepReadonly` type catches this bug at compile time.
- In tests, deep-freeze shared fixtures, so that any write fails loudly at the line that made it.

### Language notes

TypeScript type-checks the shipped code without a complaint: the copy has the right type, and types say nothing about sharing. `readonly` in an interface is shallow too, unless applied at each level. `structuredClone` has been a global since Node 17.
