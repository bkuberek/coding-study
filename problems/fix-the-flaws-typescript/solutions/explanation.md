# Fix the Flaws (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: check the owner in every query that takes an id, decode a name before checking where it leads, copy only the fields a user may set, bind every value, and keep tokens and internals out of the log and the answers |

## How the project grows level by level

| Level | Finding | What the fix changes |
|-------|---------|----------------------|
| 1 | Anyone signed in reads and deletes any note by its id | `readNote` and `deleteNote` in `src/notes.ts` ask for `owner_id` too |
| 2 | A download name climbs out of `attachments/`; the account endpoints take `role` from the body | `download` in `src/attachments.ts` decodes, resolves and checks the folder; `register` and `updateProfile` in `src/users.ts` read only their own fields |
| 3 | The search builds SQL from its text | `searchNotes` in `src/notes.ts` binds the text and the owner |
| 4 | Tokens in the log; messages and stacks in error answers | `login` in `src/users.ts` and the request log in `src/server.ts` print no token; `failure` in `src/server.ts` answers the code alone and logs the rest |

## Approach: reference (Check the owner, keep names inside their folder, read only the fields a user may set, bind every value, and keep secrets and internals out of what the service says)

### Intuition

Every finding has the same shape: a value the caller controls reaches something that matters, and nothing on the way asks whether it should. An id reaches a row with no question about whose row it is. A name reaches the filesystem with no question about where it leads. A body reaches the account record with no question about which fields a user may set. Search text reaches the SQL parser with no question at all. And in the other direction, a token and the service's insides reach places a stranger can read.

So the work is the same each time: find where the value goes, and put the question there, in the one place that cannot be gone around. The owner goes into the query, not into a check before it. The name is checked after it is decoded and resolved, on the path that will be opened, not on the text that came in. The account takes the fields it wants from the body, rather than the body deciding. The text goes to the database as a value, never as SQL.

The other half of the exercise is everything that must keep working. A fix that deletes the search, the download or the admin route closes the hole and fails the review. That is why every level has normal cases next to the probes.

### Say it out loud

"First I read each finding and trace the request it describes through the code, to the line where the caller's value is used. That is where the fix goes, because a check anywhere earlier can be gone around by some other route to that line.

"For the notes, the query that finds a note by id also takes the owner's id, for reading and for deleting. Another user's note then answers 404, exactly like a note that never existed, so the ids leak nothing. I check every query that takes a note id, not just the one the ticket shows.

"For downloads, I decode the name first, then resolve it against the folder and check that the result is a file directly inside it. Checking the raw text for `../` misses `..%2F`, and checking for `..` misses `%2e%2e%2f`. Checking the resolved path catches them all, and a name with a space still works.

"For accounts, I copy only the fields a user may set: username and password when they sign up, the display name after that. A new account is always a member. The ticket showed `PATCH /me`, but sign-up spread the body the same way, so I fixed both.

"For the search, the text is bound as a parameter. Then `' OR '1'='1` is just text no title holds, and `O'Brien` finds O'Brien. Stripping or escaping quotes by hand breaks the second and is easy to get wrong.

"For the log, I print what was asked and how it was answered, with no headers, and the login line no longer prints the token. For errors, the client gets the code; the message and stack go to the log."

### Algorithm

1. Level 1: add `AND owner_id = ?` to the queries in `readNote` and `deleteNote`, bound to the caller's id. No row means 404, whoever owns the id.
2. Level 2: in `download`, decode the name, answering 404 for an encoding that does not decode. Resolve it against the folder, answer 404 unless the result's `dirname` is the folder, and answer 404 for any file that cannot be read.
3. Level 2: in `register`, read `username` and `password` from the body and insert `member`. In `updateProfile`, read `display_name`, keep the current one when it is missing, and update that column alone.
4. Level 3: in `searchNotes`, write `owner_id = ? AND title LIKE '%' || ? || '%'` and bind the caller's id and the text.
5. Level 4: print `login: <username> signed in`, without the token. Print the request log line after the answer, as the method, the path and the status, with no headers.
6. Level 4: in `failure`, answer `{"error": code}` for a known error, and for anything else print the error to the log and answer 500 `{"error": "internal_error"}`.

### Design

The reference replaces four files of the starter and leaves the others as they were.

- `src/notes.ts`: the owner in every query that takes a note's id; the search with bound values.
- `src/attachments.ts`: `decoded` and `download`, which checks the resolved path, not the text.
- `src/users.ts`: `register` and `updateProfile` with their own fields only; `login` without the token in its log line.
- `src/server.ts`: `failure`, which answers the code alone, and the request log without headers.
- `tests/security.test.ts`: one test per finding, with a raw `node:http` request for the literal `../`, which `fetch` would resolve before sending.

Not graded, and worth discussing:

- **Authorization in one place.** Here each query carries its owner. In a larger service, a repository that takes the caller in every method, or row-level security in the database, means a new route cannot forget it.
- **Sessions.** Tokens never expire and are stored as they are. A real service keeps a hash of each token, with an expiry, and lets a user end their sessions.
- **Structured logs.** A logger that writes chosen fields, with an allowlist of what may be printed, stops the next header from leaking the way this one did.
- **Tests that attack.** Each fix comes with a test that sends the probe and one that does the normal thing, so a later change cannot reopen the hole or close the feature without a test failing.

### Correctness

A note leaves the database only through a query that holds `owner_id = ?` bound to the caller's id, so another user's note is never read or deleted, and its answer, 404, is the one a missing id gets. A download opens only `resolve(folder, name)` where `name` is the decoded text and the result's `dirname` is the folder; whatever the raw text held, `..`, encoded slashes or encoded dots, the path opened is a direct child of the folder. An account's role is written only as `member` at sign-up, and `updateProfile` writes only `display_name`, so no body can change a role. The search's SQL is a constant string, and the caller's text and id reach SQLite only as bound values, so no text can change what the query does. The token is printed by no line: the login line names the user, and the request log prints the method, the path and the status. An error's body is built from its code alone.

### Complexity

- Time: per request — one indexed query per note, account or session; a search scans the caller's notes, as the starter's did
- Space: per request — one row or the caller's matching notes; the fixes keep nothing new

### Trade-offs

Answering 404 for another user's note, rather than 403, costs a little honesty: the owner of a mistyped id and an attacker see the same answer. It is worth it, since a 403 tells the attacker the note exists, and the ids are counted.

Ignoring unknown fields in a body, rather than refusing them with 400, keeps old clients working when a field is renamed, and makes a typo silent. Refusing them is stricter and also correct; the statement asks for ignoring so that a client sending `role` learns nothing either way.

Checking the resolved path is a check on the result, and works whatever the encoding. An allowlist of names would be stricter still, and would need updating each time a file is added.

Binding values fixes every query it is used in. Escaping quotes by hand fixes one quote character in one dialect, and is the classic way to get it nearly right.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names the step.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Checks the owner when reading, and not when deleting | The same hole, on the other route that takes an id | `h1`: `step 4 DELETE /notes/{{id}}: status: expected 404, got 204` |
| Answers 403 for another user's note | It tells the caller the id exists | `v2`, `h1` |
| Refuses a raw name holding `../` | `..%2F` decodes to `../` after the check | `h4`: `step 2 GET /attachments/..%2Fpackage.json: status: expected 404, got 200`, and `h5` |
| Refuses a raw name holding `..` | `%2e%2e%2f` holds no `..` until it is decoded | `h5` |
| Refuses any name holding `%` | A name with a space arrives as `%20` | `h6` |
| Removes the admin route, or every role | The administrator is a user too | `h7` |
| Drops `role` from `PATCH /me` and leaves sign-up alone | Sign-up spread the body the same way | `h8`: `step 3 GET /me: body.role: expected "member", got "admin"` |
| Strips quotes from the search text | `O'Brien` no longer finds O'Brien, and finds `Obrien draft` | `h9` |
| Refuses search text that looks like SQL | A denylist misses the next probe, and refuses real text | `h9`, `h10` |
| Removes the login line, and leaves the headers in the request log | Every request with a session prints its token | `h12` |
| Hides the `Authorization` header, and leaves the login line | Signing in prints the token | `v9` |
| Removes the stack, and keeps the message | The message holds the parser's error and the code's internals | `v10`, `h13`, `h14` |
| Answers every error as 500 | The statuses are part of the contract | `v10`, `h13`, `h14` |

**Edge cases.**

- A note id that was never given and another user's note give the same answer (`v2`).
- A user who sends `role` along with a new display name gets the new name, and keeps their role (`v6`).
- A search without `q` lists all of the caller's notes, so the parameter can be missing as well as empty (`h11`).
- The literal `../` only reaches the app because the service routes on the path as it arrived; `new URL()` would resolve it first, and `fetch` does the same in a test, which is why the reference's test sends it with `node:http` (`v4`).
- `%` and `_` in a search still match any text and any character. Nothing here searches for them; escaping them with `ESCAPE` is the follow-up.
