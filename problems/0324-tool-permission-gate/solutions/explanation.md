# Tool Permission Gate: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| layered-gate | optimal | O(R + H L) per check for R rules, H alias hops and a path of length L | O(R + M + K) for R rules, M memories and K log rows | default answer; each level adds one layer in front of or behind the rules, and one function computes the verdict that `check`, `remember` and the log all use |

Here `R` is the number of rules, `H` the number of alias hops followed while resolving a path (at most 40), `L` the length of a path, `M` the number of remembered answers and `K` the number of rows in the audit log.

## How the design grows level by level

| Level | Change | What the gate adds |
|-------|--------|--------------------|
| 1 | Rules by tool name, most specific wins | A set of `(effect, pattern)` pairs and a sort key for the matching ones |
| 2 | Scopes on arguments | A layer in front of the rules that can only deny: a path resolver with aliases and a URL host reader |
| 3 | Read-only tools, risk, memory | A base verdict (`deny`, `allow`, or `ask` with a reason) and a memory that may settle an `ask` |
| 4 | Channels, questions, audit log | A door (`receive`) that trusts one channel, a numbered list of questions, and one place that writes the log |

The idea that keeps the four levels small is that **a decision is computed, never stored**: `check` runs a fixed sequence of layers (scope, deny rule, risk, allow or ask rule, read-only mark, memory) on the current state and returns the first verdict that applies, together with the name of the layer. The same function gives the reason for the log, the "would it ask?" test of `remember`, and the decision. A design in which approvals are written into the rules would lose the difference between a rule the user wrote and an answer to a single question, and with it the ability to say why.

The statement is grounded in two entries of the OWASP Top 10 for LLM Applications 2026: LLM01:2026 Prompt Injection (2025: LLM01), the way untrusted text turns into actions, and LLM03:2026 Excessive Agency (2025: LLM06), the harm that follows when the application grants too much functionality, too many permissions or too much autonomy. Its mitigations (least privilege, human approval for high-impact actions, separating untrusted content, and checking authorization in code and not in the model) are the four layers above.

## Approach: layered-gate (Scope first then the most specific rule then risk then memory)

### Intuition

The gate is a pipeline of questions, ordered from the ones that can only say no to the ones that can only ask. A scope or a deny rule says no and nothing overrides it. A risk turns a yes into a question. Only what is left as a question may be settled by a remembered answer, and a remembered answer is the weakest layer: a rule added later outranks it. Injection resistance is not a clever filter on text: it is the absence of any path from text to state. The only door is `receive`, it opens for one channel, and the channel is a value the harness sets, not something the text can claim.

### Algorithm

1. Keep the rules as a set of `(effect, pattern)` pairs. To decide a tool, take the matching rules and the maximum of the key `(is exact, prefix length, strictness)`, with `deny > ask > allow` for strictness. No match is `ask`.
2. Keep scopes per tool and parameter, and aliases per link. To resolve a path, read its pieces from left to right with a queue of pieces and a list of names. Skip empty and `.` pieces, pop on `..`, push any other piece, and when the path so far equals an alias link, empty the list and put the pieces of the target in front of the queue. Count the hops and fail after 40.
3. A path is inside a root when the root's resolved names are a prefix of the path's resolved names. A host is read by cutting the authority out of the URL, dropping the user name, splitting off the port, lower-casing, and comparing with the allowed entries (`*.` entries need a longer host).
4. `judge(tool, args, memory)` returns `(decision, reason, can ask)`: first the first argument out of scope (`deny`), then a matching `deny` rule, then the first risky argument (`ask`), then an `allow` rule, an `ask` rule, the read-only mark, or the default. If memory is allowed and the base decision is `ask`, look up the exact memory, then the tool memory (skipping an `allow` when the call is risky).
5. `check` calls `judge`, opens a numbered question if the result is `ask`, writes a row to the log and returns the decision. `remember` stores an answer only when `judge` without memory says the call can ask.
6. `receive` compares the channel with `user`. Anything else is ignored with `untrusted-channel`. For `user`, the text is split on single spaces: exactly two words, a verb and an argument. A rule verb with a valid pattern adds a rule; an answer verb with a valid number settles a pending question and may call `remember`. Everything else is `not-a-directive`. A row is written in each case.

### Correctness

Order independence of level 1: the decision depends on the set of matching rules and on a total order over their keys, so it does not depend on the order of insertion, and removing a rule gives the decision of the best of the rest. The key is a total order because two different matching patterns of the same kind have different prefix lengths (two prefixes of one name differ in length), and two equal patterns differ in effect.

Resolution: each step either consumes a piece or replaces the current names with the target's pieces, and the hop counter bounds the second kind of step, so resolution terminates; the result is what a file system would give for an absolute path, because an alias is followed at the moment it is reached and `..` pops from the resolved names. Comparing name lists instead of text is what makes `/work2` outside `/work`.

Safety of the layers: the verdict is a pure function of the current state, in which only three things can lower a restriction: a rule added by the user (directly or through `receive`), a remembered answer (which only settles an `ask` and never a `deny`) and a removed rule. The first two are reachable from text only through `receive` with channel `user`. A remembered `allow` for a tool never answers a risky call, so a broad answer cannot cover the dangerous variant.

Questions and log: a question opens when a check returns `ask`, and only `check` returns `ask`, so numbers are consecutive. A question leaves `pending` once, so an answer is applied at most once. Every `check` and `receive` writes exactly one row, so the log has one row for each decision.

### Complexity

- Time: O(R + H L) per check for R rules, H alias hops and a path of length L — matching scans the rules once, and a path is read once plus the pieces of each followed target; the memory lookups are hash lookups and the risk and scope lists are short.
- Space: O(R + M + K) for R rules, M memories and K log rows — rules, scopes, aliases and risks are stored once, each remembered answer is one entry, and each decision adds one row to the log.

### Trade-offs

- **Most specific against first match.** First match is easy to explain and to implement, and its meaning depends on line order, which makes edits risky: a broad `allow` above a narrow `deny` silently wins. Most specific makes the order irrelevant, at the cost of defining specificity precisely (here: exact, then prefix length, then strictness). Some tools break the remaining ties with "deny wins", which is what level 1 does.
- **Default `ask` against default `deny`.** The classic principle of fail-safe defaults says access should be granted only on explicit permission. An agent harness has a person to ask, so the default here is a question rather than a refusal; an unattended agent would use `deny`.
- **Resolve by data, not by the real file system.** The aliases are given, so the problem is deterministic. A real gate resolves paths against the real file system, and then there is a gap between checking a path and using it, in which a link can change. A common remedy is to check the object that was opened, not its name, or to run the tool in a sandbox.
- **A trusted channel is a design decision, not a filter.** Scanning tool output for phrases like "ignore previous instructions" is a losing game, since the attacker chooses the words. Deciding that only one channel can grant leaves no wording that works.
- **Memory scope.** Remembering per exact call is safe and noisy; remembering per tool is quiet and broad. The rule that a tool-wide `allow` does not cover risky calls keeps most of the quiet and drops the worst of the breadth.

### Pitfalls and edge cases

- Level 1: an exact rule beats a wildcard even when the wildcard's prefix is the whole name. `read_*` matches `read_`. `*` is the least specific, and removing a rule uncovers the next one. A pattern is a prefix of the name, not a substring (`read*` does not match `my_read`).
- Level 2: never compare path text with `startsWith`: `/workspace` starts with `/work`. A `..` after an alias climbs from the target. The parent of the root is the root. A relative path fails. A loop of aliases, or an alias that contains itself, must fail closed and not recurse forever. For hosts, take the host after the last `@` of the authority, and cut the authority at `/`, `?` and `#` first, or `https://evil.test/?h=allowed.example` and `https://evil.test#@allowed.example` pass. `*.example.org` does not match `example.org`, and a suffix test without the dot would let `notexample.org` in. A backslash or a space anywhere in a URL, and a percent sign in the host, is refused because different parsers read them differently.
- Level 3: a read-only mark does not outrank an explicit rule, a risk or a scope. `remember` returns `false` for a call that does not ask, so a scope cannot be argued away by an answer. The exact memory ignores the order of the arguments but not an extra argument. A remembered `allow` for the tool does not cover a risky call, while a remembered `deny` does. Rules added after an answer outrank it, and removing them brings the answer back.
- Level 4: compare the channel exactly (`User`, `user ` and `tool:user` are not `user`). A directive is the whole text: leading or trailing spaces, double spaces, tabs and newlines make it chat. Numbers have no leading zero. A rule already present is `no-change`. An answer works once. `decide`, `remember` and the other harness methods write no row. When the rules change between a question and its answer, the question is still answered but nothing is remembered.

### Language notes

- Python: a set of `(effect, pattern)` tuples and `max(..., key=...)` with a tuple key give the whole of level 1; `str.removesuffix` and `re.fullmatch` keep the host reader short. `dict` and `tuple(sorted(...))` serve as the memory keys.
- TypeScript: use `Object.hasOwn` (or a `Map`) to test whether a word is a directive verb, since `"constructor" in {}` is true. Maps cannot have array keys, so the exact memory is keyed by a JSON string of the tool and the sorted pairs. `Array.prototype.sort` without a comparator compares as strings, which is the order wanted for names of arguments. The URL reader is a regular expression plus a few string cuts, not the built-in `URL` class, so that both languages apply exactly the rules of the statement.

## Further reading

- [OWASP Top 10 for LLM Applications 2026, LLM01:2026 Prompt Injection (2025: LLM01)](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/): direct and indirect injection (external content that carries embedded instructions), and the mitigations of least privilege, human approval for privileged operations and separating untrusted content.
- [OWASP Top 10 for LLM Applications 2026, LLM03:2026 Excessive Agency (2025: LLM06)](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/): excessive functionality, permissions and autonomy, with the mitigations of minimizing tools and their permissions, requiring user approval and complete mediation.
- J. H. Saltzer and M. D. Schroeder, "The Protection of Information in Computer Systems", Proceedings of the IEEE 63(9):1278-1308, 1975, doi:10.1109/PROC.1975.9939: the design principles of fail-safe defaults and complete mediation, which the default and the single door of the gate follow.
- [POSIX.1-2017, Base Definitions, section 4.13 Pathname Resolution](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap04.html): how a symbolic link is replaced by its contents in the middle of a path, and how dot-dot refers to the parent of the directory reached so far; the root is commonly its own parent, which POSIX allows and this problem makes the rule.
- [RFC 3986, Uniform Resource Identifier: Generic Syntax](https://www.rfc-editor.org/rfc/rfc3986): the authority with its optional user information, host and port, and the statement that the host is case-insensitive.
- [CWE-22, Path Traversal](https://cwe.mitre.org/data/definitions/22.html) and [CWE-59, Improper Link Resolution Before File Access](https://cwe.mitre.org/data/definitions/59.html): the two weaknesses that the path scope guards against.
