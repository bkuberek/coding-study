# Versioned Memory Store

## Statement

Several runs of an assistant share one long-term memory: short notes about a user, each under a key. A run reads a note, asks a model to revise it, and writes it back. The model takes seconds, so two runs often revise the same note at once, and with plain writes the second one silently erases the first one's revision. That is a **lost update**, and nobody notices until the assistant forgets something it was told.

Implement `MemoryStore`, which prevents it with versions. Every key has a version that counts the changes accepted for it, and a key that was never changed is at version 0. A change names the version its writer read, and it is accepted only if that is still the key's version. Otherwise it is refused, nothing changes, and the writer learns the current version, so it can read the note again, merge its revision in, and retry.

- `get(key)` returns the key's value, or `""` when it has none: it was never written, or it was forgotten.
- `version(key)` returns the key's version.
- `write(key, expectedVersion, value)`: if `expectedVersion` equals the key's version, the value is set, the version goes up by 1, and the call returns `[1, newVersion]`. Otherwise nothing changes and it returns `[0, currentVersion]`.
- `forget(key, expectedVersion)`: the same check. When it is accepted, the key has no value afterwards, its version goes up by 1, and the call returns `[1, newVersion]`. Otherwise nothing changes and it returns `[0, currentVersion]`.

The rules that matter:

- **Only equality is accepted.** An expected version below the current one is stale, and one above it was never handed out.
- **Versions belong to keys.** A change to one key leaves every other key's version alone.
- **A version never goes down**, not even when a key is forgotten. If forgetting brought it back to 0, a writer that read the key before it was first written, and so holds version 0, could write over a note that was created and forgotten in the meantime, without seeing either change.
- **Every accepted change counts**: writing the value a key already has, and forgetting a key that has no value, both raise the version. A refused change counts for nothing.

The store is called by one operation at a time, in the order of a case. A case lays out what several writers did, interleaved, as one sequence: two `version` calls in a row are two writers reading.

## Input

- `MemoryStore()`: an empty store.
- `get(key)`, `version(key)`: read one key.
- `write(key, expectedVersion, value)`: change a key's value, if `expectedVersion` is its version.
- `forget(key, expectedVersion)`: remove a key's value, if `expectedVersion` is its version.

## Output

The constructor returns nothing. `get` returns a string, `version` an integer, and `write` and `forget` return `[1, newVersion]` when the change is accepted and `[0, currentVersion]` when it is refused.

## Examples

### Example 1

<!-- case: ex1 -->

Two runs read the note at version 1. The first one's write is accepted, and the note moves to version 2. The second one's write still expects version 1, so it is refused with the current version, 2. It reads the note again, merges its own revision in, and writes with version 2, which is accepted. Neither revision is lost.

### Example 2

<!-- case: ex2 -->

The plan is written at version 1 and forgotten at version 2: it has no value, and its version stays 2. A writer that read the key before it existed expects version 0 and is refused. Writing with version 2 is accepted.

### Example 3

<!-- case: ex3 -->

A key nobody wrote is at version 0 with no value, so a write that expects version 3 is refused, and one that expects 0 is accepted. Another key is untouched.

## Constraints

- At most `10^4` operations per case.
- Keys are 1 to 40 characters long and compared exactly.
- Values are 1 to 200 characters long, so a value is never `""`.
- `0 <= expectedVersion <= 10^4`.

## Follow-ups

- A run that is refused merges and retries. When should it give up, and what should it do then?
- Store the notes in a database table with a `version` column. Which single statement makes a write accepted only at the expected version, and how do you know whether it was?
- Make a change to two keys at once: both are accepted or neither is. What should a refusal report?
- Several threads share one store in a single process. Which part of a change has to happen without another thread in between?

## Hints

### Hint 1

One map from key to (version, value) is enough. A key missing from the map is at version 0 with no value.

### Hint 2

`write` and `forget` are the same change with a different new value. Write the check once.

### Hint 3

Forgetting keeps the key's entry, with no value and the next version. Deleting the entry would bring the version back to 0.
