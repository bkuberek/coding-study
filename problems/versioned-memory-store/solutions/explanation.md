# Versioned Memory Store: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| versioned-map | optimal | O(1) per call | O(u) | default answer |

`u` is the number of keys ever changed.

## Approach: versioned-map (One map from each key to its version and value that keeps forgotten keys)

### Intuition

A lost update happens because a writer acts on something it read earlier, and the store cannot tell that the thing has changed since. A version number makes "since" checkable: the writer says which version it read, and the store accepts the change only if that is still the version. This is compare-and-set, or optimistic concurrency: nobody holds a lock while the model thinks, and the rare collision costs one retry.

Two details make the version trustworthy. A refused change must not touch it, or a refused writer would knock out the next honest one. And it must never go down: a version that comes back to a value it had before, as it would if forgetting deleted the key, lets a writer holding that old number in again. That is the ABA problem, and the cure is a tombstone, an entry that remembers the version after its value is gone.

### Algorithm

1. Keep a map from key to (version, value). A missing key reads as (0, no value).
2. `get` and `version` read the entry.
3. `write` and `forget` share one step: read the key's version; if the expected version differs, return `[0, version]`; otherwise store (version + 1, new value), where `forget`'s new value is none, and return `[1, version + 1]`.

### Correctness

A key's version is 0 until its first accepted change, and each accepted change raises it by exactly 1, so it counts accepted changes and never decreases. A change is accepted only when the writer's expected version equals the current one, which means no other change was accepted since the writer read it, so it cannot overwrite a revision it did not see. A refused change writes nothing, so it cannot disturb any other writer's version. Keys are separate entries, so a change to one never moves another.

### Complexity

- Time: O(1) per call — one map lookup and at most one map write, on average.
- Space: O(u) — one entry per key ever changed, forgotten ones included.

### Trade-offs

Tombstones cost memory for keys that are gone. A real store sweeps them after a while, which is safe once no writer can still hold a version read before the forget, for example after every lease or session older than the tombstone has ended.

A lock held from read to write would also prevent lost updates, but here it would be held across a model call that takes seconds, and every other run would wait. Optimistic versions never block, and they only cost a retry when two runs really did collide. When collisions are frequent, the retries pile up, and that is the point at which a queue per key or a lock starts to pay.

The cases here are sequences of calls, with interleavings written out, rather than threads run against each other. That tests what the store promises: its outcome for each order the writers can reach it in. Within one process, the check and the write must also run with nothing in between. In TypeScript a synchronous method already does, since the event loop runs one at a time. In Python with threads, a lock around the check and the write does it. In a database it is one `UPDATE ... WHERE key = ? AND version = ?`, with the number of updated rows as the answer.

### Pitfalls and edge cases

- **No check at all.** A blind write is the lost update itself (`ex1`, `h1`, `h9`).
- **A check other than equality.** Accepting an older expected version lets stale writers in (`h1`, `h12`), and accepting a newer one lets a writer claim a version nobody handed out (`ex3`, `h5`).
- **Bumping the version on a refusal.** Then the refused writer's retry, and every other writer who read the same version, are refused too (`h2`, `h13`).
- **Forgetting by deleting.** The version goes back to 0, and a writer that read the key before it existed gets in (`ex2`, `h3`, `h7`, `h10`).
- **One counter for all keys.** Versions belong to keys, so a change to one key must not refuse writers of another (`h4`, `h8`).
- **Skipping a change that writes the same value.** It is still an accepted change, and writers who read the version before it must be refused (`h6`).
- **What a refusal reports.** The current version, so the writer can read again from the right place: not the version it expected, and not the next one (`h12`).
- **Unknown keys.** They read as version 0 with no value, reading them creates nothing, and forgetting one at version 0 is an accepted change (`ex3`, `h7`, `h11`).
- **Exact keys.** `User` and `user` are different keys (`h8`).

### Language notes

- Python: `dict.get(key, default)` with a shared `NamedTuple` for the missing entry reads a key without creating it. A `NamedTuple` is immutable, so replacing the entry is the only way to change it.
- TypeScript: `Map.get(key) ?? default` does the same. The store is synchronous, so each call runs to the end before the event loop runs anything else, which makes the check and the write one step.
